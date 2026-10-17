"""Summary isolation, data selection, and failure behavior without network calls."""
import json
import pathlib
import sys
from types import SimpleNamespace

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from brainbob import llm, summary
from brainbob.acl import Org
import server


def memory(mid, scope="rusty-rod", **kw):
    return SimpleNamespace(id=mid, text=f"Fact {mid}", scope=scope, status="trial", **kw)


def client(records):
    org = Org.load(pathlib.Path(__file__).resolve().parents[1] / "fixtures/rusty_rod/org.json")
    store = SimpleNamespace(all=lambda: records)
    app = server.create_app(store, None, None, None, None, org=org)
    return TestClient(app), app.state.bus


def test_summary_filters_before_model_and_never_writes(monkeypatch):
    retired = memory("old"); retired.status = "retired"
    records = [memory("org"), memory("mine", "rusty-rod/sales/sales-01", authority="tentative", flagged=True),
               memory("other", "rusty-rod/sales/sales-02"), memory("secret", "rusty-rod/engineering"), retired]
    calls = []
    def complete(role, messages):
        calls.append((role, json.loads(messages[1]["content"])))
        return "A tentative fact needs review."
    monkeypatch.setattr(llm, "complete", complete)
    c, bus = client(records)
    assert c.get("/memories/summary").status_code == 401
    result = c.get("/memories/summary", headers={"X-BrainBob-Member": "sales-01"})
    assert result.status_code == 200
    assert result.json()["memory_count"] == 2
    assert result.json()["model"] == llm.NANO
    assert calls[0][0] == "summarizer"
    assert {m["id"] for m in calls[0][1]} == {"mine", "org"}
    assert calls[0][1][0]["flagged"] is True
    assert calls[0][1][0]["authority"] == "tentative"
    assert bus.history() == []
    assert len(records) == 5 and retired.status == "retired"


def test_empty_summary_skips_inference(monkeypatch):
    monkeypatch.setattr(llm, "complete", lambda *a: (_ for _ in ()).throw(AssertionError("should not run")))
    c, _ = client([])
    result = c.get("/memories/summary", headers={"X-BrainBob-Member": "sales-01"}).json()
    assert result["memory_count"] == 0 and result["summary"] == ""


def test_failure_is_retryable_and_redacted(monkeypatch):
    def fail(*a): raise RuntimeError("private provider error and secret")
    monkeypatch.setattr(llm, "complete", fail)
    c, _ = client([memory("org")])
    result = c.get("/memories/summary", headers={"X-BrainBob-Member": "sales-01"})
    assert result.status_code == 503
    assert "secret" not in result.text
    monkeypatch.setattr(llm, "complete", lambda *a: "")
    assert c.get("/memories/summary", headers={"X-BrainBob-Member": "sales-01"}).status_code == 503
    monkeypatch.setattr(llm, "complete", lambda *a: "Recovered summary")
    assert c.get("/memories/summary", headers={"X-BrainBob-Member": "sales-01"}).json()["summary"] == "Recovered summary"


def test_input_limit_disclosed_and_stable_order(monkeypatch):
    calls = []
    monkeypatch.setattr(llm, "complete", lambda role, messages: calls.append(messages) or "Overview")
    large = memory("large"); large.text = "x" * summary.MAX_INPUT_CHARS
    result = summary.summarize([large, memory("b"), memory("a")])
    assert result["truncated"] is True and result["memory_count"] == 2 and result["total_count"] == 3
    assert [m["id"] for m in json.loads(calls[0][1]["content"])] == ["a", "b"]


def test_summary_refreshes_prompt_when_memory_changes(monkeypatch):
    calls = []
    monkeypatch.setattr(llm, "complete", lambda role, messages: calls.append(messages) or "Overview")
    record = memory("one")
    summary.summarize([record])
    record.text = "Updated fact"
    summary.summarize([record])
    assert calls[0] != calls[1]


def test_summary_uses_small_separate_role():
    cfg = llm.configuration()["summarizer"]
    assert cfg["model"] == llm.NANO
    assert cfg["base_url"] == llm.DEFAULT_BASE_URL
    assert cfg["max_tokens"] == 768
    assert cfg["extra_body"] == llm.NOTHINK
