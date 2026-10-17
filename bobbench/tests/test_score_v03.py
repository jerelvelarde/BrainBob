"""Scorer/oracle 0.3 regressions. Each answer snippet is quoted from run 20261017-141014 as cited in
_notes/codex-score-review.md (T:<line> = line of the decompressed traces.jsonl.gz)."""
import gzip
import json
import pathlib

import pytest

from bobbench.schema import load_oracle
from bobbench.score import (behavior, find_traces, forbidden_hit, provider_error, read_traces, score_checkpoint,
                            score_records)
from core_fixtures import mini_oracle, mini_world  # noqa: F401
from test_worlds import ORACLE_DIR

CP = {"budget": {"context_tokens": 100000}}


def entry(world, cid):
    return load_oracle(str(ORACLE_DIR / f"{world}.json")).checkpoints[cid]


def score(world, cid, answer, cited, error=None):
    return score_checkpoint(entry(world, cid), {"answer": answer, "context": "", "cited_event_ids": cited,
                                                "error": error}, CP, set(cited))


# review #1: maintained w2/cp-6/r2, T:843 — quotes Nov 25 but selects December 2 as the freeze date
T843 = ("Based on the context, the code freeze was originally scheduled for November 25, but it has been moved. "
        "The most recent authorized statement indicates the code freeze is now set for December 2, 2026.\n\n"
        "Specifically:\n- [w2-evt-08] (2026-11-06) states: \"Code freeze moves to November 25\" (approved, active).\n"
        "- [w2-evt-08] (2026-11-06) also states: \"Release council decision: Ledgerline 4.2 go-live moves to "
        "December 2\" (approved, active).\n\n**4.2 code freeze starts: December 2, 2026.**")


def test_review1_december2_as_freeze_date_fails():
    r = score("w2-authority-corrections", "cp-6", T843, ["w2-evt-08", "w2-evt-06"])
    assert r["required"] and r["forbidden"] is False and r["cats"] == 0
    synthetic = "November 25 is not the freeze date. The freeze starts December 2."
    assert score("w2-authority-corrections", "cp-6", synthetic, ["w2-evt-08"])["cats"] == 0


def test_review1_go_live_december2_still_allowed():
    ok = ("The 4.2 code freeze starts on **November 25, 2026**. The release council moved go-live to "
          "December 2.")
    assert score("w2-authority-corrections", "cp-6", ok, ["w2-evt-08"])["cats"] == 1


# review #2: w6/cp-6 — November 8 stated as the current filing deadline
T776 = ("- **ETA Long Beach: November 16, 2026** (replaces the earlier November 9 date) [w6-evt-08]\n\n"
        "The entry-filing advisory states that pre-filing is required by **November 8, 2026** [w6-evt-05].")
T935_TAIL = ("**For entry filing timing:** The pre-file entry is required by November 8 per [w6-evt-05]. Given the "
             "active ETA update to November 16, you should time your entry filing before that date, keeping in mind "
             "the November 8 pre-file deadline.")
T944_TAIL = ("The more recent October 30 update supersedes the November 9 date with November 16, but the pre-filing "
             "deadline of November 8 remains from the earlier advisory.\n\nSince the context contains conflicting ETA "
             "information, I cannot definitively state which arrival date is current without additional clarification.")
T953_TAIL = ("Since the task asks for timing the entry filing and the context contains conflicting information, "
             "I cannot confirm a single definitive date.")


@pytest.mark.parametrize("answer", [T776, T935_TAIL, T944_TAIL, "ETA November 16. " + T953_TAIL])
def test_review2_stale_filing_deadline_or_unresolved_eta_fails(answer):
    r = score("w6-correction-propagation", "cp-6", answer, ["w6-evt-08"])
    assert r["forbidden"] is False and r["cats"] == 0


# append_only r1/r2 describe November 8 historically: must still pass
A1 = ("- **November 16** (replacing the earlier November 9 date) - as stated in [w6-evt-08]\n\nEarlier context "
      "mentions:\n- November 9 ETA - from [w6-evt-05] (2026-10-24T11:00:00-07:00)\n- Pre-file entry required by "
      "November 8 - also from [w6-evt-05] (2026-10-24T11:00:00-07:00)\n\nThe ETA was updated from November 9 to "
      "November 16 in the later entry [w6-evt-08].")
A2 = ("the most recent ETA for MRDU 448812-3 at Long Beach is **November 16, 2026** (replacing the earlier November 9 "
      "date).\n- [w6-evt-05] (2026-10-24) originally listed ETA as November 9, and also noted \"Pre-file entry required "
      "by November 8.\"\n\nThe pre-filing deadline of November 8 (from the earlier [w6-evt-05]) is now likely outdated "
      "given the ETA update to November 16.")


@pytest.mark.parametrize("answer", [A1, A2])
def test_review2_historical_november8_still_passes(answer):
    assert score("w6-correction-propagation", "cp-6", answer, ["w6-evt-05", "w6-evt-08"])["cats"] == 1


