# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = [
#   "torch==2.8.0",
#   "transformers==4.56.2",
#   "peft==0.17.1",
#   "accelerate==1.10.1",
#   "huggingface_hub==0.35.3",
#   "fastapi==0.143.3",
#   "uvicorn==0.54.0",
#   "sse-starlette==3.5.0",
#   "httpx==0.28.1",
#   "openai==3.34.0",
#   "rank-bm25==0.2.2",
# ]
# ///
"""HF Jobs run: Bob benchmark with only BrainBob's maintenance pair judge swapped. Everything else (curator, audit
judge, retrieval, rules, answerer, budget, worlds, oracles) is fixed by the checked-out commit.

    conditions: append_only, maintained (production judge), maintained_teacher (Crusoe Nemotron-3-Super-120B),
                maintained_tuned (Qwen3-0.6B + pinned LoRA, sha256-checked), maintained_small_base (same base, no LoRA)

Env: BOB_COMMIT (required, commit of https://github.com/jerelvelarde/BrainBob), CRUSOE_API_KEY (secret; written to
~/.config/crusoe/api.key with mode 600, never printed), HF_TOKEN (secret; upload), BOB_REPLICATES (default 3),
BOB_FAST=1 (smoke: one world, one replicate; world from BOB_FAST_WORLD, default w2-authority-corrections),
BOB_FLAVOR (cost estimate only, default l4x1), BOB_HUB_REPO (default Guangze/memops-small-qwen3-0.6b-lora).

Uploads scorecard.md, scorecard.json, traces.jsonl, run_meta.json and exports/ to <hub repo>/bob-runs/<UTC stamp>/ and
prints scorecard.md to the log.
"""
import json, os, re, subprocess, sys, time

REPO_URL = "https://github.com/jerelvelarde/BrainBob"
CONDITIONS = "append_only,maintained,maintained_teacher,maintained_tuned,maintained_small_base"
HUB_REPO = os.environ.get("BOB_HUB_REPO", "Guangze/memops-small-qwen3-0.6b-lora")


def sh(cmd, **kw):
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(cmd, check=True, **kw)


def write_key():
    key = (os.environ.get("CRUSOE_API_KEY") or "").strip()
    if not key:
        raise SystemExit("CRUSOE_API_KEY is not set (pass it with --secrets CRUSOE_API_KEY)")
    path = os.path.expanduser("~/.config/crusoe/api.key")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(key)
    os.chmod(path, 0o600)
    print("crusoe key written (mode 600)", flush=True)


def versions():
    import importlib.metadata as md
    out = {}
    for p in ("torch", "transformers", "peft", "accelerate", "huggingface_hub", "fastapi", "uvicorn", "sse-starlette",
              "httpx", "openai", "rank-bm25"):
        try:
            out[p] = md.version(p)
        except Exception:  # noqa: BLE001
            out[p] = None
    return out


def gpu():
    try:
        import torch
        return {"cuda": torch.cuda.is_available(), "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {str(e)[:200]}"}


def main():
    t0 = time.time()
    commit = (os.environ.get("BOB_COMMIT") or "").strip()
    if not re.fullmatch(r"[0-9a-f]{7,40}", commit):
        raise SystemExit("BOB_COMMIT must be a git commit sha")
    fast = os.environ.get("BOB_FAST") == "1"
    reps = "1" if fast else os.environ.get("BOB_REPLICATES", "3")
    worlds = os.environ.get("BOB_FAST_WORLD", "w2-authority-corrections") if fast else "all"
    stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime()) + ("-fast" if fast else "")
    work = "/tmp/bob"
    repo = os.path.join(work, "BrainBob")
    out = os.path.join(work, "results", stamp)
    os.makedirs(os.path.dirname(out), exist_ok=True)

    write_key()
    try:
        sh(["git", "clone", "--quiet", REPO_URL, repo])
        sh(["git", "-C", repo, "checkout", "--quiet", commit])
        head = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError) as e:  # no git in the image: same commit as a tarball
        print("git clone failed, falling back to the commit tarball:", type(e).__name__, flush=True)
        import io, shutil, tarfile, urllib.request
        shutil.rmtree(repo, ignore_errors=True)
        data = urllib.request.urlopen(f"{REPO_URL}/archive/{commit}.tar.gz", timeout=120).read()
        with tarfile.open(fileobj=io.BytesIO(data)) as tf:
            top = tf.getmembers()[0].name.split("/")[0]
            tf.extractall(work)
        os.rename(os.path.join(work, top), repo)
        head = top.split("-")[-1] if len(commit) < 40 else commit

    env = {k: v for k, v in os.environ.items() if k != "CRUSOE_API_KEY"}  # the child reads the key file
    env.setdefault("BOB_FLAVOR", "l4x1")
    env["PYTHONUNBUFFERED"] = "1"
    cmd = [sys.executable, "-m", "bobbench.run", "--worlds", worlds, "--conditions", CONDITIONS,
           "--replicates", reps, "--out", out] + (["--fast"] if fast else [])
    print("+", " ".join(cmd), flush=True)
    rc = subprocess.run(cmd, cwd=repo, env=env).returncode

    meta = {"job": "experiments/memops-small/job_bob.py", "bob_commit_requested": commit, "bob_commit": head,
            "repo": REPO_URL, "fast": fast, "worlds": worlds, "replicates": int(reps), "conditions": CONDITIONS.split(","),
            "flavor": env["BOB_FLAVOR"], "returncode": rc, "elapsed_s": round(time.time() - t0, 1), "stamp": stamp,
            "versions": versions(), "gpu": gpu(), "python": sys.version.split()[0]}
    tp = os.path.join(out, "traces.jsonl")
    if os.path.exists(tp):
        with open(tp, encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                if r.get("type") == "run_meta":
                    meta["run_meta"] = r
                elif r.get("type") == "run_end" and r.get("pair_judge"):
                    meta.setdefault("pair_judges", {})[r["condition"]] = {
                        k: v for k, v in r["pair_judge"].items() if k != "usage"}
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "run_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=1, default=str)

    md = os.path.join(out, "scorecard.md")
    print("=== BEGIN scorecard.md ===", flush=True)
    print(open(md, encoding="utf-8").read() if os.path.exists(md) else "(no scorecard: run failed)", flush=True)
    print("=== END scorecard.md ===", flush=True)

    try:
        from huggingface_hub import HfApi
        api = HfApi(token=os.environ.get("HF_TOKEN"))
        ci = api.upload_folder(repo_id=HUB_REPO, repo_type="model", folder_path=out, path_in_repo=f"bob-runs/{stamp}",
                               allow_patterns=["scorecard.md", "scorecard.json", "traces.jsonl", "run_meta.json", "exports/*"],
                               commit_message=f"bob judge comparison {stamp} (BrainBob {head[:12]})")
        print(f"uploaded to {HUB_REPO}/bob-runs/{stamp} commit {getattr(ci, 'oid', None)}", flush=True)
    except Exception as e:  # noqa: BLE001
        print("upload failed:", f"{type(e).__name__}: {str(e)[:300]}", flush=True)
        rc = rc or 1
    sys.exit(rc)


if __name__ == "__main__":
    main()
