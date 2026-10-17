"""Dynamic policy in brainbob.acl + the bobbench BrainBob adapter (fake llm, no network)."""
import importlib, json, pathlib, re, sys

import pytest

BACKEND = pathlib.Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))
from brainbob import llm  # noqa: E402
from brainbob.acl import Member, Org  # noqa: E402

ORG_JSON = BACKEND / "fixtures" / "rusty_rod" / "org.json"


def _adapter_mod():
    return importlib.import_module("bobbench.adapters.brainbob")


# ---------------------------------------------------------------- acl: legacy unchanged
def test_legacy_at_none_and_at_given_unchanged():
    org = Org.load(ORG_JSON)
    for at in (None, "2026-10-01", "2030-01-01T00:00:00Z"):
        assert org.can_read("sales-01", "rusty-rod/sales", at) and not org.can_read("sales-01", "rusty-rod/engineering", at)
        assert org.can_approve("exec-01", "rusty-rod", at) and not org.can_approve("sales-01", "rusty-rod", at)
        assert org.can_approve("sales-01", "rusty-rod/sales", at)
    assert org.readable_scopes("sales-01") == ["rusty-rod", "rusty-rod/sales", "rusty-rod/sales/sales-01"]


def test_legacy_member_transfer():
    org = Org.load(ORG_JSON)
    org.apply({"op": "member_remove", "subject": "sales-01", "object": "rusty-rod/sales", "effective_at": "2026-10-05"})
    org.apply({"op": "member_add", "subject": "sales-01", "object": "rusty-rod/engineering", "effective_at": "2026-10-05"})
    assert org.can_read("sales-01", "rusty-rod/sales", "2026-10-04T23:59:59Z")
    assert not org.can_read("sales-01", "rusty-rod/sales", "2026-10-05")
    assert not org.can_read("sales-01", "rusty-rod/sales") and org.can_read("sales-01", "rusty-rod/engineering")
    assert not org.can_approve("sales-01", "rusty-rod/sales", "2026-10-06")
    assert not org.can_read("sales-01", "rusty-rod/engineering", "2026-10-04")
    assert org.can_read("sales-01", "rusty-rod", "2026-10-06")  # org scope untouched
    assert org.readable_scopes("sales-01", "2026-10-06") == ["rusty-rod", "rusty-rod/sales/sales-01", "rusty-rod/engineering"]


# ---------------------------------------------------------------- acl: dynamic
WORLD = {
    "world_id": "w-test", "organizations": [{"id": "acme", "name": "Acme"}, {"id": "beta", "name": "Beta"}],
    "principals": [{"id": "acme:alice", "org": "acme", "kind": "person"}, {"id": "acme:bob", "org": "acme", "kind": "person"},
                   {"id": "beta:carol", "org": "beta", "kind": "person"}],
    "scopes": [{"id": "acme", "org": "acme", "kind": "organization"}, {"id": "acme/sales", "org": "acme", "kind": "team"},
               {"id": "acme/eng", "org": "acme", "kind": "team"},
               {"id": "acme/eng/bob", "org": "acme", "kind": "individual", "owner": "acme:bob"},
               {"id": "shared/acme--beta", "org": None, "kind": "channel"}],
}


def P(seq, op, sub, obj, at, **kw):
    return {"type": "policy", "policy_id": f"p{seq}", "seq": seq, "issuer": "harness", "op": op, "subject": sub,
            "object": obj, "effective_at": at, "permissions": kw.get("permissions", []),
            "expires_at": kw.get("expires_at"), "purpose": kw.get("purpose")}


