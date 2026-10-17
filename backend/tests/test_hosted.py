"""Hosting contracts: no provider calls, isolated memory and events."""
import base64
import importlib.util
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from test_server import build
from brainbob import events
from brainbob.memory import MemoryStore
from server import create_app

PASSWORD = "test-demo-password-123456"
AUTH = {"Authorization": "Basic " + base64.b64encode(f"brainbob:{PASSWORD}".encode()).decode()}


def test_hosted_gate(monkeypatch):
    monkeypatch.setenv("BRAINBOB_REQUIRE_AUTH", "1")
    monkeypatch.delenv("BRAINBOB_DEMO_PASSWORD", raising=False)
    with pytest.raises(RuntimeError, match="BRAINBOB_DEMO_PASSWORD"):
        build()
    monkeypatch.setenv("BRAINBOB_DEMO_PASSWORD", PASSWORD)
    c, _ = build()
    assert c.get("/healthz").json() == {"status": "ok"}
    for path in ["/memories", "/events", "/docs", "/openapi.json"]:
        assert c.get(path).status_code == 401
        assert c.get(path, headers={"Authorization": "Basic wrong"}).status_code == 401
    assert c.get("/memories", headers=AUTH).status_code == 200
    assert c.get("/memories", headers=AUTH).headers["cache-control"] == "no-store, no-transform"
    assert c.post("/episodes", headers={**AUTH, "Sec-Fetch-Site": "cross-site"}, json={"text": "bad"}).status_code == 403
    assert c.post("/episodes", headers=AUTH, json={"text": "allowed"}).status_code == 200
    assert "replay.done" in c.get("/events", headers=AUTH).text


def test_sse_closes_and_unsubscribes(monkeypatch):
    monkeypatch.setenv("BRAINBOB_SSE_MAX_SECONDS", "0.02")
    c = TestClient(create_app(MemoryStore(), None, None, None, None))
    assert "replay.done" in c.get("/events").text
    assert c.app.state.bus._subs == []


def test_files_and_sequence_survive_reload(tmp_path):
    events.reset()
    events.set_log(str(tmp_path / "events.jsonl"))
    store = MemoryStore(str(tmp_path / "memory.jsonl"))
    memory, _ = store.add("persistent demo fact", author="demo", origin="test", date="2026-10-17")
    last = events.history()[-1]["seq"]
    events.reset()
    events.set_log(str(tmp_path / "events.jsonl"))
    restored = MemoryStore(str(tmp_path / "memory.jsonl"))
    assert restored.all()[0].id == memory.id
    assert events.emit("test.after_restart")["seq"] == last + 1
    events.reset()


def test_seed_requests_include_demo_auth(monkeypatch):
    path = Path(__file__).resolve().parents[2] / "scripts/seed-company.py"
    spec = importlib.util.spec_from_file_location("seed_company", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setenv("BRAINBOB_DEMO_PASSWORD", PASSWORD)
    assert module.auth_headers() == AUTH
