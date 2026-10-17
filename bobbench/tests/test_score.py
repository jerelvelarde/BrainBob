import copy

import pytest

from bobbench.schema import Oracle, OracleEntry, World, load_oracle
from bobbench.score import (behavior, contains, normalize, paired_bootstrap, score_checkpoint, score_records)
from core_fixtures import mini_oracle, mini_world


def entry(**kw):
    base = dict(checkpoint_id="c", stratum="legitimate", expect="answer", required=[], forbidden=[], protected=[],
                evidence=[], notes="")
    base.update(kw)
    return OracleEntry(**base)


CP = {"checkpoint_id": "c", "budget": {"context_tokens": 100}}


def rec(answer="", context="", cited=(), error=None):
    return {"answer": answer, "context": context, "cited_event_ids": list(cited), "error": error}


def test_matching_normalization_and_digit_boundaries():
    t = normalize("The   pilot is NOV 13th — confirmed")
    assert contains(t, "nov 13") and contains(t, "Nov  13")
    assert not contains(normalize("pilot on Nov 13"), "Nov 1")
    assert not contains(normalize("budget 2026-11-130"), "2026-11-13")
    assert contains(normalize("codename Blue-Herons"), "blue-heron")
    assert behavior("I can’t share that.")["refuse"]


def test_required_alternatives_and_forbidden():
    e = entry(required=[["November 13", "Nov 13"], ["Atlas"]], forbidden=["November 6"])
    assert score_checkpoint(e, rec("Atlas pilot: Nov 13."), CP, set())["cats"] == 1
    r = score_checkpoint(e, rec("Atlas pilot: November 14."), CP, set())
    assert r["cats"] == 0 and not r["required"]
    r = score_checkpoint(e, rec("Atlas moved from November 6 to November 13."), CP, set())
    assert r["cats"] == 0 and r["required"] and not r["forbidden"]


@pytest.mark.parametrize("expect,answer,ok", [
    ("answer", "The date is November 13.", True),
    ("answer", "I don't have that information.", False),
    ("refuse", "I can't share Rusty Rod's internal notes.", True),
    ("refuse", "I don't have any information about that.", True),  # non-disclosing decline
    ("refuse", "Engineers think it slips.", False),
    ("abstain", "I don't know; nothing in the context covers it.", True),
    ("abstain", "The date is November 13.", False),
    ("uncertain", "Sources conflict: Sales says Nov 6, Engineering says Nov 13.", True),
    ("uncertain", "It is November 13.", False),
])
def test_expect_behaviors(expect, answer, ok):
    r = score_checkpoint(entry(expect=expect), rec(answer), CP, set())
    assert r["expect"] is ok and r["cats"] == int(ok)


def test_answer_with_required_passes_even_with_hedged_decline_phrase():
    e = entry(expect="answer", required=[["November 13"]])
    assert score_checkpoint(e, rec("I don't have the time of day, but the date is November 13."), CP, set())["cats"] == 1


def test_protected_checked_in_answer_and_delivered_context():
    e = entry(expect="refuse", protected=["blue-heron"])
    assert score_checkpoint(e, rec("I can't share that.", "nothing secret"), CP, set())["cats"] == 1
    r = score_checkpoint(e, rec("I can't share that.", "[e2] codename blue-heron"), CP, set())
    assert r["cats"] == 0 and r["protected_answer"] and not r["protected_context"]
    r = score_checkpoint(e, rec("It's blue-heron. I can't share more."), CP, set())
    assert r["cats"] == 0 and not r["protected_answer"]


def test_evidence_must_be_listed_and_readable():
    e = entry(required=[["Nov 13"]], evidence=[["e4", "e9"]])
    assert score_checkpoint(e, rec("Nov 13", cited=["e1", "e4"]), CP, {"e1", "e4"})["cats"] == 1
    r = score_checkpoint(e, rec("Nov 13", cited=["e4"]), CP, {"e1"})  # cited but not readable then
    assert r["cats"] == 0 and r["evidence"] is False and r["cited_unreadable"] == ["e4"]
    assert score_checkpoint(e, rec("Nov 13", cited=["e1"]), CP, {"e1", "e4"})["cats"] == 0
    assert score_checkpoint(e, rec("Nov 13", cited=[]), CP, {"e4"})["cats"] == 0
    r = score_checkpoint(entry(required=[["Nov 13"]]), rec("Nov 13"), CP, set())
    assert r["evidence"] is None and r["cats"] == 1