def test_membership_window_and_timezones():
    org = Org.from_world(WORLD)
    assert not org.can_read("acme:alice", "acme/sales", "2026-10-02")  # principal org alone gives nothing
    org.apply(P(1, "member_add", "acme:alice", "acme/sales", "2026-10-02T09:00:00-07:00", expires_at="2026-10-10T00:00:00Z"))
    assert not org.can_read("acme:alice", "acme/sales", "2026-10-02T15:59:59Z")
    assert org.can_read("acme:alice", "acme/sales", "2026-10-02T16:00:00Z")      # = 09:00 -07:00, start inclusive
    assert org.can_write("acme:alice", "acme/sales", "2026-10-05")
    assert not org.can_read("acme:alice", "acme/sales", "2026-10-10T00:00:00Z")  # expiry exclusive
    assert org.can_read("acme:alice", "acme/sales")                              # at=None: latest state, not closed
    assert not org.can_read("acme:alice", "acme", "2026-10-05") and not org.can_read("acme:alice", "acme/sales/x", "2026-10-05")
    assert not org.can_approve("acme:alice", "acme/sales", "2026-10-05")         # membership never approves
    assert org.can_read("acme:bob", "acme/eng/bob", "2026-01-01") and not org.can_read("acme:alice", "acme/eng/bob", "2026-10-05")
    assert not org.can_read("nobody", "acme/sales", "2026-10-05")


def test_future_effective_and_remove():
    org = Org.from_world(WORLD)
    org.apply(P(1, "member_add", "acme:bob", "acme/eng", "2026-10-10"))
    assert not org.can_read("acme:bob", "acme/eng", "2026-10-09") and org.can_read("acme:bob", "acme/eng", "2026-10-10")
    r = org.apply(P(2, "member_remove", "acme:bob", "acme/eng", "2026-10-20"))
    assert r["entries_changed"] == 1 and r["applied"]
    assert org.can_read("acme:bob", "acme/eng", "2026-10-19") and not org.can_read("acme:bob", "acme/eng", "2026-10-20")
    assert not org.can_read("acme:bob", "acme/eng")
    org.apply(P(3, "member_add", "acme:bob", "acme/eng", "2026-11-01"))  # re-join later
    assert not org.can_read("acme:bob", "acme/eng", "2026-10-25") and org.can_read("acme:bob", "acme/eng", "2026-11-02")


def test_grant_purpose_expiry_and_partial_revoke():
    org = Org.from_world(WORLD)
    org.apply(P(1, "grant", "beta:carol", "shared/acme--beta", "2026-10-01", permissions=["read", "write"],
                expires_at="2026-10-10", purpose="pilot-delivery"))
    assert org.can_read("beta:carol", "shared/acme--beta", "2026-10-05", purpose="pilot-delivery")
    assert not org.can_read("beta:carol", "shared/acme--beta", "2026-10-05", purpose="marketing")
    assert not org.can_read("beta:carol", "shared/acme--beta", "2026-10-05")  # purpose-bound grant needs the purpose
    assert not org.can_read("beta:carol", "shared/acme--beta", "2026-10-10", purpose="pilot-delivery")
    org.apply(P(2, "revoke", "beta:carol", "shared/acme--beta", "2026-10-04", permissions=["write"]))
    assert org.can_write("beta:carol", "shared/acme--beta", "2026-10-03", purpose="pilot-delivery")
    assert not org.can_write("beta:carol", "shared/acme--beta", "2026-10-05", purpose="pilot-delivery")
    assert org.can_read("beta:carol", "shared/acme--beta", "2026-10-05", purpose="pilot-delivery")  # read kept
    assert not org.can_read("beta:carol", "shared/acme--beta", "2026-10-11", purpose="pilot-delivery")  # same expiry
    org.apply(P(3, "revoke", "beta:carol", "shared/acme--beta", "2026-10-06"))  # all permissions
    assert not org.can_read("beta:carol", "shared/acme--beta", "2026-10-07", purpose="pilot-delivery")
    assert org.can_read("beta:carol", "shared/acme--beta", "2026-10-05", purpose="pilot-delivery")  # history stays
    assert not org.can_read("acme:alice", "shared/acme--beta", "2026-10-05", purpose="pilot-delivery")


