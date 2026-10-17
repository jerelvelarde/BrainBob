"""Write-time maintenance: every row of the SPEC rule table, the Atlas scenario, and the supporting store/agent changes.
No network: curator.extract and the judge are faked."""
import sys, pathlib, json, re
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import pytest
from brainbob import events, curator, maintain, agent, llm
from brainbob.memory import MemoryStore
from brainbob.types import Episode, Memory

ORG = "rusty-rod"
TEAM = {"exec-01": "executive", "exec-02": "executive", "sales-01": "sales", "eng-01": "engineering", "eng-02": "engineering"}
JM = llm._roles()["judge"]["model"]
CM = llm._roles()["curator"]["model"]


class FakeACL:
    """Same policy as SPEC: org, own team, own individual path readable; org approval needs exec."""
    def __init__(self): self.calls = []
    def _paths(self, m): return [ORG, f"{ORG}/{TEAM[m]}", f"{ORG}/{TEAM[m]}/{m}"] if m in TEAM else []
    def can_read(self, m, scope): self.calls.append(("read", m, scope)); return scope in self._paths(m)
    def can_approve(self, m, scope):
        self.calls.append(("approve", m, scope))
        if m not in TEAM: return False
        if scope == ORG: return TEAM[m] == "executive"
        return scope in self._paths(m)[1:]


def date_judge(cand, mem):
    """Atlas-style judge: same subject (atlas + pilot) -> same if the day matches, else conflict; otherwise unrelated."""
    a, b = cand["text"].lower(), mem.text.lower()
    if "atlas" in a and "atlas" in b and "pilot" in a and "pilot" in b:
        da, db = re.findall(r"november (\d+)", a), re.findall(r"november (\d+)", b)
        return "same" if da == db else "conflict"
    return "unrelated"


@pytest.fixture(autouse=True)
def fresh_events(tmp_path):
    events.reset(); events.set_log(str(tmp_path / "events.jsonl"))
    yield
    events.reset()


@pytest.fixture
def facts(monkeypatch):
    table = {}
    monkeypatch.setattr(curator, "extract", lambda ep, role="curator": list(table[ep.id]))
    return table


def ep(eid, author, scope, authority, date, text="x"):
    return Episode(eid, text, date, "test", author=author, scope=scope, authority=authority)


def types_since(seq):
    return [e["type"] for e in events.history(after=seq)]


def last_seq():
    h = events.history(); return h[-1]["seq"] if h else 0


def seed(store, facts, acl, text="The Atlas client pilot is due November 6, 2026.", date="2026-10-01"):
    facts["e0"] = [text]
    d = maintain.ingest(ep("e0", "exec-01", ORG, "approved", date), store, acl, judge=date_judge)
    assert [x.action for x in d] == ["add"]
    return store.get(d[0].memory_id)


# ---------- rule table ----------

def test_same_is_dropped_as_duplicate(facts):
    s, acl = MemoryStore(), FakeACL(); old = seed(s, facts, acl)
    facts["e1"] = ["Atlas pilot deadline: November 6, 2026 (confirmed)."]
    n = last_seq()
    d = maintain.ingest(ep("e1", "sales-01", f"{ORG}/sales", "discussion", "2026-10-05"), s, acl, judge=date_judge)
    assert d[0].action == "reject" and d[0].related == [old.id] and d[0].model == JM
    rej = [e for e in events.history(after=n) if e["type"] == "memory.rejected"]
    assert rej and rej[0]["reason"] == "duplicate" and rej[0]["model"] == JM
    assert "memory.added" not in types_since(n) and len(s.all()) == 1