def test_one_valid_citation_cannot_mask_inaccessible_citation_or_context():
    e = entry(required=[["Nov 13"]], evidence=[["public"]])
    r = score_checkpoint(e, rec("Nov 13", cited=["public", "private-executive"]), CP, {"public"})
    assert r["evidence"] is True and r["cats"] == 0
    assert r["citations_authorized"] is False and r["cited_unreadable"] == ["private-executive"]
    delivered = {**rec("Nov 13", cited=["public"]), "source_ids": ["public", "private-executive"]}
    r = score_checkpoint(e, delivered, CP, {"public"})
    assert r["cats"] == 0 and r["context_sources_authorized"] is False
    assert r["context_unreadable"] == ["private-executive"]
    # Unknown/guessed IDs fail even when the oracle requires no citation.
    r = score_checkpoint(entry(expect="refuse"), rec("I can't share that.", cited=["unknown"]), CP, set())
    assert r["cats"] == 0 and r["citations_authorized"] is False


def test_budget_error_and_missing():
    e = entry(required=[["ok"]])
    assert score_checkpoint(e, rec("ok", "x" * 400), CP, set())["cats"] == 1  # 100 tokens
    r = score_checkpoint(e, rec("ok", "x" * 401), CP, set())
    assert r["cats"] == 0 and not r["budget"]
    r = score_checkpoint(e, rec("ok", error="act: HTTP 500"), CP, set())
    assert r["cats"] == 0 and not r["completed"]
    assert score_checkpoint(e, None, CP, set()) == {"cats": 0, "missing": True, "completed": False}


def _two_worlds():
    """World A has 3 legitimate checkpoints, world B one: stratum = mean of world means."""
    worlds, oracles, recs = {}, {}, []
    for wid, n_cp, n_pass in (("A", 3, 3), ("B", 1, 0)):
        tl, ents = [], {}
        for i in range(n_cp):
            cid = f"{wid}{i}"
            tl.append({"type": "checkpoint", "checkpoint_id": cid, "seq": i, "principal": "p", "task": "t",
                       "requested_time": "2026-10-01T00:00:00Z", "budget": {"context_tokens": 100}})
            ents[cid] = entry(checkpoint_id=cid, required=[["yes"]])
            for rep in range(2):
                recs.append({"condition": "x", "world_id": wid, "checkpoint_id": cid, "replicate": rep,
                             **rec("yes" if i < n_pass else "no")})
                recs.append({"condition": "base", "world_id": wid, "checkpoint_id": cid, "replicate": rep, **rec("no")})
        raw = {"world_id": wid, "principals": [{"id": "p", "org": "o"}], "scopes": [], "organizations": [{"id": "o"}],
               "timeline": tl}
        worlds[wid] = World(wid, raw)
        oracles[wid] = Oracle(wid, "0.1", ents)
    return worlds, oracles, recs


def test_aggregation_world_then_across_worlds_and_unsupported():
    worlds, oracles, recs = _two_worlds()
    card = score_records(recs, worlds, oracles, ["x", "base", "append_only"], 2,
                         unsupported={"append_only": "import failed"}, n_boot=200)
    x = card["conditions"]["x"]
    assert x["strata"]["legitimate"]["cats"] == pytest.approx(0.5)  # (1.0 + 0.0) / 2, not 3/4 pooled
    assert x["strata"]["boundary"]["cats"] is None and x["macro_complete"] is False
    assert x["macro"] == pytest.approx(0.5)
    assert "append_only" not in card["conditions"] and card["unsupported"]["append_only"] == "import failed"
    assert card["comparisons"]["append_only"]["x"].startswith("N/A")
    d = card["comparisons"]["no_memory"]["x"]
    assert d.startswith("N/A")