def test_approver_and_grant_approve():
    org = Org.from_world(WORLD)
    org.apply(P(1, "approver", "acme:bob", "acme", "2026-10-01", expires_at="2026-12-01"))
    org.apply(P(2, "grant", "acme:alice", "acme/sales", "2026-10-01", permissions=["approve"]))
    assert org.can_approve("acme:bob", "acme", "2026-10-01") and not org.can_approve("acme:bob", "acme", "2026-09-30")
    assert not org.can_approve("acme:bob", "acme", "2026-12-01") and not org.can_read("acme:bob", "acme", "2026-10-05")
    assert org.can_approve("acme:alice", "acme/sales", "2026-10-02") and not org.can_read("acme:alice", "acme/sales", "2026-10-02")
    org.apply(P(3, "revoke", "acme:bob", "acme", "2026-10-15", permissions=["approve"]))
    assert org.can_approve("acme:bob", "acme", "2026-10-14") and not org.can_approve("acme:bob", "acme", "2026-10-16")
    assert org.can("acme:alice", "approve", "acme/sales", "2026-10-02") and not org.can("acme:alice", "publish", "acme/sales", "2026-10-02")
    v = org.view("2026-10-14")
    assert v.can_approve("acme:bob", "acme") and "acme:bob" in v.members
    v.at = "2026-10-16"
    assert not v.can_approve("acme:bob", "acme")
    with pytest.raises(ValueError):
        org.apply(P(4, "bogus", "acme:bob", "acme", "2026-10-01"))
    with pytest.raises(ValueError):
        org.apply(P(5, "grant", "acme:bob", "acme", "2026-10-01", permissions=["erase"]))
    assert [r["policy_id"] for r in org.export()["log"]] == ["p1", "p2", "p3"]


def test_old_member_constructor_still_works():
    org = Org([Member("a", "sales"), Member("b", "eng", "approver")], "x")
    assert org.readable_scopes("a") == ["x", "x/sales", "x/sales/a"] and org.can_approve("b", "x")


# ---------------------------------------------------------------- adapter
def fake_complete(role, messages, fresh=False, **kw):
    content = messages[-1]["content"]
    if role.startswith("curator"):
        s = content.split("SESSION:\n", 1)[1].strip()
        return json.dumps([s.split(": ", 1)[1] if ": " in s else s])
    if role == "judge":
        return '{"verdict": "unrelated", "reason": "fake"}' if "candidate" in content else '{"verdict": "insufficient", "reason": "fake"}'
    raise AssertionError(f"unexpected core model role: {role}")


def fake_shared_answer(task, context, **kwargs):
    return {"answer": "fake answer", "cited_event_ids": re.findall(r"^\[(evt-\d+)\]", context, re.M),
            "cost": {"calls": 0, "usd": 0.0}}


def S(seq, eid, actor, audience, at, content):
    return {"type": "source", "event_id": eid, "seq": seq, "actor_id": actor, "occurred_at": at, "received_at": at,
            "effective_at": at, "audience": audience, "source_id": f"src-{eid}", "source_revision": 1,
            "channel": "trusted", "content": content}


@pytest.fixture
def adapter(monkeypatch, tmp_path, request):
    monkeypatch.setattr(llm, "complete", fake_complete)
    mod = _adapter_mod()
    assert mod.llm is llm  # one shared core configuration/usage identity
    a = mod.BrainBobAdapter(mode=request.param, answer_fn=fake_shared_answer)
    a.reset(WORLD, {"context_tokens": 4000}, str(tmp_path))
    for e in [P(1, "member_add", "acme:alice", "acme/sales", "2026-10-01"),
              P(2, "member_add", "acme:bob", "acme/eng", "2026-10-01"),
              P(3, "approver", "acme:bob", "acme/eng", "2026-10-01"),
              P(4, "grant", "beta:carol", "shared/acme--beta", "2026-10-01", permissions=["read"], expires_at="2026-10-10")]:
        assert a.apply_policy(e)["applied"]
    r1 = a.ingest(S(5, "evt-1", "acme:alice", ["acme/sales"], "2026-10-02T10:00:00Z", "Q4 sales target is forty deals."))
    r2 = a.ingest(S(6, "evt-2", "acme:bob", ["acme/eng"], "2026-10-02T11:00:00Z", "Release date is November 13."))
    r3 = a.ingest(S(7, "evt-3", "acme:alice", ["shared/acme--beta", "acme/sales"], "2026-10-03T09:00:00Z",
                    "Beta kickoff is October 20."))
    assert r1["episodes"][0]["authority"] == "discussion" and r2["episodes"][0]["authority"] == "approved"
    assert [e["scope"] for e in r3["episodes"]] == ["shared/acme--beta", "acme/sales"]
    return a


