"""Issue #6: the tuned 0.6B checker is opt-in and may only replace memories when an independent judge confirms.
Offline: the five known false conflicts (saved tuned responses) go through the real maintain.ingest rules in the
'approved, authorized, unlocked' condition, where an unconfirmed conflict would retire a valid memory."""
import json
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "experiments/memops-small"))
import bridge
import replay_policy
from brainbob import curator, events, llm, maintain
from brainbob.memory import MemoryStore
from brainbob.types import Episode

RUN = ROOT / "experiments/memops-small/out/runs/20261017-210457"
KNOWN_FALSE = {"eval-007", "eval-011", "eval-015", "eval-035", "eval-048"}


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    events.reset()
    monkeypatch.setattr(curator, "extract", lambda ep, role="curator": [ep.text])
    monkeypatch.setattr(curator, "model_for", lambda role: "fixture")
    monkeypatch.setattr(llm, "complete", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no model calls")))
    yield
    events.reset()


def run(old_text, old_date, new_text, new_date, judge, locked=False):
    store = MemoryStore()
    old, _ = store.add(old_text, author="owner", origin="old", date=old_date, scope="policy-replay", authority="approved")
    if locked: store.lock(old.id, "owner")
    ep = Episode("new", new_text, new_date, "src", author="owner", scope="policy-replay", authority="approved")
    d = maintain.ingest(ep, store, replay_policy.ControlledACL(True), judge=judge)[0]
    return d, store, old


def saved_small(response):
    return bridge.make_judge(lambda msgs: response, model="tuned@b904e6ec")


def known_cases():
    inputs = {r["id"]: r for r in replay_policy.read(ROOT / "experiments/memops-small/bob_inputs/eval_inputs.jsonl")}
    gold = {r["id"]: r for r in replay_policy.read(ROOT / "benchmarks/bob/eval.jsonl")}
    preds = {r["id"]: r for r in replay_policy.read(RUN / "tuned_eval.jsonl")}
    ids = sorted(i for i in preds if preds[i].get("response") == '{"verdict":"conflict"}' and gold[i]["gold"] != "conflict")
    return [(i, inputs[i], preds[i]["response"]) for i in ids]


def test_the_five_known_false_conflicts_are_found():
    assert {i for i, _, _ in known_cases()} == KNOWN_FALSE


def test_unsafe_baseline_retires_so_the_tests_are_meaningful():
    i, row, resp = known_cases()[0]
    d, _, old = run(row["existing"]["text"], row["existing"]["date"], row["candidate"]["text"], row["candidate"]["date"], saved_small(resp))
    assert d.action == "supersede" and old.status == "retired"


@pytest.mark.parametrize("confirm_verdict", ["same", "unrelated"])
def test_five_false_conflicts_never_retire_in_confirm_mode(confirm_verdict):
    for i, row, resp in known_cases():
        judge = bridge.make_safe_judge(saved_small(resp), lambda c, m: confirm_verdict, "confirm")
        d, store, old = run(row["existing"]["text"], row["existing"]["date"], row["candidate"]["text"], row["candidate"]["date"], judge)
        assert d.action in ("tentative", "add", "reject"), i
        assert old.status != "retired" and store.get(old.id).status != "retired", i
        assert d.action != "supersede", i
        assert judge.log == [{"mode": "confirm", "memory_id": old.id, "small": "conflict", "confirm": confirm_verdict, "final": None}]


@pytest.mark.parametrize("raw", ["gibberish", "", "{\"verdict\":\"conflict\",\"x\":1}", "{\"verdict\":\"CONFLICT\"}",
                                 "conflict", "<think>conflict</think>", "[]", "{\"verdict\":"])
def test_malformed_output_never_replaces(raw):
    # confirm judge would say conflict, to prove the small judge's garbage alone cannot trigger a replacement
    judge = bridge.make_safe_judge(saved_small(raw), lambda c, m: "conflict", "confirm")
    d, _, old = run("Atlas launch is November 6.", "2026-10-01", "Borealis launch is November 13.", "2026-10-16", judge)
    assert d.action == "tentative" and old.status != "retired"
    assert judge.log[0]["small"] is None and judge.log[0]["final"] is None


@pytest.mark.parametrize("bad", [None, "", "foo", 3, "Conflict"])
def test_bad_small_judge_return_values_never_replace(bad):
    judge = bridge.make_safe_judge(lambda c, m: bad, lambda c, m: "conflict", "confirm")
    d, _, old = run("Atlas launch is November 6.", "2026-10-01", "Borealis launch is November 13.", "2026-10-16", judge)
    assert d.action == "tentative" and old.status != "retired"


def test_small_judge_exception_never_replaces():
    def boom(c, m): raise RuntimeError("endpoint down")
    judge = bridge.make_safe_judge(boom, lambda c, m: "conflict", "confirm")
    d, _, old = run("Atlas launch is November 6.", "2026-10-01", "Borealis launch is November 13.", "2026-10-16", judge)
    assert d.action == "tentative" and old.status != "retired"


def test_confirmed_conflict_still_replaces():
    judge = bridge.make_safe_judge(saved_small('{"verdict":"conflict"}'), lambda c, m: "conflict", "confirm")
    d, store, old = run("Atlas launch is November 6.", "2026-10-01", "Atlas launch moved to November 13.", "2026-10-16", judge)
    assert d.action == "supersede" and store.get(old.id).status == "retired"
    assert judge.log[0]["small"] == "conflict" and judge.log[0]["confirm"] == "conflict" and judge.log[0]["final"] == "conflict"


def test_confirmed_conflict_still_respects_locks():
    judge = bridge.make_safe_judge(saved_small('{"verdict":"conflict"}'), lambda c, m: "conflict", "confirm")
    d, store, old = run("Atlas launch is November 6.", "2026-10-01", "Atlas launch moved to November 13.", "2026-10-16", judge, locked=True)
    assert d.action == "tentative" and store.get(old.id).status != "retired"


def test_same_and_unrelated_from_small_model_pass_through():
    for verdict in ("same", "unrelated"):
        judge = bridge.make_safe_judge(saved_small('{"verdict":"%s"}' % verdict), lambda c, m: "conflict", "confirm")
        assert judge({"text": "a", "date": "2026-10-16"}, type("M", (), {"id": "m", "text": "b", "date": "2026-10-01"})()) == verdict


def test_observe_mode_equals_confirm_judge_alone():
    cases = [(r["existing"], r["candidate"], resp) for _, r, resp in known_cases()]
    cases.append(({"text": "Atlas launch is November 6.", "date": "2026-10-01"},
                  {"text": "Atlas launch moved to November 13.", "date": "2026-10-16"}, '{"verdict":"unrelated"}'))
    for confirm_verdict in ("same", "unrelated", "conflict", None):
        for ex, ca, resp in cases:
            args = (ex["text"], ex["date"], ca["text"], ca["date"])
            plain, _, p_old = run(*args, lambda c, m: confirm_verdict)
            obs = bridge.make_safe_judge(saved_small(resp), lambda c, m: confirm_verdict, "observe")
            d, _, o_old = run(*args, obs)
            assert (d.action, d.reason, o_old.status) == (plain.action, plain.reason, p_old.status)
            assert obs.log[0]["final"] == confirm_verdict and obs.log[0]["small"] in ("same", "conflict", "unrelated")


def test_bad_mode_rejected():
    with pytest.raises(ValueError): bridge.make_safe_judge(lambda c, m: None, lambda c, m: None, "on")
