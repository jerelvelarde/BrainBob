"""Thresholded label probabilities on a LABELED set (local, pure python, no model).

Calibrate the threshold on labeled development data only (our synthetic dev or Bob dev.jsonl gold); never pick it
by looking at Bob eval outcomes. Below threshold -> None -> maintain's conservative path (tentative, never overwrite).

  python threshold_report.py --probs out/runs/<run>/label_probs.json --key tuned_dev --gold <bob>/benchmarks/bob/dev.jsonl
  python threshold_report.py --probs ... --key tuned_dev --gold ... --sweep
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from job_all import thresholded


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probs", required=True); ap.add_argument("--key", required=True, help="e.g. base_dev, tuned_dev")
    ap.add_argument("--gold", required=True, help="JSONL with id + gold (Bob dev.jsonl) or id + label")
    ap.add_argument("--threshold", type=float, default=0.8); ap.add_argument("--sweep", action="store_true")
    a = ap.parse_args()
    gold = {}
    for l in open(a.gold, encoding="utf8"):
        if l.strip():
            r = json.loads(l); gold[r["id"]] = r.get("gold") or r.get("label")
    P = json.load(open(a.probs, encoding="utf8"))[a.key]
    rows = [dict(id=r["id"], gold=gold[r["id"]], probs=r["probs"]) for r in (P["rows"] if isinstance(P, dict) else P)
            if r.get("probs") and r["id"] in gold]
    for t in ([0.5, 0.6, 0.7, 0.8, 0.9, 0.95] if a.sweep else [a.threshold]):
        kept = [r for r in rows if max(r["probs"].values()) >= t]
        acc = sum(max(r["probs"], key=r["probs"].get) == r["gold"] for r in kept) / len(kept) if kept else None
        print(json.dumps(dict(threshold=t, n=len(rows), overall_coverage=len(kept) / len(rows) if rows else None,
                              selective_accuracy=acc, per_label=thresholded(rows, t))))


if __name__ == "__main__":
    main()
