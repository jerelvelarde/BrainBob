from types import SimpleNamespace

from bobbench import answer as ans


def test_parse_reply_variants():
    assert ans.parse_reply("Date is Nov 13.\nCITED: evt-1, evt-2") == ("Date is Nov 13.", ["evt-1", "evt-2"])
    assert ans.parse_reply("x\n**CITED:** [evt-3]") == ("x", ["evt-3"])
    assert ans.parse_reply("x\nCITED: none") == ("x", [])
    assert ans.parse_reply("<think>hm</think>y\ncited: e1 e1") == ("y", ["e1"])
    assert ans.parse_reply("no citation line") == ("no citation line", [])


def test_messages_carry_envelope_and_ids():
    m = ans.build_messages("Do it", "[e4] fact", "p1", "2026-10-12", None)
    assert m[0]["content"] == ans.SYSTEM_PROMPT and "CITED:" in m[0]["content"]
    assert "[e4] fact" in m[1]["content"] and "Principal: p1" in m[1]["content"]
    assert "none stated" in m[1]["content"]


def test_answer_caches_by_request_and_salt(tmp_path, monkeypatch):
    calls = []

    class FakeCompletions:
        def create(self, **req):
            calls.append(req)
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="Nov 13\nCITED: e4"))],
                                   usage=SimpleNamespace(prompt_tokens=100, completion_tokens=10))

    fake = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    monkeypatch.setenv("BOBBENCH_CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(ans, "_get_client", lambda base_url: fake)
    r1 = ans.answer("t", "[e4] c", cache_salt="rep0")
    r2 = ans.answer("t", "[e4] c", cache_salt="rep0")
    r3 = ans.answer("t", "[e4] c", cache_salt="rep1")
    assert len(calls) == 2
    assert r1["answer"] == "Nov 13" and r1["cited_event_ids"] == ["e4"] and not r1["cost"]["cached"]
    assert r2["cost"]["cached"] and r2["cost"]["usd"] == 0 and r2["cost"]["usd_if_uncached"] > 0
    assert not r3["cost"]["cached"]
    req = calls[0]
    assert req["temperature"] == 0 and req["model"] == ans.DEFAULT_MODEL
    assert req["extra_body"] == {"chat_template_kwargs": {"enable_thinking": False}}
    assert "api_key" not in str(ans.config()).lower()
