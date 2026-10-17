import pytest

from bobbench.policy import Policy
from core_fixtures import AH, CHAN, CLIENT, ENG, EXEC, MAYA, RR, T, _pol, _src, base_manifest, mini_world


def P(*events):
    p = Policy(base_manifest())
    for e in events:
        p.apply(e)
    return p


def test_team_membership_is_time_aware():
    p = P(_pol(1, "member_add", MAYA, "rusty-rod/sales", T(5)))
    assert not p.can(MAYA, "read", "rusty-rod/sales", T(4))
    assert p.can(MAYA, "read", "rusty-rod/sales", T(5))
    assert not p.can(ENG, "read", "rusty-rod/sales", T(6))


def test_member_remove_ends_access_from_its_effective_time():
    p = P(_pol(1, "member_add", MAYA, "rusty-rod/sales", T(1)), _pol(2, "member_remove", MAYA, "rusty-rod/sales", T(10)))
    assert p.can(MAYA, "read", "rusty-rod/sales", T(9, 23))
    assert not p.can(MAYA, "read", "rusty-rod/sales", T(10))
    p.apply(_pol(3, "member_add", MAYA, "rusty-rod/sales", T(20)))
    assert not p.can(MAYA, "read", "rusty-rod/sales", T(15))
    assert p.can(MAYA, "read", "rusty-rod/sales", T(21))


def test_org_membership_reads_org_scope_only_and_is_never_implied():
    p = P(_pol(1, "member_add", MAYA, RR, T(1)))
    assert p.can(MAYA, "read", RR, T(2))
    assert not p.can(MAYA, "read", "rusty-rod/eng", T(2))
    assert not p.can(ENG, "read", RR, T(2))  # principal.org alone gives nothing
    assert not p.can(MAYA, "write", RR, T(2))


def test_individual_scope_owner_only():
    p = P(_pol(1, "member_add", ENG, "rusty-rod/sales/maya", T(1)))
    assert p.can(MAYA, "read", "rusty-rod/sales/maya", T(1))
    assert not p.can(ENG, "read", "rusty-rod/sales/maya", T(2))


def test_channel_only_through_grant_with_expiry():
    p = P(_pol(1, "member_add", CLIENT, CHAN, T(1)))
    assert not p.can(CLIENT, "read", CHAN, T(2))  # membership opens nothing on a channel
    p.apply(_pol(2, "grant", CLIENT, CHAN, T(5), ["read"], expires_at=T(20)))
    assert not p.can(CLIENT, "read", CHAN, T(4))
    assert p.can(CLIENT, "read", CHAN, T(5))
    assert p.can(CLIENT, "read", CHAN, T(19, 23))
    assert not p.can(CLIENT, "read", CHAN, T(20))  # expires_at is exclusive
    assert not p.can(CLIENT, "write", CHAN, T(10))


def test_purpose_limited_grant():
    p = P(_pol(1, "grant", CLIENT, CHAN, T(1), ["read"], purpose="project-update"))
    assert p.can(CLIENT, "read", CHAN, T(2), purpose="project-update")
    assert not p.can(CLIENT, "read", CHAN, T(2), purpose="marketing")
    assert not p.can(CLIENT, "read", CHAN, T(2))


def test_revoke_full_partial_and_regrant():
    p = P(_pol(1, "grant", ENG, CHAN, T(1), ["read", "write"]), _pol(2, "revoke", ENG, CHAN, T(10), ["write"]))
    assert p.can(ENG, "write", CHAN, T(9))
    assert not p.can(ENG, "write", CHAN, T(10))
    assert p.can(ENG, "read", CHAN, T(11))
    p.apply(_pol(3, "revoke", ENG, CHAN, T(12)))
    assert p.can(ENG, "read", CHAN, T(11))
    assert not p.can(ENG, "read", CHAN, T(12))
    p.apply(_pol(4, "grant", ENG, CHAN, T(14), ["read"]))
    assert not p.can(ENG, "read", CHAN, T(13))
    assert p.can(ENG, "read", CHAN, T(15))


def test_approval_comes_only_from_policy():
    p = P(_pol(1, "member_add", EXEC, RR, T(1)))
    assert not p.can(EXEC, "approve", RR, T(2))
    p.apply(_pol(2, "approver", EXEC, RR, T(3)))
    assert not p.can(EXEC, "approve", RR, T(2, 23))
    assert p.can(EXEC, "approve", RR, T(3))
    p.apply(_pol(3, "grant", ENG, RR, T(4), ["approve"], expires_at=T(6)))
    assert p.can(ENG, "approve", RR, T(5)) and not p.can(ENG, "approve", RR, T(6))
    assert not p.can(ENG, "read", RR, T(5))  # approve does not imply read
    p.apply(_pol(4, "revoke", EXEC, RR, T(8), ["approve"]))
    assert not p.can(EXEC, "approve", RR, T(9))


def test_grant_to_org_and_team_subjects():
    p = P(_pol(1, "grant", AH, CHAN, T(1), ["read"]),
          _pol(2, "member_add", ENG, "rusty-rod/eng", T(1)),
          _pol(3, "grant", "rusty-rod/eng", CHAN, T(1), ["write"]),
          _pol(4, "member_remove", ENG, "rusty-rod/eng", T(10)))
    assert p.can(CLIENT, "read", CHAN, T(2))
    assert not p.can(MAYA, "read", CHAN, T(2))
    assert p.can(ENG, "write", CHAN, T(5))
    assert not p.can(ENG, "write", CHAN, T(11))  # team grant follows current membership


def test_readable_events_and_replay_watermark():
    w = mini_world()
    p = Policy.replay(w, upto_seq=20)
    ids = [e["event_id"] for e in p.readable_events(MAYA, T(12), "client-update")]
    assert ids == ["e1", "e3", "e4"]
    assert [e["event_id"] for e in p.readable_events(CLIENT, T(12), "project-update")] == ["e5"]
    assert p.readable_events(CLIENT, T(12)) == []  # purpose-limited grant
    assert [e["event_id"] for e in p.readable_events(ENG, T(12))] == ["e1", "e2", "e4"]
    # the member_remove at seq 22 is not applied before seq 20 ...
    assert p.can(MAYA, "read", RR, T(15))
    # ... and is applied afterwards
    p2 = Policy.replay(w, upto_seq=24)
    assert not p2.can(MAYA, "read", RR, T(15))
    assert [e["event_id"] for e in p2.readable_events(MAYA, T(15))] == ["e3"]
    assert p2.can(MAYA, "read", RR, T(13))  # historical time: still a member then


def test_can_read_any_audience_scope_and_unknowns():
    p = P(_pol(1, "member_add", MAYA, "rusty-rod/sales", T(1)))
    e = _src(2, "x", ENG, ["rusty-rod/eng", "rusty-rod/sales"], T(2), "hi")
    assert p.can_read(MAYA, e, T(3))
    assert not p.can_read(ENG, e, T(3))
    assert not p.can(MAYA, "read", "nope", T(3))
    assert not p.can("ghost", "read", "rusty-rod/sales", T(3))


def test_out_of_order_apply_rejected():
    p = P(_pol(5, "member_add", MAYA, RR, T(1)))
    with pytest.raises(ValueError):
        p.apply(_pol(4, "member_add", ENG, RR, T(1)))