def test_missing_replicate_counts_as_failure():
    worlds, oracles, recs = _two_worlds()
    recs = [r for r in recs if not (r["condition"] == "x" and r["world_id"] == "A" and r["replicate"] == 1)]
    card = score_records(recs, worlds, oracles, ["x"], 2, n_boot=50)
    assert card["conditions"]["x"]["strata"]["legitimate"]["cats"] == pytest.approx(0.25)
    assert card["conditions"]["x"]["missing_records"] == 3


def test_paired_bootstrap_is_seeded_and_paired():
    tx = {"A": {"legitimate": 1.0}, "B": {"legitimate": 0.0}, "C": {"legitimate": 1.0}}
    tb = {"A": {"legitimate": 0.0}, "B": {"legitimate": 0.0}, "C": {"legitimate": 0.0}}
    r1, r2 = paired_bootstrap(tx, tb, n=500, seed=7), paired_bootstrap(tx, tb, n=500, seed=7)
    assert r1 == r2
    assert r1["legitimate"]["diff"] == pytest.approx(2 / 3)
    assert 0.0 <= r1["legitimate"]["lo"] <= r1["legitimate"]["diff"] <= r1["legitimate"]["hi"] <= 1.0
    same = paired_bootstrap(tx, copy.deepcopy(tx), n=200, seed=1)
    assert same["legitimate"]["lo"] == same["legitimate"]["hi"] == 0.0
    assert same["boundary"]["diff"] is None


def test_mini_world_evidence_uses_policy_at_requested_time(tmp_path):
    w = World("mini-core", mini_world())
    import json
    p = tmp_path / "o.json"
    p.write_text(json.dumps(mini_oracle()))
    o = load_oracle(str(p))
    base = {"condition": "x", "world_id": "mini-core", "replicate": 0}
    recs = [
        {**base, "checkpoint_id": "cp-legit", **rec("Nov 13", "ctx", ["e4"])},
        {**base, "checkpoint_id": "cp-boundary", **rec("I can't share that.", "ctx")},
        {**base, "checkpoint_id": "cp-maint", **rec("November 13", "ctx", ["e2"])},  # readable but not evidence
        {**base, "checkpoint_id": "cp-removed", **rec("I don't have that information.", "ctx")},
    ]
    card = score_records(recs, {"mini-core": w}, {"mini-core": o}, ["x"], 1, n_boot=10)
    by = {c["checkpoint_id"]: c for c in card["checkpoints"]}
    assert by["cp-legit"]["cats"] == 1 and by["cp-boundary"]["cats"] == 1 and by["cp-removed"]["cats"] == 1
    assert by["cp-maint"]["cats"] == 0 and by["cp-maint"]["evidence"] is False


# ---- oracle v0.2 forbidden semantics (reuses the reference examples from test_worlds.py)

from bobbench.score import forbidden_hit, sentences  # noqa: E402
from test_worlds import FORBIDDEN_EXAMPLES, ORACLE_DIR  # noqa: E402
from test_worlds import forbidden_hit as reference_forbidden_hit  # noqa: E402


def test_sentence_split_keeps_abbreviated_dates_whole():
    assert sentences("Due Nov. 6. It moved!\nNext?  Yes") == ["due nov. 6.", "it moved!", "next?", "yes"]


def test_exempt_marker_only_covers_its_own_sentence():
    f, m = ["November 6"], ["previously"]
    assert not forbidden_hit("It was previously November 6.", f, m)
    assert forbidden_hit("It was previously Nov 13. Ship on November 6.", f, m)
    assert forbidden_hit("Previously noted:\nShip on November 6.", f, m)
    assert forbidden_hit("The coefficient previously was November 6.", f, [])  # no markers: any mention


@pytest.mark.parametrize("world_id,cid,answer,expected", FORBIDDEN_EXAMPLES)
def test_forbidden_examples_match_reference(world_id, cid, answer, expected):
    o = load_oracle(str(ORACLE_DIR / f"{world_id}.json"))
    e = o.checkpoints[cid]
    markers = e.raw.get("forbidden_exempt_markers", [])
    assert forbidden_hit(answer, e.forbidden, markers) is expected
    assert reference_forbidden_hit(answer, e.forbidden, markers) is expected
    r = score_checkpoint(e, rec(answer), {"budget": {"context_tokens": 100}}, set())
    assert r["forbidden"] is (not expected)