def test_conflict_approved_authorized_newer_supersedes(facts):
    s, acl = MemoryStore(), FakeACL(); old = seed(s, facts, acl)
    facts["e1"] = ["The Atlas client pilot is now due November 13, 2026."]
    n = last_seq()
    d = maintain.ingest(ep("e1", "exec-02", ORG, "approved", "2026-10-15"), s, acl, judge=date_judge)
    new = s.get(d[0].memory_id)
    assert d[0].action == "supersede" and new.supersedes == old.id and new.status == "trial"
    assert s.get(old.id).status == "retired" and s.get(old.id).reason == f"superseded by {new.id}"
    t = types_since(n)
    assert t.index("memory.added") < t.index("memory.retired") < t.index("memory.corrected")
    ret = next(e for e in events.history(after=n) if e["type"] == "memory.retired")
    assert ret["reason"] == f"superseded by {new.id}" and ret["model"] == JM
    added = next(e for e in events.history(after=n) if e["type"] == "memory.added")
    assert added["memory"]["supersedes"] == old.id and added["model"] == CM and added["memory"]["model"] == CM


def test_conflict_approved_but_older_is_rejected_stale(facts):
    s, acl = MemoryStore(), FakeACL(); old = seed(s, facts, acl, date="2026-10-15")
    facts["e1"] = ["The Atlas client pilot is due November 13, 2026."]
    n = last_seq()
    d = maintain.ingest(ep("e1", "exec-02", ORG, "approved", "2026-10-01"), s, acl, judge=date_judge)
    assert d[0].action == "reject" and "stale" in d[0].reason and d[0].related == [old.id]
    rej = [e for e in events.history(after=n) if e["type"] == "memory.rejected"]
    assert rej[0]["reason"] == "stale" and rej[0]["model"] == JM
    assert s.get(old.id).status == "trial" and len(s.all()) == 1


@pytest.mark.parametrize("authority", ["tentative", "discussion"])
def test_conflict_not_approved_becomes_tentative(facts, authority):
    s, acl = MemoryStore(), FakeACL(); old = seed(s, facts, acl)
    facts["e1"] = ["Engineering estimates the Atlas pilot for November 13, 2026."]
    n = last_seq()
    d = maintain.ingest(ep("e1", "eng-01", f"{ORG}/engineering", authority, "2026-10-10"), s, acl, judge=date_judge)
    new = s.get(d[0].memory_id)
    assert d[0].action == "tentative" and new.status == "tentative" and new.conflicts_with == [old.id]
    assert s.get(old.id).status == "trial"
    conf = [e for e in events.history(after=n) if e["type"] == "memory.conflict"]
    assert conf == [conf[0]] and conf[0]["new_id"] == new.id and conf[0]["old_id"] == old.id and conf[0]["model"] == JM
    assert "memory.retired" not in types_since(n)


def test_conflict_approved_by_non_approver_becomes_tentative(facts):
    """eng-01 can approve its own team scope, not the org memory it conflicts with."""
    s, acl = MemoryStore(), FakeACL(); old = seed(s, facts, acl)
    facts["e1"] = ["The Atlas client pilot is due November 13, 2026."]
    n = last_seq()
    d = maintain.ingest(ep("e1", "eng-01", f"{ORG}/engineering", "approved", "2026-10-20"), s, acl, judge=date_judge)
    new = s.get(d[0].memory_id)
    assert d[0].action == "tentative" and new.status == "tentative" and new.authority == "approved"
    assert s.get(old.id).status == "trial" and "memory.conflict" in types_since(n) and "memory.retired" not in types_since(n)


def test_approved_claim_without_approval_rights_is_downgraded(facts):
    """eng-01 writes 'approved' straight to the org scope: it cannot approve there, so it is only a proposal."""
    s, acl = MemoryStore(), FakeACL(); old = seed(s, facts, acl)
    facts["e1"] = ["The Atlas client pilot is due November 13, 2026."]
    d = maintain.ingest(ep("e1", "eng-01", ORG, "approved", "2026-10-20"), s, acl, judge=date_judge)
    new = s.get(d[0].memory_id)
    assert new.status == "tentative" and new.authority == "tentative" and s.get(old.id).status == "trial"


