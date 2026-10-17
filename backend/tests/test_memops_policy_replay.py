"""Saved-response integration diagnostics. No model inference and no gold in actions."""
import json
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "experiments/memops-small"))
import bob_format
import bridge
import replay_policy
from brainbob import curator, events, llm, maintain
from brainbob.memory import MemoryStore
from brainbob.types import Episode


def pair():
    existing = {"id": "old", "text": "Atlas launch is November 6.", "date": "2026-10-01"}
    candidate = {"source_id": "source", "text": "Borealis launch is November 13.", "date": "2026-10-16"}
    row = {"id": "test-1", "existing": existing, "candidate": candidate,
           "input_sha256": bob_format.input_hash("test-1", existing, candidate),
           "messages": bob_format.messages("test-1", existing, candidate)}
    pred = {"id": row["id"], "input_sha256": row["input_sha256"], "response": '{"verdict":"conflict"}'}
    return row, pred


@pytest.fixture(autouse=True)
def reset_events():
    events.reset()
    yield
    events.reset()


def test_false_conflict_can_retire_valid_approved_unlocked_memory():
    row, pred = pair()
    results = replay_policy.replay([row], [pred], "frozen-test-model")
    by_condition = {r["condition"]: r for r in results}
    unlocked = by_condition["approved_unlocked"]
    assert unlocked["action"] == "supersede" and unlocked["old_status"] == "retired"
    for condition in ("approved_locked", "tentative", "unapproved_author"):
        assert by_condition[condition]["action"] == "tentative"
        assert by_condition[condition]["old_status"] != "retired"
    report = replay_policy.diagnose(results, [{**row, "gold": "unrelated"}])
    assert report["approved_unlocked"]["false_conflict_overwrites"] == 1
    assert all(report[c]["false_conflict_overwrites"] == 0 for c in report if c != "approved_unlocked")
    assert all(r["decision_model"] == "saved-response:frozen-test-model" for r in results)


def test_invalid_saved_response_takes_conservative_path():
    row, pred = pair()
    pred["response"] = "invalid json"
    results = replay_policy.replay([row], [pred], "frozen")
    assert all(r["action"] == "tentative" and r["old_status"] != "retired" for r in results)


@pytest.mark.parametrize("mutation", ["gold", "hash", "duplicate", "messages"])
def test_replay_rejects_labels_or_unbound_responses(mutation):
    row, pred = pair()
    predictions = [pred]
    if mutation == "gold": row["gold"] = "unrelated"
    if mutation == "hash": pred["input_sha256"] = "wrong"
    if mutation == "duplicate": predictions.append(pred)
    if mutation == "messages": row["messages"][1]["content"] = "altered"
    with pytest.raises(ValueError): replay_policy.replay([row], predictions, "frozen")
    assert events.history() == []


def test_posthoc_gold_join_is_bound_to_inputs():
    row, pred = pair()
    results = replay_policy.replay([row], [pred], "frozen")
    row["candidate"]["text"] = "different pair"
    with pytest.raises(ValueError, match="gold input mismatch"):
        replay_policy.diagnose(results, [{**row, "gold": "unrelated"}])


@pytest.mark.parametrize("mode,want", [("callback", "adapter@revision"), ("override", "replay:adapter@revision"),
                                       ("unidentified", "custom:unidentified"), ("default", None)])
def test_judge_provenance_follows_actual_hook(monkeypatch, mode, want):
    monkeypatch.setattr(curator, "extract", lambda ep, role: [ep.text])
    calls = []
    monkeypatch.setattr(llm, "complete", lambda role, msgs: calls.append(role) or '{"verdict":"conflict"}')
    store = MemoryStore()
    old, _ = store.add("Atlas deadline November 6", author="owner", origin="old", date="2026-10-01",
                       scope="policy-replay", authority="approved")
    episode = Episode("new", "Atlas deadline November 13", "2026-10-16", "source",
                      author="owner", scope="policy-replay", authority="approved")
    kwargs = {}
    if mode != "default":
        def judge(c, m): return "conflict"
        if mode in ("callback", "override"): judge.model_id = "adapter@revision"
        kwargs["judge"] = judge
    if mode == "override": kwargs["judge_model"] = want
    decision = maintain.ingest(episode, store, replay_policy.ControlledACL(True), **kwargs)[0]
    expected = want or llm._roles()["judge"]["model"]
    assert decision.action == "supersede" and decision.model == expected
    changed = [e for e in events.history() if e["type"] in ("memory.retired", "memory.corrected")]
    assert changed and all(e["model"] == expected for e in changed)
    assert calls == (["judge"] if mode == "default" else [])


def test_bridge_carries_explicit_model_identity():
    judge = bridge.make_judge(lambda msgs: '{"verdict":"same"}', model="small-model@frozen-revision")
    assert judge.model_id == "small-model@frozen-revision"
