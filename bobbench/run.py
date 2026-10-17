"""CLI runner: worlds x conditions x replicates -> bobbench/results/<ts>/.

    python -m bobbench.run --worlds all \
        --conditions no_memory,full_history,append_only,maintained,always_refuse,unfiltered \
        --replicates 3 [--fast]

Each (world, condition, replicate) starts from an empty adapter, receives timeline items
one by one in seq order, and at each checkpoint gets ``maintain`` then a fresh session
and ``act``. The adapter sees the world manifest (no timeline), delivered items and the
checkpoint's visible fields only. Oracle files are read by ``score.py`` after all runs
finish; the run phase only learns whether every checkpoint has an oracle entry.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import platform
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from . import __version__
from .adapter import SURFACES, count_tokens
from .adapters import CONDITIONS, Unsupported, resolve
from .schema import ORACLES_DIR, PKG_DIR, WORLDS_DIR, check_oracle, find_world_paths, load_world, oracle_path_for, validate_world

RESULTS_DIR = os.path.join(PKG_DIR, "results")
DEFAULT_BUDGET = {"context_tokens": 4000}


def _sha(s: str) -> str:
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()


def run_seed(world_id: str, condition: str, replicate: int) -> int:
    return int(_sha(f"{world_id}|{condition}|{replicate}")[:8], 16)


def _err(e: BaseException) -> str:
    return f"{type(e).__name__}: {str(e)[:300]}"


def run_world(world, condition: str, factory, replicate: int, workdir: str, exports_dir: str | None = None,
              probes: bool = True) -> list[dict]:
    """Run one condition on one world from empty state. Returns trace records."""
    wid = world.world_id
    seed = run_seed(wid, condition, replicate)
    out = []
    t0 = time.time()
    base = {"world_id": wid, "condition": condition, "replicate": replicate, "seed": seed}
    errors, n_src, n_pol = [], 0, 0
    os.makedirs(workdir, exist_ok=True)
    try:
        adapter = factory()
        adapter.seed, adapter.replicate = seed, replicate
        first_budget = next((c.get("budget") for c in world.checkpoints if c.get("budget")), None)
        adapter.reset(world.manifest(), copy.deepcopy(world.raw.get("budget") or first_budget or DEFAULT_BUDGET), workdir)
    except Exception as e:  # noqa: BLE001
        msg = f"reset failed: {_err(e)}"
        out.append({"type": "run_start", **base, "adapter": None, "error": msg})
        for cp in world.checkpoints:
            out.append({"type": "checkpoint", **base, "checkpoint_id": cp["checkpoint_id"], "seq": cp["seq"],
                        "principal": cp["principal"], "answer": "", "context": "", "cited_event_ids": [],
                        "cost": {}, "error": msg, "probes": {}})
        out.append({"type": "run_end", **base, "errors": [msg], "elapsed_s": round(time.time() - t0, 3)})
        return out
    out.append({"type": "run_start", **base, "adapter": getattr(adapter, "name", type(adapter).__name__),
                "adapter_class": f"{type(adapter).__module__}.{type(adapter).__name__}"})
    last_seq = -1
    for item in world.timeline:
        kind = item.get("type")
        visible = copy.deepcopy(item)
        if kind == "source":
            n_src += 1
            try:
                rc = adapter.ingest(visible)
                if isinstance(rc, dict) and rc.get("ok") is False:
                    errors.append(f"ingest {item['event_id']}: not ok")
            except Exception as e:  # noqa: BLE001
                errors.append(f"ingest {item.get('event_id')}: {_err(e)}")
        elif kind == "policy":
            n_pol += 1
            try:
                adapter.apply_policy(visible)
            except Exception as e:  # noqa: BLE001
                errors.append(f"apply_policy {item.get('policy_id')}: {_err(e)}")
        elif kind == "checkpoint":
            out.append(_checkpoint(adapter, item, last_seq, base, probes))
        last_seq = item["seq"]
    export_sha, export_bytes = None, 0
    try:
        exp = adapter.export_trace()
        blob = json.dumps(exp, ensure_ascii=False, default=str, sort_keys=True)
        export_sha, export_bytes = _sha(blob), len(blob)
        if exports_dir:
            os.makedirs(exports_dir, exist_ok=True)
            with open(os.path.join(exports_dir, f"{wid}__{condition}__r{replicate}.json"), "w", encoding="utf-8") as f:
                f.write(blob)
    except Exception as e:  # noqa: BLE001
        errors.append(f"export_trace: {_err(e)}")
    out.append({"type": "run_end", **base, "sources": n_src, "policies": n_pol, "errors": errors[:50],
                "n_errors": len(errors), "export_sha256": export_sha, "export_bytes": export_bytes,
                "elapsed_s": round(time.time() - t0, 3)})
    return out


def _checkpoint(adapter, cp: dict, last_seq: int, base: dict, probes: bool) -> dict:
    principal, task = cp["principal"], cp["task"]
    rt, purpose = cp["requested_time"], cp.get("purpose")
    budget = cp.get("budget") or DEFAULT_BUDGET
    rec = {"type": "checkpoint", **base, "checkpoint_id": cp["checkpoint_id"], "seq": cp["seq"],
           "principal": principal, "task": task, "requested_time": rt, "purpose": purpose, "budget": budget}
    errors = []
    try:
        rec["maintain_receipt"] = adapter.maintain(last_seq, copy.deepcopy(budget))
    except Exception as e:  # noqa: BLE001
        errors.append(f"maintain: {_err(e)}")
    t0 = time.time()
    session = None
    try:
        session = adapter.open_session(principal, task, rt, purpose, copy.deepcopy(budget))
    except Exception as e:  # noqa: BLE001
        errors.append(f"open_session: {_err(e)}")
    context = ""
    if isinstance(session, dict):
        context = session.get("context") or ""
        context = context if isinstance(context, str) else json.dumps(context, ensure_ascii=False, default=str)
        rec.update(session_id=session.get("session_id"), context=context, context_sha256=_sha(context),
                   context_tokens=count_tokens(context), context_tokens_reported=session.get("context_tokens"),
                   source_ids=list(session.get("source_ids") or []),
                   session_meta={k: v for k, v in session.items()
                                 if k not in ("context", "session_id", "context_tokens", "source_ids")})
        try:
            res = adapter.act(session, task) or {}
            rec.update(answer=res.get("answer") or "", cited_event_ids=list(res.get("cited_event_ids") or []),
                       cost=res.get("cost") or {})
            if res.get("error"):
                errors.append(f"act: {res['error']}")
        except Exception as e:  # noqa: BLE001
            errors.append(f"act: {_err(e)}")
        final = session.get("context") or ""
        final = final if isinstance(final, str) else json.dumps(final, ensure_ascii=False, default=str)
        if final != context:  # the adapter re-assembled the context inside act: score what was finally delivered
            rec.update(context=final, context_sha256=_sha(final), context_tokens=count_tokens(final),
                       context_opened_sha256=_sha(context), context_changed_in_act=True,
                       source_ids=list(session.get("source_ids") or []))
    elif session is not None:
        errors.append("open_session: did not return a dict")
    rec.setdefault("context", context)
    rec.setdefault("answer", "")
    rec.setdefault("cited_event_ids", [])
    rec.setdefault("cost", {})
    rec["latency_s"] = round(time.time() - t0, 3)
    if probes:
        pr = {}
        request = {"query": task, "requested_time": rt, "purpose": purpose}
        for s in SURFACES:
            try:
                pr[s] = adapter.inspect_surface(principal, s, copy.deepcopy(request))
            except Exception as e:  # noqa: BLE001
                pr[s] = {"_probe_error": _err(e)}
        rec["probes"] = pr
    if session is not None:
        try:
            adapter.close_session(session)
        except Exception as e:  # noqa: BLE001
            errors.append(f"close_session: {_err(e)}")
    rec["error"] = "; ".join(errors) or None
    return rec


def _git_commit() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=PKG_DIR, capture_output=True, text=True,
                              timeout=10).stdout.strip() or None
    except Exception:  # noqa: BLE001
        return None


def validate_all(world_paths: list[str], oracles_dir: str) -> tuple[list, list[str], list[str]]:
    worlds, errors, warnings = [], [], []
    seen = set()
    for p in world_paths:
        try:
            w = load_world(p)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{os.path.basename(p)}: {_err(e)}")
            continue
        if w.world_id in seen:
            errors.append(f"duplicate world_id {w.world_id!r}")
        seen.add(w.world_id)
        e1, w1 = validate_world(w)
        errors += e1
        warnings += w1
        if not e1:
            e2, w2 = check_oracle(w, oracle_path_for(w, oracles_dir))
            errors += e2
            warnings += w2
        worlds.append(w)
    return worlds, errors, warnings


def run_benchmark(world_paths: list[str], conditions: list[str], replicates: int = 3, out_dir: str | None = None,
                  oracles_dir: str = ORACLES_DIR, factories: dict | None = None, fast: bool = False,
                  workers: int = 4, probes: bool = True, n_boot: int | None = None, log=print) -> tuple[str, dict]:
    worlds, errors, warnings = validate_all(world_paths, oracles_dir)
    for w in warnings:
        log(f"warning: {w}")
    if errors:
        raise SystemExit("invalid worlds/oracles:\n  " + "\n  ".join(errors))
    if not worlds:
        raise SystemExit("no worlds to run")
    if out_dir is None:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S") + ("-fast" if fast else "")
        out_dir = os.path.join(RESULTS_DIR, stamp)
        k = 1
        while os.path.exists(out_dir):
            k += 1
            out_dir = os.path.join(RESULTS_DIR, f"{stamp}-{k}")
    os.makedirs(out_dir, exist_ok=True)
    factories = dict(factories or {})
    resolved, unsupported = {}, {}
    for c in conditions:
        if c in factories:
            resolved[c] = factories[c]
            continue
        try:
            resolved[c] = resolve(c)
        except Unsupported as e:
            unsupported[c] = str(e)
    try:
        from .answer import config as answer_config
        acfg = answer_config()
    except Exception as e:  # noqa: BLE001
        acfg = {"error": _err(e)}
    meta = {"type": "run_meta", "run_id": os.path.basename(out_dir), "bobbench_version": __version__,
            "started": datetime.now().astimezone().isoformat(), "argv": sys.argv, "fast": fast,
            "conditions": list(conditions), "replicates": replicates, "unsupported": unsupported,
            "world_paths": [w.path for w in worlds],
            "world_sha256": {w.world_id: w.sha256 for w in worlds}, "oracles_dir": oracles_dir,
            "answer_config": acfg, "git_commit": _git_commit(), "python": sys.version.split()[0],
            "platform": platform.platform(), "seed_rule": "int(sha256('world|condition|replicate')[:8], 16)",
            "probes": probes, "warnings": warnings}
    trace_path = os.path.join(out_dir, "traces.jsonl")
    lock = threading.Lock()
    tf = open(trace_path, "w", encoding="utf-8")

    def write(recs):
        with lock:
            for r in recs:
                tf.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
            tf.flush()

    write([meta] + [{"type": "unsupported", "condition": c, "reason": r} for c, r in unsupported.items()])
    jobs = [(c, w, r) for c in conditions if c in resolved for w in worlds for r in range(replicates)]
    par = [j for j in jobs if getattr(resolved[j[0]], "parallel_safe", False)]
    seq = [j for j in jobs if not getattr(resolved[j[0]], "parallel_safe", False)]
    exports = os.path.join(out_dir, "exports")

    def do(job):
        c, w, r = job
        recs = run_world(w, c, resolved[c], r, os.path.join(out_dir, "work", f"{w.world_id}__{c}__r{r}"),
                         exports, probes)
        write(recs)
        n_err = sum(1 for x in recs if x.get("type") == "checkpoint" and x.get("error"))
        log(f"done {w.world_id} {c} r{r}: {sum(1 for x in recs if x.get('type') == 'checkpoint')} checkpoints, {n_err} with errors")

    try:
        if par:
            with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
                for f in as_completed([ex.submit(do, j) for j in par]):
                    f.result()
        for j in seq:
            do(j)
    finally:
        write([{"type": "run_finished", "finished": datetime.now().astimezone().isoformat()}])
        tf.close()
    from .score import BOOTSTRAP_N, score_dir  # oracles are read only from here on
    card = score_dir(out_dir, oracles_dir, n_boot=n_boot or BOOTSTRAP_N)
    return out_dir, card


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m bobbench.run")
    ap.add_argument("--worlds", default="all", help="'all' or comma list of world ids / file stems")
    ap.add_argument("--conditions", default=None, help=f"comma list; default all: {','.join(CONDITIONS)}")
    ap.add_argument("--replicates", type=int, default=3)
    ap.add_argument("--fast", action="store_true", help="one replicate (smoke run)")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--no-probes", action="store_true")
    ap.add_argument("--worlds-dir", default=WORLDS_DIR)
    ap.add_argument("--oracles-dir", default=ORACLES_DIR)
    ap.add_argument("--out", default=None)
    ap.add_argument("--rescore", default=None, metavar="RESULTS_DIR",
                    help="score an existing run's traces with the current oracles; no adapter or model calls")
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    if a.rescore:
        from .score import score_dir
        conds = [c.strip() for c in a.conditions.split(",") if c.strip()] if a.conditions else None
        score_dir(a.rescore, a.oracles_dir, conditions=conds, keep_previous=True)
        print(open(os.path.join(a.rescore, "scorecard.md"), encoding="utf-8").read())
        print(f"rescored: {a.rescore}")
        return
    conditions = [c.strip() for c in (a.conditions or ",".join(CONDITIONS)).split(",") if c.strip()]
    bad = [c for c in conditions if c not in CONDITIONS]
    if bad:
        ap.error(f"unknown conditions {bad}; choose from {list(CONDITIONS)}")
    reps = 1 if a.fast else a.replicates
    paths = find_world_paths(a.worlds, a.worlds_dir)
    out_dir, _card = run_benchmark(paths, conditions, reps, a.out, a.oracles_dir, fast=a.fast,
                                   workers=a.workers, probes=not a.no_probes)
    print(open(os.path.join(out_dir, "scorecard.md"), encoding="utf-8").read())
    print(f"results: {out_dir}")


if __name__ == "__main__":
    main()