def test_unrelated_everywhere_is_added(facts):
    s, acl = MemoryStore(), FakeACL(); seed(s, facts, acl)
    facts["e1"] = ["The client wants weekly status emails."]
    n = last_seq()
    d = maintain.ingest(ep("e1", "sales-01", f"{ORG}/sales", "discussion", "2026-10-05"), s, acl, judge=date_judge)
    m = s.get(d[0].memory_id)
    assert d[0].action == "add" and m.status == "trial" and m.scope == f"{ORG}/sales" and m.authority == "discussion"
    assert m.model == CM and m.author == "sales-01" and m.origin == "e1"
    assert types_since(n) == ["memory.added", "episode.ingested"]


# ---------- safety guards ----------

def test_unparseable_judge_never_overwrites(facts):
    s, acl = MemoryStore(), FakeACL(); old = seed(s, facts, acl)
    facts["e1"] = ["The Atlas client pilot is due November 13, 2026."]
    d = maintain.ingest(ep("e1", "exec-02", ORG, "approved", "2026-10-15"), s, acl, judge=lambda c, m: None)
    assert d[0].action == "tentative" and s.get(old.id).status == "trial"


def test_locked_old_memory_is_not_superseded(facts):
    s, acl = MemoryStore(), FakeACL(); old = seed(s, facts, acl); s.lock(old.id, "exec-01")
    facts["e1"] = ["The Atlas client pilot is due November 13, 2026."]
    d = maintain.ingest(ep("e1", "exec-02", ORG, "approved", "2026-10-15"), s, acl, judge=date_judge)
    assert d[0].action == "tentative" and s.get(old.id).status == "locked"


def test_correction_into_narrower_scope_does_not_retire_org_memory(facts):
    """exec-02 approves in the executive team scope: sales could no longer read the commitment, so no overwrite."""
    s, acl = MemoryStore(), FakeACL(); old = seed(s, facts, acl)
    facts["e1"] = ["The Atlas client pilot is due November 13, 2026."]
    d = maintain.ingest(ep("e1", "exec-02", f"{ORG}/executive", "approved", "2026-10-15"), s, acl, judge=date_judge)
    assert d[0].action == "tentative" and s.get(old.id).status == "trial"


def test_unreadable_scopes_are_never_compared(facts):
    s, acl = MemoryStore(), FakeACL()
    facts["e0"] = ["The Atlas client pilot is due November 13, 2026."]
    maintain.ingest(ep("e0", "eng-01", f"{ORG}/engineering", "tentative", "2026-10-10"), s, acl, judge=date_judge)
    seen = []
    facts["e1"] = ["The Atlas client pilot is due November 20, 2026."]
    d = maintain.ingest(ep("e1", "sales-01", f"{ORG}/sales", "discussion", "2026-10-11"), s, acl,
                        judge=lambda c, m: seen.append(m.id) or date_judge(c, m))
    assert seen == [] and d[0].action == "add"


def test_tentative_and_same_origin_memories_are_not_compared(facts):
    s, acl = MemoryStore(), FakeACL(); seed(s, facts, acl)
    facts["e1"] = ["Atlas pilot estimate November 13.", "Atlas pilot estimate November 20."]
    seen = []
    maintain.ingest(ep("e1", "eng-01", f"{ORG}/engineering", "tentative", "2026-10-10"), s, acl,
                    judge=lambda c, m: seen.append((c["text"][-4:], m.id)) or date_judge(c, m))
    assert all(mid == "m1" for _, mid in seen)  # never the sibling, never the tentative one


def test_same_but_narrower_scope_does_not_block_publication(facts):
    """An exec team note must not swallow the later approved org-wide publication of the same fact."""
    s, acl = MemoryStore(), FakeACL()
    facts["e0"] = ["The Atlas client pilot is due November 6, 2026."]
    maintain.ingest(ep("e0", "exec-01", f"{ORG}/executive", "discussion", "2026-09-30"), s, acl, judge=date_judge)
    facts["e1"] = ["Atlas pilot due November 6, 2026."]
    d = maintain.ingest(ep("e1", "exec-01", ORG, "approved", "2026-10-01"), s, acl, judge=date_judge)
    assert d[0].action == "add" and s.get(d[0].memory_id).scope == ORG


