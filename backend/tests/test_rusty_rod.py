"""Structure and self-consistency of the Rusty Rod correctness fixture, plus the deterministic grader. No model calls."""
import sys, pathlib, re
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import pytest
from types import SimpleNamespace as NS
from adapters import rusty_rod as rr

DATA = rr.load()
SC = DATA["scenarios"]
try:
    from brainbob import acl as _acl
    ORG = _acl.Org.load(rr.ORG_JSON)
except Exception:  # acl lane not ready: SPEC rules on a fake org
    class _Fake:
        teams = {**{f"exec-0{i}": "executive" for i in range(1, 4)}, **{f"sales-0{i}": "sales" for i in range(1, 6)},
                 **{f"eng-{i:02d}": "engineering" for i in range(1, 11)}}
        def readable_scopes(self, m): return ["rusty-rod", f"rusty-rod/{self.teams[m]}", f"rusty-rod/{self.teams[m]}/{m}"]
        def can_read(self, m, s): return m in self.teams and s in self.readable_scopes(m)
        def can_write(self, m, s): return self.can_read(m, s)
        def can_approve(self, m, s):
            if s == "rusty-rod": return self.teams.get(m) == "executive"
            return self.can_read(m, s)
    ORG = _Fake()

MEMBERS = [f"exec-0{i}" for i in range(1, 4)] + [f"sales-0{i}" for i in range(1, 6)] + [f"eng-{i:02d}" for i in range(1, 11)]
TEAM = {m: m.split("-")[0].replace("exec", "executive").replace("eng", "engineering") for m in MEMBERS}
SCOPES = {"rusty-rod"} | {f"rusty-rod/{t}" for t in set(TEAM.values())} | {f"rusty-rod/{TEAM[m]}/{m}" for m in MEMBERS}
QS = [(s, q) for s in SC for q in s["questions"]]


def test_counts_and_groups():
    assert len(SCOPES) == 22 and len(MEMBERS) == 18
    held = [s for s in SC if s["split"] == "heldout"]; dev = [s for s in SC if s["split"] == "dev"]
    assert len(held) == 30 and len(dev) == 6
    for g in rr.GROUPS:
        assert sum(s["group"] == g for s in held) == 5, g
        assert sum(s["group"] == g for s in dev) == 1, g
    first_updates = [s for s in held if s["group"] == "Updates"][0]
    assert "atlas" in first_updates["id"] and "November 6" in first_updates["episodes"][0]["text"]
    assert len({s["id"] for s in SC}) == len(SC)
    assert rr.scenarios("heldout", fast=True) and len(rr.scenarios("heldout", fast=True)) == 12


@pytest.mark.parametrize("sc", SC, ids=[s["id"] for s in SC])
def test_scenario_fields(sc):
    assert sc["split"] in ("dev", "heldout") and sc["group"] in rr.GROUPS
    assert 3 <= len(sc["episodes"]) <= 8 and 1 <= len(sc["questions"]) <= 3
    for e in sc["episodes"]:
        assert {"author", "scope", "authority", "date", "text"} <= set(e)
        assert e["author"] in MEMBERS and e["scope"] in SCOPES and e["authority"] in rr.AUTHORITIES
        assert re.fullmatch(r"2026-\d\d-\d\d", e["date"]) and e["text"].strip()
        assert ORG.can_write(e["author"], e["scope"]), (e["author"], e["scope"])
        if e["authority"] == "approved": assert ORG.can_approve(e["author"], e["scope"]), (e["author"], e["scope"])
    for q in sc["questions"]:
        assert {"member", "question", "expect", "forbid", "must_not_retrieve"} <= set(q)
        assert q["member"] in MEMBERS and q["question"].strip()
        assert q["expect"] in ("abstain", "uncertain") or (isinstance(q["expect"], list) and q["expect"] and all(x.strip() for x in q["expect"]))
        if q["expect"] == "uncertain": assert len(q["values"]) >= 2
        for s in q["must_not_retrieve"]:
            assert s in SCOPES and not ORG.can_read(q["member"], s)
        if isinstance(q["expect"], list):  # forbid never overlaps the accepted answers
            for f in q["forbid"]:
                assert not any(rr.has(x, f) or rr.has(f, x) for x in q["expect"]), (f, q["expect"])
    for u in sc.get("state", {}).get("updated", []): assert u["new"] and u["old"]


def _readable_text(sc, member):
    return "\n".join(e["text"] for e in sc["episodes"] if ORG.can_read(member, e["scope"]))


@pytest.mark.parametrize("sq", QS, ids=[f"{s['id']}:{q['member']}:{q['question'][:30]}" for s, q in QS])
def test_expectation_derivable_from_readable_episodes(sq):
    """Each expectation follows from what the asking member can read, and nothing else."""
    sc, q = sq
    txt = _readable_text(sc, q["member"])
    if isinstance(q["expect"], list):
        assert rr.any_has(txt, q["expect"]), q
    elif q["expect"] == "uncertain":
        for g in q["values"]: assert rr.any_has(txt, g), (g, q)
    else:  # abstain: the hidden value must not be readable; the unreadable scopes hold a private episode
        for f in q["forbid"]: assert not rr.has(txt, f), (f, q)
    # every must_not_retrieve scope is not readable by the member (already checked); a hidden-answer question has one
    if q["expect"] == "abstain" and q["forbid"]:
        hidden = "\n".join(e["text"] for e in sc["episodes"] if not ORG.can_read(q["member"], e["scope"]))
        assert rr.any_has(hidden, q["forbid"]), q


