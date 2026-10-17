import sys, pathlib, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import pytest
from types import SimpleNamespace as NS
from brainbob import events, audit
from brainbob.memory import MemoryStore


@pytest.fixture(autouse=True)
def fresh_events(tmp_path):
    events.reset(); events.set_log(str(tmp_path / "events.jsonl"))
    yield
    events.reset()


def eps(n=50, auth="approved"):
    return [NS(id=f"e{i}", text=f"Atlas launch note {i}", date=f"2026-10-{i % 28 + 1:02d}", source="t", authority=auth) for i in range(n)]


def store():
    s = MemoryStore()
    s.add("Atlas launch is in March", author="a", origin="e0", date="2026-01-01")
    return s


def fake(verdict, calls=None):
    def f(role, messages, **kw):
        assert role == "judge"
        return json.dumps({"verdict": verdict, "reason": "r"})
    return f


def test_seed_reproducible(monkeypatch):
    monkeypatch.setattr(audit.llm, "complete", fake("insufficient"))
    a = audit.audit_recent(store(), eps(), seed=7, propose=lambda m, e: None)
    b = audit.audit_recent(store(), eps(), seed=7, propose=lambda m, e: None)
    c = audit.audit_recent(store(), eps(), seed=8, propose=lambda m, e: None)
    assert a.sampled_ids == b.sampled_ids and len(set(a.sampled_ids)) == 10 and a.sampled_ids != c.sampled_ids
    assert set(a.sampled_ids) <= set(a.eligible_ids) and len(a.eligible_ids) == 50


def test_insufficient_changes_nothing(monkeypatch):
    monkeypatch.setattr(audit.llm, "complete", fake("insufficient"))
    s = store(); before = [m.__dict__.copy() for m in s.all()]; called = []
    r = audit.audit_recent(s, eps(), seed=1, propose=lambda m, e: called.append(1))
    assert not called and [m.__dict__ for m in s.all()] == before
    assert r.counts["insufficient"] == r.counts["checked"] > 0
    types = [e["type"] for e in events.history() if e["type"].startswith("audit.")]
    assert types[0] == "audit.started" and types[-1] == "audit.finished"
    assert types.count("audit.checked") == r.counts["checked"]


@pytest.mark.parametrize("auth,expect", [("approved", True), ("tentative", False)])
def test_contradicted_authority(monkeypatch, auth, expect):
    monkeypatch.setattr(audit.llm, "complete", fake("contradicted"))
    called = []
    audit.audit_recent(store(), eps(auth=auth), seed=1, propose=lambda m, e: called.append((m.id, e.id)))
    assert bool(called) is expect


def test_coverage_about_20_percent_and_judgment(monkeypatch):
    monkeypatch.setattr(audit.llm, "complete", fake("contradicted"))
    s = store(); cov = []
    for seed in range(300):
        r = audit.audit_recent(s, eps(), seed=seed, propose=lambda m, e: None)
        cov.append(r.coverage(["e17"]))
    assert abs(sum(cov) / len(cov) - 0.2) < 0.06
    # judgment accuracy only counts pairs whose evidence was sampled
    r = audit.audit_recent(s, eps(), seed=3, propose=lambda m, e: None)
    ep = r.sampled_ids[0]
    assert r.judgment_accuracy({("m1", ep): "contradicted", ("m1", "not-sampled"): "supported"}) == 1.0
    assert r.judgment_accuracy({("m1", "not-sampled"): "supported"}) is None