def test_no_acl_means_nothing_is_superseded(facts):
    s = MemoryStore()
    facts["e0"] = ["The Atlas client pilot is due November 6, 2026."]
    maintain.ingest(ep("e0", "exec-01", ORG, "approved", "2026-10-01"), s, None, judge=date_judge)
    facts["e1"] = ["The Atlas client pilot is due November 13, 2026."]
    d = maintain.ingest(ep("e1", "exec-02", ORG, "approved", "2026-10-15"), s, None, judge=date_judge)
    assert d[0].action == "tentative" and s.get("m1").status == "trial"


# ---------- Atlas, three steps ----------

def test_atlas_three_steps(facts):
    s, acl = MemoryStore(), FakeACL()
    facts["a1"] = ["The Atlas client pilot is due November 6, 2026.", "The Atlas client goal is a working inventory forecast."]
    facts["a2"] = ["Engineering's revised estimate puts the Atlas client pilot at November 13, 2026."]
    facts["a3"] = ["The Atlas client pilot commitment is changed to November 13, 2026."]

    d1 = maintain.ingest(ep("a1", "exec-01", ORG, "approved", "2026-10-01"), s, acl, judge=date_judge)
    nov6, goal = (s.get(x.memory_id) for x in d1)
    assert [x.action for x in d1] == ["add", "add"] and nov6.authority == "approved" and nov6.scope == ORG

    n = last_seq()
    d2 = maintain.ingest(ep("a2", "eng-01", f"{ORG}/engineering", "tentative", "2026-10-10"), s, acl, judge=date_judge)
    est = s.get(d2[0].memory_id)
    assert est.status == "tentative" and est.conflicts_with == [nov6.id] and s.get(nov6.id).status == "trial"
    assert types_since(n) == ["memory.added", "memory.conflict", "episode.ingested"]

    n = last_seq()
    d3 = maintain.ingest(ep("a3", "exec-02", ORG, "approved", "2026-10-15"), s, acl, judge=date_judge)
    nov13 = s.get(d3[0].memory_id)
    assert d3[0].action == "supersede" and nov13.supersedes == nov6.id and nov13.authority == "approved"
    assert s.get(nov6.id).status == "retired" and s.get(nov6.id).reason == f"superseded by {nov13.id}"
    assert s.get(goal.id).status == "trial"  # unchanged goal stays active
    assert types_since(n) == ["memory.added", "memory.retired", "memory.corrected", "episode.ingested"]

    # a fresh sales agent sees the corrected org commitment, not the engineering estimate
    got = s.search("Atlas pilot due", reader=f"{ORG}/sales/sales-01")
    assert nov13.id in [m.id for m in got] and nov6.id not in [m.id for m in got] and est.id not in [m.id for m in got]
    # every event that changes a memory carries a model id
    for e in events.history():
        if e["type"] in ("memory.added", "memory.retired", "memory.corrected", "memory.conflict", "memory.rejected"):
            assert e.get("model"), e


# ---------- judge parsing ----------

@pytest.mark.parametrize("raw,want", [
    ('{"verdict": "conflict", "reason": "dates differ"}', "conflict"),
    ('```json\n{"verdict": "same", "reason": "x"}\n```', "same"),
    ('Let me think. Both mention Atlas {not json}. Final:\n{"verdict": "Unrelated", "reason": "x"}', "unrelated"),
    ('<think>{"verdict": "same"}</think>{"verdict": "conflict", "reason": "x"}', "conflict"),
    ('verdict: conflict', "conflict"),
    ('{"verdict": "maybe"}', None),
    ('', None),
])
def test_parse_verdict(raw, want):
    assert maintain.parse_verdict(raw) == want