def test_dev_and_heldout_do_not_overlap():
    dev = [s for s in SC if s["split"] == "dev"]; held = [s for s in SC if s["split"] == "heldout"]
    norm_q = lambda ss: {rr.norm(q["question"]) for s in ss for q in s["questions"]}
    norm_e = lambda ss: {rr.norm(e["text"]) for s in ss for e in s["episodes"]}
    assert not norm_q(dev) & norm_q(held) and not norm_e(dev) & norm_e(held)
    client = lambda s: re.findall(r"\b([A-Z][a-z]+)\b", s["episodes"][0]["text"])
    # the main client name of each dev scenario never appears in held-out text
    held_txt = " ".join(e["text"] for s in held for e in s["episodes"])
    for d, name in [("ex-dev", "Jasper"), ("up-dev", "Basalt"), ("re-dev", "Glacier"), ("fo-dev", "Sable"), ("sh-dev", "Yarrow"), ("in-dev", "Falcon")]:
        assert name in " ".join(client(next(s for s in dev if s["id"] == d))) and name not in held_txt


def test_requirements_covered():
    held = [s for s in SC if s["split"] == "heldout"]
    qs = [q for s in held for q in s["questions"]]
    assert sum(bool(q["expect"] == "abstain" and q["must_not_retrieve"] and q["forbid"]) for q in qs) >= 5   # permission isolation
    assert sum(q["expect"] == "uncertain" for q in qs) >= 2                                             # unresolved conflicts
    assert any(e["authority"] == "tentative" for s in held if s["group"] == "Updates" for e in s["episodes"])  # tentative vs approved
    assert sum(bool(s.get("state", {}).get("keep")) for s in held) >= 15                               # retention of unrelated memories
    assert all(s.get("state", {}).get("updated") for s in held if s["group"] == "Forgetting")         # explicit retirement


def test_grader():
    assert rr.has("Due Nov. 13th, 2026", "nov 13") and not rr.has("Due Nov 13", "nov 1")
    assert rr.has("cut picking errors", "picking error") and not rr.has("$140,000", "40 000")
    q = dict(expect=["november 13", "nov 13"], forbid=["november 6"])
    assert rr.grade(q, "November 13, 2026.") == dict(correct=True, stale=False, kind="fact")
    assert rr.grade(q, "It moved from November 6 to November 13.")["stale"]
    assert not rr.grade(q, "November 16")["correct"]
    ab = dict(expect="abstain", forbid=["300k"])
    assert rr.grade(ab, "I don't know.")["correct"] and not rr.grade(ab, "About $300K.")["correct"]
    assert not rr.grade(ab, "I don't know, maybe $300k")["correct"]
    un = dict(expect="uncertain", values=[["aws"], ["gcp"]], forbid=[])
    assert rr.grade(un, "Either AWS or GCP") ["correct"] and rr.grade(un, "That's unresolved.")["correct"]
    assert not rr.grade(un, "AWS Batch.")["correct"]


def test_state_check_and_audit_gold():
    sc = next(s for s in SC if s["id"] == "up-1-atlas")
    M = lambda i, t, st, o: NS(id=i, text=t, status=st, origin=o)
    store = NS(all=lambda: [M("m1", "Atlas pilot due November 6, 2026", "retired", "up-1-atlas-e1"),
                            M("m2", "Atlas goals: cut picking errors by 30%", "trial", "up-1-atlas-e1"),
                            M("m3", "Atlas pilot due date moved to November 13, replacing November 6", "trial", "up-1-atlas-e3")])
    r = rr.state_check(sc, store)
    assert r["updates"][0]["correct"] and not r["keeps"][0]["forgotten"]
    bad = NS(all=lambda: [M("m1", "Atlas pilot due November 6", "trial", "up-1-atlas-e1"), M("m2", "picking errors goal", "retired", "up-1-atlas-e1")])
    r = rr.state_check(sc, bad)
    assert not r["updates"][0]["correct"] and r["keeps"][0]["forgotten"]
    assert rr.audit_gold(sc, M("m1", "Atlas pilot due November 6", "trial", "up-1-atlas-e1"), "up-1-atlas-e3") == "contradicted"
    assert rr.audit_gold(sc, M("m1", "x", "trial", "up-1-atlas-e1"), "up-1-atlas-e1") == "supported"
    assert rr.audit_gold(sc, M("m9", "x", "trial", "up-2-e1"), "up-1-atlas-e2") == "insufficient"
    assert rr.decisive_ids(sc) == ["up-1-atlas-e3"]


def test_episodes_carry_fields():
    sc = SC[0]
    e = rr.episodes(sc)[0]
    assert (e.author, e.scope, e.authority) == (sc["episodes"][0]["author"], sc["episodes"][0]["scope"], sc["episodes"][0]["authority"])
    eps = rr.readable_episodes(next(s for s in SC if s["id"] == "up-1-atlas"), "sales-02", ORG)
    assert all(x.scope in ("rusty-rod", "rusty-rod/sales", "rusty-rod/sales/sales-02") for x in eps) and len(eps) == 3