BOTH = pytest.mark.parametrize("adapter", ["append_only", "maintained"], indirect=True)


@BOTH
def test_adapter_flow_and_transfer(adapter):
    a = adapter
    m = a.maintain(7, {})
    assert m["ok"] and m["operation"] == "write_time_only" and m["mode"] == a.mode
    s = a.open_session("acme:alice", "What is the sales target and the release date?", "2026-10-05T00:00:00Z", None, {"context_tokens": 4000})
    assert set(s["source_ids"]) == {"evt-1", "evt-3"} and "November 13" not in s["context"]
    assert "forty deals" in s["context"] and s["context_tokens"] > 0 and s["context_tokens"] <= 4000
    out = a.act(s, "What is the sales target and the release date?")
    assert out["answer"] == "fake answer" and set(out["cited_event_ids"]) == {"evt-1", "evt-3"} and "usd" in out["cost"]
    a.close_session(s)
    # alice moves from sales to eng
    a.apply_policy(P(8, "member_remove", "acme:alice", "acme/sales", "2026-10-06"))
    a.apply_policy(P(9, "member_add", "acme:alice", "acme/eng", "2026-10-06"))
    s2 = a.open_session("acme:alice", "What is the sales target and the release date?", "2026-10-07T00:00:00Z", None, {"context_tokens": 4000})
    assert s2["source_ids"] == ["evt-2"] and "forty deals" not in s2["context"] and "Beta kickoff" not in s2["context"]
    assert a.act(s2, "What is the sales target and the release date?")["cited_event_ids"] == ["evt-2"]
    # an old session acted on after a backdated revoke is rechecked, not reused
    s_old = a.open_session("acme:alice", "sales target", "2026-10-05T12:00:00Z", None, {})
    a.apply_policy(P(10, "member_remove", "acme:alice", "acme/sales", "2026-10-05"))
    o = a.act(s_old, "sales target")
    assert o["error"] == "policy changed; reopen session"
    assert "evt-1" not in o["cited_event_ids"] and "forty deals" not in s_old["context"]
    t = a.export_trace()
    assert t["mode"] == a.mode and t["model_configuration"]["agent"]["model"]
    assert any(m["origin"] == "evt-1" for m in t["memories"])
    assert t["acts"] and t["operations"]


@BOTH
def test_adapter_grant_expiry(adapter):
    a = adapter
    s = a.open_session("beta:carol", "When is the Beta kickoff?", "2026-10-05T00:00:00Z", None, {})
    assert s["source_ids"] == ["evt-3"] and "October 20" in s["context"]
    s2 = a.open_session("beta:carol", "When is the Beta kickoff?", "2026-10-10T00:00:00Z", None, {})
    assert s2["source_ids"] == [] and "October 20" not in s2["context"]
    assert a.act(s2, "When is the Beta kickoff?")["cited_event_ids"] == []


@BOTH
def test_adapter_declares_unsupported_surfaces_and_scopes_context(adapter):
    # The implemented adapter is a core component, not an HTTP test client.
    # Unsupported surfaces are an explicit readiness gap, never a passed probe.
    a = adapter
    a.apply_policy(P(8, "member_remove", "acme:alice", "acme/sales", "2026-10-06"))
    before = a.open_session("acme:alice", "sales target", "2026-10-05", None, {})
    after = a.open_session("acme:alice", "sales target", "2026-10-07", None, {})
    assert "forty deals" in before["context"] and "evt-1" in before["source_ids"]
    assert "forty deals" not in after["context"] and "evt-1" not in after["source_ids"]
    unknown = a.open_session("nobody", "sales target", "2026-10-05", None, {})
    assert unknown["source_ids"] == [] and "forty deals" not in unknown["context"]
    for surface in ("search", "record", "source", "history", "events", "export", "session_cache"):
        assert a.inspect_surface("acme:alice", surface, {"event_id": "evt-1", "at": "2026-10-07"}) is None


