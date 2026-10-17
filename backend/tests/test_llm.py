"""Offline checks for fine-tuned model routing and cache isolation."""
import json
import pathlib
import sys
from types import SimpleNamespace

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from brainbob import llm


def test_role_override_keeps_judge_fixed(monkeypatch):
    monkeypatch.setenv("BRAINBOB_CURATOR_MODEL", "bonan-checkpoint-1")
    monkeypatch.setenv("BRAINBOB_CURATOR_BASE_URL", "http://localhost:9000/v1/")
    monkeypatch.setenv("BRAINBOB_CURATOR_EXTRA_BODY", "null")
    monkeypatch.setenv("BRAINBOB_CURATOR_API_KEY", "test-secret")
    cfg = llm.configuration()
    assert cfg["curator"]["model"] == "bonan-checkpoint-1"
    assert cfg["curator"]["base_url"] == "http://localhost:9000/v1"
    assert cfg["curator"]["extra_body"] is None
    assert cfg["judge"]["model"] == "openai/gpt-oss-120b"
    assert cfg["judge"]["base_url"] == llm.DEFAULT_BASE_URL
    assert "test-secret" not in json.dumps(cfg)


def test_client_isolated_by_endpoint_and_credential(monkeypatch):
    monkeypatch.setattr(llm, "_clients", {})
    monkeypatch.setattr(llm, "OpenAI", lambda **kw: SimpleNamespace(**kw))
    monkeypatch.setenv("BRAINBOB_API_KEY", "default-secret")
    monkeypatch.setenv("BRAINBOB_AGENT_API_KEY", "candidate-secret")
    monkeypatch.setenv("BRAINBOB_AGENT_BASE_URL", "http://localhost:9000/v1")
    candidate = llm._get_client("agent")
    judge = llm._get_client("judge")
    assert candidate.base_url == "http://localhost:9000/v1"
    assert candidate.api_key == "candidate-secret"
    assert judge.api_key == "default-secret"
    assert candidate is llm._get_client("agent")
    monkeypatch.setenv("BRAINBOB_AGENT_API_KEY", "new-secret")
    assert candidate is not llm._get_client("agent")


def test_cache_separates_endpoint_and_checkpoint(monkeypatch, tmp_path):
    calls = []
    def create(**request):
        calls.append(request)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=f"answer-{len(calls)}"))],
                               usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1))
    fake = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(llm, "_get_client", lambda role: fake)
    monkeypatch.setattr(llm, "CACHE", str(tmp_path))
    monkeypatch.setattr(llm, "_USAGE", [])
    messages = [{"role": "user", "content": "hello"}]
    assert llm.complete("agent", messages) == "answer-1"
    assert llm.complete("agent", messages) == "answer-1"
    monkeypatch.setenv("BRAINBOB_AGENT_BASE_URL", "http://localhost:9000/v1")
    assert llm.complete("agent", messages) == "answer-2"
    monkeypatch.setenv("BRAINBOB_AGENT_CACHE_NAMESPACE", "checkpoint-sha-2")
    assert llm.complete("agent", messages) == "answer-3"
    assert llm.complete("agent", messages, fresh=True) == "answer-4"
    assert len(calls) == 4
