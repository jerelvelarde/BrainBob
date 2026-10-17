"""Replay saved Bob pair responses through real maintenance rules without inference.

Controlled policy stress test: one known existing record, one supplied candidate
fact, one saved verdict per pair. Permission/lock conditions are interventions,
not benchmark metadata. Gold is joined only after all memory actions complete.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bob_format
from brainbob import curator, events, llm, maintain
from brainbob.memory import MemoryStore
from brainbob.types import Episode

CONDITIONS = ("approved_unlocked", "approved_locked", "tentative", "unapproved_author")


def read(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def indexed(rows):
    result = {}
    for row in rows:
        if row["id"] in result:
            raise ValueError(f"duplicate id: {row['id']}")
        result[row["id"]] = row
    return result


def validate(inputs, predictions):
    by_id, preds = indexed(inputs), indexed(predictions)
    if not by_id or set(by_id) != set(preds):
        raise ValueError("prediction IDs must exactly match nonempty input IDs")
    for pid, row in by_id.items():
        if set(row) != {"id", "existing", "candidate", "input_sha256", "messages"}:
            raise ValueError("inputs must be the label-free Bob export")
        expected = bob_format.input_hash(pid, row["existing"], row["candidate"])
        if row["input_sha256"] != expected or preds[pid].get("input_sha256") != expected:
            raise ValueError(f"input hash mismatch: {pid}")
        if row["messages"] != bob_format.messages(pid, row["existing"], row["candidate"]):
            raise ValueError(f"input messages mismatch: {pid}")
        if ("response" in preds[pid]) == ("error" in preds[pid]):
            raise ValueError(f"prediction needs response xor error: {pid}")
    return preds


class ControlledACL:
    def __init__(self, approve): self.approve = approve
    def can_read(self, member, scope): return scope == "policy-replay"
    def can_approve(self, member, scope): return self.approve and scope == "policy-replay"


def replay(inputs, predictions, model):
    """No labels accepted; no calls to a model or external service permitted."""
    preds = validate(inputs, predictions)
    rows = []
    with patch.object(llm, "complete", side_effect=AssertionError("offline replay cannot call a model")), \
         patch.object(curator, "extract", side_effect=lambda ep, role: [ep.text]), \
         patch.object(curator, "model_for", return_value="fixture:provided-candidate-fact"):
        for row in inputs:
            pred = preds[row["id"]]
            verdict = bob_format.verdict(pred.get("response"))
            for condition in CONDITIONS:
                store = MemoryStore()
                old, _ = store.add(row["existing"]["text"], author="owner", origin="existing-source",
                                   date=row["existing"]["date"], scope="policy-replay", authority="approved")
                if condition == "approved_locked": store.lock(old.id, "owner")
                called = []
                def saved_judge(candidate, memory):
                    # Bound to the frozen pair, not whichever neighbor happens to be retrieved.
                    assert (memory.text, memory.date) == (row["existing"]["text"], row["existing"]["date"])
                    assert (candidate["text"], candidate["date"]) == (row["candidate"]["text"], row["candidate"]["date"])
                    called.append(memory.id)
                    return verdict
                saved_judge.model_id = "saved-response:" + model
                episode = Episode(row["candidate"]["source_id"], row["candidate"]["text"],
                                  row["candidate"]["date"], "saved-pair-replay", author="owner", scope="policy-replay",
                                  authority="tentative" if condition == "tentative" else "approved")
                decisions = maintain.ingest(episode, store, ControlledACL(condition != "unapproved_author"), judge=saved_judge)
                assert len(called) == 1 and len(decisions) == 1
                decision = decisions[0]
                rows.append({"id": row["id"], "input_sha256": row["input_sha256"], "condition": condition,
                             "verdict": verdict, "action": decision.action, "reason": decision.reason,
                             "old_status": old.status, "new_status": store.get(decision.memory_id).status if decision.memory_id else None,
                             "decision_model": decision.model})
    return rows


def diagnose(rows, gold_cases):
    """Post-hoc labels describe observed actions; they cannot drive the replay."""
    gold = indexed(gold_cases)
    if {row["id"] for row in rows} != set(gold):
        raise ValueError("gold IDs must match replay IDs")
    for row in rows:
        case = gold[row["id"]]
        if bob_format.input_hash(case["id"], case["existing"], case["candidate"]) != row["input_sha256"]:
            raise ValueError(f"gold input mismatch: {row['id']}")
    summary = {}
    for condition in CONDITIONS:
        selected = [row for row in rows if row["condition"] == condition]
        false_conflicts = [r for r in selected if r["verdict"] == "conflict" and gold[r["id"]]["gold"] != "conflict"]
        overwrites = [r for r in false_conflicts if r["old_status"] == "retired"]
        summary[condition] = {"n": len(selected), "actions": dict(Counter(r["action"] for r in selected)),
                              "classification_correct": sum(r["verdict"] == gold[r["id"]]["gold"] for r in selected),
                              "false_conflict_count": len(false_conflicts),
                              "false_conflict_overwrites": len(overwrites),
                              "false_conflict_overwrite_ids": [r["id"] for r in overwrites],
                              "old_records_retired": sum(r["old_status"] == "retired" for r in selected)}
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--gold", type=Path, required=True, help="read after every policy action, only for diagnosis")
    parser.add_argument("--model", required=True, help="actual saved prediction model/checkpoint identity")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists(): raise FileExistsError(args.out)
    events.reset()
    rows = replay(read(args.inputs), read(args.predictions), args.model)
    report = {"kind": "saved_response_policy_replay_not_fresh_inference", "model": args.model,
              "limitations": ["Provided candidate facts bypass extraction; this does not evaluate curator quality.",
                              "Single-neighbor isolated stores; four controlled authority/lock interventions.",
                              "Existing benchmark IDs/source IDs differ from live bridge IDs; no new model response is claimed.",
                              "Pair classifier and policy stress diagnostic; not full Bob Benchmark CATS or production rollout."],
              "sha256": {"inputs": digest(args.inputs), "predictions": digest(args.predictions), "gold": digest(args.gold)},
              "conditions": diagnose(rows, read(args.gold)), "rows": rows}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x") as f: json.dump(report, f, indent=2); f.write("\n")
    print(json.dumps(report["conditions"], indent=2))


if __name__ == "__main__": main()
