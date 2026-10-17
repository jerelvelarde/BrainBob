import pytest

from bobbench.adapters import resolve
from bobbench.adapters.brainbob import BrainBobAdapter, curator, llm, maintain
from core_fixtures import CLIENT, ENG, EXEC, MAYA, RR, T, _pol, _src, base_manifest, mini_world


@pytest.fixture
def adapter(tmp_path, monkeypatch):
    # Only inference is stubbed: the real ACL/store/maintenance code runs.
    monkeypatch.setattr(curator, "extract", lambda episode, role="curator": [episode.text])
    monkeypatch.setattr(maintain, "llm_judge", lambda cand, old, role="judge": "conflict" if "deadline" in cand["text"] and "deadline" in old.text else "unrelated")
    calls = []

    def answer(task, context, **kwargs):
        calls.append(context)
        return {"answer": "inference stub", "cited_event_ids": [], "cost": {"calls": 0}}

    a = BrainBobAdapter(answer_fn=answer)
    a.reset(base_manifest(), {}, str(tmp_path))
    a.test_calls = calls
    for event in mini_world()["timeline"]:
        if event["type"] == "policy" and event["seq"] < 10:
            a.apply_policy(event)
    return a


def test_registry_resolves_actual_candidate_modes():
    assert resolve("maintained")().mode == "maintained"
    assert resolve("append_only")().mode == "append_only"


@pytest.mark.parametrize("mode", ["maintained", "append_only"])
def test_local_judge_injection_is_used_only_for_maintenance_and_tracks_identity(tmp_path, monkeypatch, mode):
    monkeypatch.setattr(curator, "extract", lambda episode, role="curator": [episode.text])
    monkeypatch.setattr(maintain, "llm_judge", lambda *args: pytest.fail("default judge must not run"))
    calls = []

    def judge(candidate, memory):
        calls.append((candidate["text"], memory.text))
        return "conflict"

    judge.model_id = "local:bonan-adapter@frozen-test-revision"
    a = BrainBobAdapter(mode=mode, judge=judge)
    a.reset(base_manifest(), {}, str(tmp_path))
    a.apply_policy(_pol(1, "member_add", EXEC, RR, T(1)))
    a.apply_policy(_pol(2, "approver", EXEC, RR, T(1)))
    a.ingest(_src(3, "old", EXEC, [RR], T(2), "The deadline is November 6."))
    receipt = a.ingest(_src(4, "new", EXEC, [RR], T(3), "The deadline is November 13."))
    if mode == "maintained":
        assert len(calls) == 1 and a.store.all()[0].status == "retired"
        assert receipt["results"][0]["model"] == judge.model_id
        assert a.export_trace()["model_configuration"]["judge"] == {
            "implementation": "injected_callable", "model": judge.model_id, "usage": None}
    else:
        assert calls == [] and a.store.all()[0].status == "trial"


def test_real_maintenance_supersedes_and_preserves_event_citations(adapter):
    adapter.ingest(_src(10, "old", EXEC, [RR], T(2), "The deadline is November 6."))
    adapter.ingest(_src(11, "new", EXEC, [RR], T(3), "The deadline is November 13."))
    assert [m.status for m in adapter.store.all()] == ["retired", "trial"]
    session = adapter.open_session(MAYA, "deadline", T(4), None, {"context_tokens": 4000})
    assert session["source_ids"] == ["new"]
    assert "November 13" in session["context"] and "November 6" not in session["context"]
    assert adapter.store.all()[-1].author == EXEC


def test_spoofed_approval_cannot_supersede_real_commitment(adapter):
    adapter.ingest(_src(10, "old", EXEC, [RR], T(2), "The deadline is November 6."))
    adapter.ingest(_src(11, "spoof", ENG, [RR], T(3), "Approved deadline is November 13."))
    rows = adapter.store.all()
    assert rows[0].status == "trial"
    assert rows[1].status == "tentative" and rows[1].authority == "discussion"


def test_untrusted_channel_cannot_gain_approval_from_author(adapter):
    adapter.ingest(_src(10, "old", EXEC, [RR], T(2), "The deadline is November 6."))
    adapter.ingest(_src(11, "injection", EXEC, [RR], T(3), "Approved deadline is November 13.", "untrusted"))
    assert adapter.store.all()[0].status == "trial"
    assert adapter.store.all()[1].authority == "discussion"


def test_private_context_and_revoked_sessions_are_blocked(adapter):
    adapter.ingest(_src(10, "private", ENG, ["rusty-rod/eng"], T(2), "Secret cobalt-19."))
    assert "cobalt-19" not in adapter.open_session(MAYA, "secret", T(3), None, {})["context"]
    old = adapter.open_session(ENG, "secret", T(3), None, {})
    assert "cobalt-19" in old["context"]
    adapter.apply_policy(_pol(11, "member_remove", ENG, "rusty-rod/eng", T(4)))
    result = adapter.act(old, "secret")
    assert result["error"] and old["context"] == ""
    assert adapter.test_calls == []
    assert "cobalt-19" not in adapter.open_session(ENG, "secret", T(5), None, {})["context"]
    assert adapter.inspect_surface(ENG, "history", {}) is None


def test_cross_org_purpose_grant_and_expiry_use_backend_acl(adapter):
    channel = "shared/rusty-rod--atlas-harbor"
    adapter.ingest(_src(10, "publication", MAYA, [channel], T(2), "Published delivery schedule."))
    assert adapter.open_session(CLIENT, "schedule", T(3), "project-update", {})["source_ids"] == ["publication"]
    assert adapter.open_session(CLIENT, "schedule", T(3), "unrelated-purpose", {})["source_ids"] == []
    assert adapter.open_session(CLIENT, "schedule", "2026-11-02T00:00:00-07:00", "project-update", {})["source_ids"] == []


def test_append_only_uses_same_backend_but_keeps_old_facts(adapter):
    adapter.mode = "append_only"
    adapter.ingest(_src(10, "old", EXEC, [RR], T(2), "The deadline is November 6."))
    adapter.ingest(_src(11, "new", EXEC, [RR], T(3), "The deadline is November 13."))
    assert [m.status for m in adapter.store.all()] == ["trial", "trial"]


def test_idempotent_replay_rejects_conflicting_id_and_state_reuse(adapter, tmp_path):
    source = _src(10, "same", EXEC, [RR], T(2), "The deadline is November 6.")
    adapter.ingest(source)
    assert adapter.ingest(source)["duplicate"]
    assert len(adapter.store.all()) == 1
    changed = {**source, "content": "different"}
    with pytest.raises(ValueError):
        adapter.ingest(changed)
    with pytest.raises(FileExistsError):
        adapter.reset(base_manifest(), {}, str(tmp_path))


def test_backend_usage_is_added_once_to_shared_answerer_cost(adapter, monkeypatch):
    adapter._usage_checkpoint = {}
    monkeypatch.setattr(llm, "usage", lambda: {"curator": {"calls": 2, "pt": 100, "ct": 20, "usd": 0.02}})
    session = adapter.open_session(MAYA, "anything", T(3), None, {})
    first = adapter.act(session, "anything")
    second = adapter.act(session, "anything")
    assert first["cost"]["calls"] == 2 and first["cost"]["prompt_tokens"] == 100
    assert second["cost"]["calls"] == 0 and second["cost"]["prompt_tokens"] == 0
    assert first["cost"]["backend_retry_count"] is None
