"""Merge several single-world HF-Jobs bob-runs into one results dir and score it.

python -m bobbench.merge_runs --hub-repo Guangze/memops-small-qwen3-0.6b-lora --prefix bob-runs/ \
    --since 20261017-2153 --out bobbench/results/<stamp>-judge-swap-merged

No model calls. Validates: same BOB_COMMIT, same conditions, no duplicate world.
Writes traces.jsonl (one merged run_meta + all non-meta records), sources.json, scorecard.{md,json}.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

from .run import WORLDS_DIR, ORACLES_DIR

HEADER = ("> **Merged result.** This card combines {n} separate single-world, single-replicate jobs "
          "(BOB_FAST=1; worlds: {worlds}). **replicates=1, not the 3 required by the spec**; no per-world "
          "variance estimate, so confidence intervals reflect world sampling only.\n"
          "> Worlds missing from this merge: {missing}. Source runs: see sources.json.\n\n")


def list_runs(api, repo, prefix, since):
    runs = set()
    for f in api.list_repo_files(repo):
        m = re.fullmatch(re.escape(prefix) + r"([^/]+)/(traces\.jsonl|run_meta\.json)", f)
        if m and m.group(1) >= since:
            runs.add(m.group(1))
    return sorted(runs)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m bobbench.merge_runs")
    ap.add_argument("--hub-repo", required=True)
    ap.add_argument("--prefix", default="bob-runs/")
    ap.add_argument("--since", required=True, help="run-stamp lower bound, e.g. 20261017-2153")
    ap.add_argument("--out", required=True)
    ap.add_argument("--worlds-dir", default=WORLDS_DIR)
    ap.add_argument("--oracles-dir", default=ORACLES_DIR)
    ap.add_argument("--cache", default=None, help="download cache dir (default <out>/_downloads)")
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    from huggingface_hub import HfApi, hf_hub_download
    from .score import BOOTSTRAP_N, score_dir

    api = HfApi()
    runs = list_runs(api, a.hub_repo, a.prefix, a.since)
    if not runs:
        raise SystemExit("no runs found")
    os.makedirs(a.out, exist_ok=False)
    cache = a.cache or os.path.join(a.out, "_downloads")

    sources, metas, all_recs = [], [], []
    for r in runs:
        loc = {}
        for fn in ("traces.jsonl", "run_meta.json"):
            loc[fn] = hf_hub_download(a.hub_repo, f"{a.prefix}{r}/{fn}", repo_type="model", local_dir=cache)
        jm = json.load(open(loc["run_meta.json"], encoding="utf-8"))
        recs = [json.loads(l) for l in open(loc["traces.jsonl"], encoding="utf-8") if l.strip()]
        meta = next((x for x in recs if x.get("type") == "run_meta"), None)
        if meta is None:
            print(f"skip {r}: no run_meta in traces"); continue
        wids = sorted(meta.get("world_sha256", {}))
        sources.append({"run": r, "worlds": wids, "bob_commit": jm.get("bob_commit") or meta.get("git_commit"),
                        "conditions": meta.get("conditions"), "replicates": meta.get("replicates"),
                        "hf_job_id": next((jm.get(k) or meta.get(k) for k in ("hf_job_id", "job_id", "JOB_ID")
                                           if jm.get(k) or meta.get(k)), None),
                        "returncode": jm.get("returncode"), "flavor": jm.get("flavor"),
                        "elapsed_s": jm.get("elapsed_s"), "hub_path": f"{a.prefix}{r}"})
        metas.append(meta)
        all_recs.append([x for x in recs if x.get("type") not in ("run_meta", "run_finished")])

    errs = []
    if len({s["bob_commit"] for s in sources}) > 1:
        errs.append(f"different BOB_COMMIT: {sorted({str(s['bob_commit']) for s in sources})}")
    if len({tuple(s["conditions"] or []) for s in sources}) > 1:
        errs.append("different condition sets across runs")
    if len({s["replicates"] for s in sources}) > 1:
        errs.append("different replicate counts across runs")
    seen = {}
    for s in sources:
        for w in s["worlds"]:
            if w in seen:
                errs.append(f"world {w} duplicated in {seen[w]} and {s['run']}")
            seen[w] = s["run"]
    if errs:
        raise SystemExit("merge refused:\n  " + "\n  ".join(errs))

    # worlds / oracles are resolved locally by file name (container paths do not exist here)
    wpaths = {}
    for m in metas:
        for p in m.get("world_paths", []):
            wpaths[os.path.basename(p)] = os.path.join(a.worlds_dir, os.path.basename(p))
    shas = {}
    for m in metas:
        shas.update(m.get("world_sha256", {}))
    allw = sorted(f[:-5] for f in os.listdir(a.worlds_dir) if f.endswith(".json"))
    missing = [w for w in allw if not any(w == x or w.startswith(x) or x.startswith(w.split("-")[0]) for x in seen)]
    missing = [w for w in allw if w.split("-")[0] not in {x.split("-")[0] for x in seen}]

    m0 = metas[0]
    for s in sources:
        s["merged_into"] = os.path.basename(a.out)
    merged = {**m0, "type": "run_meta", "run_id": os.path.basename(a.out), "merged_from": [s["run"] for s in sources],
              "world_paths": sorted(wpaths.values()), "world_sha256": shas, "oracles_dir": a.oracles_dir,
              "replicates": 1, "fast": True, "argv": ["bobbench.merge_runs"] + (argv or sys.argv[1:]),
              "unsupported": {k: v for m in metas for k, v in (m.get("unsupported") or {}).items()}}
    with open(os.path.join(a.out, "traces.jsonl"), "w", encoding="utf-8") as f:
        f.write(json.dumps(merged, ensure_ascii=False, default=str) + "\n")
        for recs in all_recs:
            for x in recs:
                f.write(json.dumps(x, ensure_ascii=False, default=str) + "\n")
    with open(os.path.join(a.out, "sources.json"), "w", encoding="utf-8") as f:
        json.dump({"hub_repo": a.hub_repo, "missing_worlds": missing, "sources": sources}, f, indent=1)

    card = score_dir(a.out, a.oracles_dir, n_boot=BOOTSTRAP_N)
    card["merge"] = {"sources": sources, "missing_worlds": missing, "replicates": 1}
    with open(os.path.join(a.out, "scorecard.json"), "w", encoding="utf-8") as f:
        json.dump(card, f, indent=1, ensure_ascii=False, default=str)
    md = os.path.join(a.out, "scorecard.md")
    body = open(md, encoding="utf-8").read()
    with open(md, "w", encoding="utf-8") as f:
        f.write(HEADER.format(n=len(sources), worlds=", ".join(sorted(seen)), missing=", ".join(missing) or "none") + body)
    print(f"merged {len(sources)} runs -> {a.out}; missing worlds: {missing or 'none'}")


if __name__ == "__main__":
    main()