# ---------------------------------------------------------------- acl: group subjects, channels, parity
def test_group_subjects_channels_and_manifest_memberships():
    w = dict(WORLD, memberships=[{"principal": "acme:bob", "scope": "acme", "since": "2026-09-01", "until": "2026-11-01"}])
    org = Org.from_world(w)
    assert org.can_read("acme:bob", "acme", "2026-10-01") and not org.can_read("acme:bob", "acme", "2026-11-01")
    org.apply(P(1, "member_add", "acme:alice", "shared/acme--beta", "2026-10-01"))
    assert not org.can_read("acme:alice", "shared/acme--beta", "2026-10-02")  # channel: grants only
    org.apply(P(2, "grant", "beta", "shared/acme--beta", "2026-10-01", permissions=["read"]))       # org subject
    org.apply(P(3, "member_add", "acme:alice", "acme/sales", "2026-10-01"))
    org.apply(P(4, "grant", "acme/sales", "shared/acme--beta", "2026-10-01", permissions=["read"]))  # scope subject
    org.apply(P(5, "member_remove", "acme:alice", "acme/sales", "2026-10-05"))
    assert org.can_read("beta:carol", "shared/acme--beta", "2026-10-02") and not org.can_read("acme:bob", "shared/acme--beta", "2026-10-02")
    assert org.can_read("acme:alice", "shared/acme--beta", "2026-10-04") and not org.can_read("acme:alice", "shared/acme--beta", "2026-10-06")
    assert "beta" not in org.members and "acme/sales" not in org.members


def test_read_and_approve_match_reference_policy():
    sys.path.insert(0, str(ROOT))
    policy = pytest.importorskip("bobbench.policy")
    evs = [P(1, "member_add", "acme:alice", "acme/sales", "2026-10-01T08:00:00-07:00"),
           P(2, "member_add", "acme:bob", "acme", "2026-10-01"),
           P(3, "approver", "acme:bob", "acme", "2026-10-02", expires_at="2026-10-20"),
           P(4, "grant", "beta:carol", "shared/acme--beta", "2026-10-01", permissions=["read", "approve"],
             expires_at="2026-10-15", purpose="pilot"),
           P(5, "grant", "acme/sales", "shared/acme--beta", "2026-10-03", permissions=["read"]),
           P(6, "member_add", "acme:alice", "shared/acme--beta", "2026-10-01"),
           P(7, "revoke", "beta:carol", "shared/acme--beta", "2026-10-10", permissions=["approve"]),
           P(8, "member_remove", "acme:alice", "acme/sales", "2026-10-08"),
           P(9, "member_add", "acme:alice", "acme/eng", "2026-10-08"),
           P(10, "revoke", "acme:bob", "acme", "2026-10-12")]
    ref, org = policy.Policy(WORLD), Org.from_world(WORLD)
    for e in evs:
        ref.apply(e); org.apply(e)
    times = ["2026-09-30", "2026-10-01T15:00:00Z", "2026-10-02", "2026-10-04", "2026-10-09", "2026-10-11", "2026-10-13", "2026-10-16", "2026-10-21"]
    n = 0
    for p in [x["id"] for x in WORLD["principals"]]:
        for s in [x["id"] for x in WORLD["scopes"]]:
            for t in times:
                for pur in (None, "pilot", "other"):
                    for perm in ("read", "approve"):
                        assert org.can(p, perm, s, t, pur) == ref.can(p, perm, s, t, pur), (p, perm, s, t, pur)
                        n += 1
    assert n == 3 * 5 * 9 * 3 * 2