# review #3: historical source summaries are not current stale claims
T237 = ("Based on the release calendar and the release council decision, the 4.2 code freeze starts on "
        "**November 25, 2026**.\n\nHere's the timeline from the sources:\n\n- **[w2-evt-01]**: The original release "
        "calendar listed code freeze starting November 11.\n- **[w2-evt-09]**: A reminder confirmed code freeze starts "
        "November 11.\n- **[w2-evt-08]**: The release council decision finalized: Ledgerline 4.2 go-live moves to "
        "December 2, and **code freeze moves to November 25**.")
T684 = ("1. **November 11** - Multiple approved memories state this date:\n   - [w2-evt-09] \"code freeze for version "
        "4.2 starts November 11\"\n   - [w2-evt-01] \"Code freeze starts November 11\"\n\nThe most recent **approved** "
        "memory about the code freeze date is [w2-evt-08] from November 6, which states the code freeze **moves to "
        "November 25**. This overrides the earlier November 11 date from [w2-evt-09] and [w2-evt-01].\n\nFor your "
        "planning, the code freeze is scheduled to start **November 25, 2026**.")
T263 = ("- **On-time delivery rate**: 95.1% (corrected from the earlier 96.4% figure)\n- **Q4 delivery schedule "
        "change**: Stockton deliveries will move to Tuesdays and Fridays\n\nThe initial report [w3-evt-07] stated 96.4% "
        "on-time delivery with three temperature excursions under 20 minutes and the Q4 schedule change. The correction "
        "[w3-evt-09] revised the on-time rate to 95.1%.")


@pytest.mark.parametrize("world,cid,answer,cited", [
    ("w2-authority-corrections", "cp-6", T237, ["w2-evt-08"]),
    ("w2-authority-corrections", "cp-6", T684, ["w2-evt-08"]),
    ("w3-cross-org-publication", "cp-8", T263, ["w3-evt-07", "w3-evt-09"]),
])
def test_review3_historical_summaries_pass(world, cid, answer, cited):
    r = score(world, cid, answer, cited)
    assert r["forbidden"] and r["cats"] == 1


def test_review3_unlabelled_stale_claim_still_fails():
    e = entry("w2-authority-corrections", "cp-6")
    m = e.raw["forbidden_exempt_markers"]
    assert forbidden_hit("Code freeze starts **November 11**.", e.forbidden, m)
    assert forbidden_hit("- Code freeze starts November 11.", e.forbidden, m)


# review #4: phrases-0.3
def test_review4_observed_paraphrases():
    assert behavior("Celeste is on leave through November 20, and deliverable sign-off will wait for her return.")["uncertain"]
    assert behavior("We need Celeste to make the final call.")["uncertain"]
    assert behavior("I cannot definitively state which arrival date is current")["abstain"]
    assert behavior("I cannot confirm a single definitive date.")["abstain"]
    assert behavior("The client constraints are not documented in the available memories.")["abstain"]


# review #7: provider failure returned as answer text
T801 = ("[ERROR: Agent failed (Function process_single_item_agent timed out after 90.0 seconds), API failed "
        "(API request returned None after all retries)]")


def test_review7_provider_error_text_is_not_completed():
    assert provider_error(T801)
    assert not provider_error("The log line said [ERROR: disk full] but the deploy succeeded.")
    r = score("w1-scoped-assembly", "cp-4", T801, [])
    assert r["completed"] is False and r["cats"] == 0


# review #6: gzip traces
def test_review6_reads_gzip_traces(tmp_path):
    lines = [{"type": "run_meta", "x": 1}, {"type": "checkpoint", "answer": "a"}]
    with gzip.open(tmp_path / "traces.jsonl.gz", "wt", encoding="utf-8") as f:
        f.write("\n".join(json.dumps(x) for x in lines) + "\n")
    p = find_traces(str(tmp_path))
    assert p.endswith(".gz") and read_traces(p) == lines


# review #10: invalid aggregation input raises
def _mini(tmp_path):
    from bobbench.schema import load_world
    wp, op = tmp_path / "w.json", tmp_path / "o.json"
    wp.write_text(json.dumps(mini_world()), encoding="utf-8")
    op.write_text(json.dumps(mini_oracle()), encoding="utf-8")
    w = load_world(str(wp))
    return {w.world_id: w}, {w.world_id: load_oracle(str(op))}


def test_review10_invalid_records_raise(tmp_path):
    worlds, oracles = _mini(tmp_path)
    wid = next(iter(worlds))
    cid = worlds[wid].checkpoints[0]["checkpoint_id"]
    r = {"condition": "c", "world_id": wid, "checkpoint_id": cid, "replicate": 0, "answer": ""}
    score_records([r], worlds, oracles, ["c"], 1, n_boot=10)  # valid
    for bad, reps in [([r, dict(r)], 1), ([{**r, "replicate": 1}], 1), ([{**r, "replicate": None}], 1),
                      ([{**r, "checkpoint_id": "nope"}], 1), ([{**r, "world_id": "nope"}], 1), ([r], 0)]:
        with pytest.raises(ValueError):
            score_records(bad, worlds, oracles, ["c"], reps, n_boot=10)