def test_llm_judge_is_one_call(monkeypatch):
    calls = []
    monkeypatch.setattr(llm, "complete", lambda role, msgs, **kw: calls.append(role) or '```json\n{"verdict":"conflict"}\n```')
    m = Memory("m1", "Atlas due Nov 6", "a", "e0", "2026-10-01")
    assert maintain.llm_judge({"text": "Atlas due Nov 13", "date": "2026-10-10"}, m) == "conflict" and calls == ["judge"]


# ---------- store, curator, agent ----------

def test_search_tentative_and_retired():
    s = MemoryStore()
    a = s.add("atlas pilot nov 6", author="a", origin="e", date="d")[0]
    t = s.add("atlas pilot nov 13", author="a", origin="e", date="d", status="tentative")[0]
    r = s.add("atlas pilot nov 20", author="a", origin="e", date="d")[0]; s.retire(r.id, "x")
    assert {m.id for m in s.search("atlas pilot")} == {a.id, t.id}
    assert {m.id for m in s.search("atlas pilot", include_tentative=False)} == {a.id}


def test_dedupe_is_scope_local():
    s = MemoryStore()
    assert s.add("Atlas pilot due Nov 13", author="a", origin="e", date="d", scope="rusty-rod/engineering")[0]
    assert s.add("Atlas pilot due Nov 13", author="b", origin="f", date="d", scope="rusty-rod")[0]
    assert s.add("Atlas pilot due Nov 13", author="b", origin="g", date="d", scope="rusty-rod")[0] is None


def test_old_jsonl_defaults(tmp_path):
    p = tmp_path / "m.jsonl"
    p.write_text(json.dumps({"id": "m1", "text": "old", "author": "a", "origin": "x", "date": "d", "status": "trial"}) + "\n", encoding="utf8")
    m = MemoryStore(str(p)).get("m1")
    assert m.authority == "discussion" and m.model is None and m.conflicts_with == []
    e = Episode("e1", "t", "d", "s")
    assert e.author is None and e.scope == "team" and e.authority == "discussion"


def test_curator_stamps_model_authority_scope(monkeypatch):
    monkeypatch.setattr(llm, "complete", lambda role, msgs, **kw: '["Atlas pilot due Nov 6"]')
    s = MemoryStore()
    m = curator.ingest(ep("e1", "exec-01", ORG, "approved", "2026-10-01"), s)[0]
    assert m.model == CM and m.authority == "approved" and m.scope == ORG
    class Bare:  # server.Episode / old adapters have no scope or authority
        id, text, date, source = "e2", "t", "d", "s"
    monkeypatch.setattr(llm, "complete", lambda role, msgs, **kw: '["something else entirely"]')
    m2 = curator.ingest(Bare(), s)[0]
    assert m2.scope == "team" and m2.authority == "discussion" and m2.model == CM


def test_agent_prompt_shows_metadata_and_conflicts(monkeypatch):
    seen = {}
    monkeypatch.setattr(llm, "complete", lambda role, msgs, **kw: seen.setdefault("p", msgs[0]["content"]) and "Nov 6.\nCITED: m1")
    old = Memory("m7", "Atlas due Nov 6", "exec-01", "e0", "2026-10-01", "trial", ORG, authority="approved")
    new = Memory("m9", "Atlas maybe Nov 13", "eng-01", "e1", "2026-10-10", "tentative", f"{ORG}/engineering",
                 authority="tentative", conflicts_with=["m7"])
    a = agent.answer("When is the Atlas pilot due?", [old, new])
    p = seen["p"]
    assert "[m1] (date 2026-10-01; scope rusty-rod; authority approved; status active) Atlas due Nov 6" in p
    assert "[m2] (date 2026-10-10; scope rusty-rod/engineering; authority tentative; status tentative, conflicts with [m1])" in p
    assert "approved and active" in p and "I don't know" in p and "CITED:" in p
    assert a.cited_ids == ["m7"] and a.text == "Nov 6."
    assert "conflicts with a memory not shown" in agent.render([new])
