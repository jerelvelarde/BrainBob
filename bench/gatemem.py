"""GateMem preflight and incremental prediction export. Preflight never calls a model."""
import argparse
import importlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from adapters import gatemem


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["preflight", "predict"])
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--adapter", help="module:factory implementing reset/ingest/query")
    parser.add_argument("--output", type=Path, help="new directory; existing runs are never overwritten")
    parser.add_argument("--limit-episodes", type=int, help="label output as a subset")
    args = parser.parse_args()
    report = gatemem.preflight(args.data_dir)
    if args.command == "preflight":
        print(json.dumps(report, indent=2))
        return 0
    if not args.adapter or not args.output:
        parser.error("predict requires --adapter and --output")
    if args.limit_episodes is not None and args.limit_episodes < 1:
        parser.error("--limit-episodes must be positive")
    module, name = args.adapter.split(":", 1)
    factory = getattr(importlib.import_module(module), name)
    episodes, checkpoints = gatemem.load(args.data_dir)
    from brainbob import llm
    report["model_configuration"] = llm.configuration()
    report["cost_note"] = "Unknown model/provider tariffs are not verified; do not treat estimates as billed cost."
    if args.limit_episodes is not None:
        episodes = episodes[:args.limit_episodes]
    ids = {e["episode_id"] for e in episodes}
    selected = [cp for cp in checkpoints if cp["episode_id"] in ids]
    report.update(status="running", adapter=args.adapter, selected_episodes=sorted(ids),
                  selected_checkpoints=len(selected), completed_checkpoints=0,
                  subset=len(selected) != len(checkpoints), scoring="not_run")
    report["implementation_commit"] = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    report["implementation_dirty"] = bool(subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT, text=True).strip())
    args.output.mkdir(parents=True, exist_ok=False)
    manifest = args.output / "manifest.json"
    manifest.write_text(json.dumps(report, indent=2) + "\n")
    try:
        with (args.output / "predictions.jsonl").open("w", encoding="utf-8") as f:
            for row in gatemem.replay(episodes, selected, factory):
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                f.flush()
                report["completed_checkpoints"] += 1
        report["status"] = "predictions_complete_unscored"
        return 0
    except Exception as exc:
        report.update(status="failed_incomplete", error_type=type(exc).__name__)
        raise
    finally:
        manifest.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
