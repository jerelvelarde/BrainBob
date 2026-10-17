"""Maintenance-judge comparison conditions, offline: fake curator, fake backend LLM, fake Crusoe endpoint and fake
local generator. No model is loaded and no network request is made."""
import json
import sys

import pytest

from bobbench import answer as answer_mod
from bobbench import run as runmod
from bobbench.adapters import ALL_CONDITIONS, CONDITIONS, JUDGE_CONDITIONS, resolve
from bobbench.adapters import judges
from bobbench.adapters.brainbob import BrainBobAdapter, bb_curator, bb_llm, bb_maintain, production_judge
from core_fixtures import fake_answer, mini_oracle, write_mini

RUN = ["append_only", "maintained", "maintained_teacher", "maintained_tuned", "maintained_small_base"]


def _relation(existing: str, candidate: str) -> str:
    return "conflict" if "commitment" in existing and "commitment" in candidate else "unrelated"


@pytest.fixture
def offline(monkeypatch, tmp_path):
    seen = {"loads": [], "backend": []}
    monkeypatch.setattr(bb_curator, "extract", lambda episode, role="curator": [episode.text])

    def complete(role, messages, fresh=False, **kw):  # backend LLM: production pair judge + audit judge
        seen["backend"].append((role, messages))
        if messages[0]["content"].startswith("You audit"):
            return '{"verdict": "insufficient", "reason": "stub"}'
        existing, new = messages[1]["content"].split("NEW candidate")
        return json.dumps({"verdict": _relation(existing, new), "reason": "stub"})

    monkeypatch.setattr(bb_llm, "complete", complete)
    monkeypatch.setattr(answer_mod, "answer", fake_answer)

    def bob_reply(msgs):
        d = json.loads(msgs[1]["content"])
        return json.dumps({"verdict": _relation(d["existing"]["text"], d["candidate"]["text"])})

    def endpoint(url, model, api_key=None, max_tokens=16):
        assert (url, model, api_key) == (judges.TEACHER_BASE_URL, judges.TEACHER_MODEL, "test-key")

        def gen(msgs):
            gen.last_usage = {"prompt_tokens": 200, "completion_tokens": 6}
            return bob_reply(msgs)
        return gen

    def local_generator(adapter=None, base=None, revision=None, max_new_tokens=16, *, adapter_revision=None):
        seen["loads"].append((adapter, base, revision, adapter_revision))
        return bob_reply if adapter else (lambda msgs: "The verdict is conflict.")  # base: never strict JSON

    b = judges.bridge()
    monkeypatch.setattr(b, "_endpoint", endpoint)
    monkeypatch.setattr(b, "local_generator", local_generator)
    monkeypatch.setattr(judges, "verify_adapter", lambda: {"adapter_sha256": judges.ADAPTER_SHA256, "verified": True})
    monkeypatch.setattr(judges, "_LOCAL", {})
    key = tmp_path / "api.key"
    key.write_text("test-key\n")
    monkeypatch.setattr(judges, "KEY_FILE", str(key))
    return seen


def _oracle():
    o = mini_oracle()
    o["checkpoints"]["cp-maint"]["forbidden"] = ["commitment is November 6"]
    return o


def test_conditions_registered_lazily_with_pinned_judges(offline):
    assert set(JUDGE_CONDITIONS) <= set(ALL_CONDITIONS) and not set(JUDGE_CONDITIONS) & set(CONDITIONS)
    for cond in JUDGE_CONDITIONS:
        a = resolve(cond)()
        assert isinstance(a, BrainBobAdapter) and a.name == cond and a.mode == "maintained"
        assert isinstance(a.judge, judges.TracedJudge)
        assert a.judge.info["kind"] == judges.JUDGE_CONDITIONS[cond]
    assert offline["loads"] == [(judges.ADAPTER, judges.BASE, judges.BASE_REVISION, judges.ADAPTER_REVISION),
                                (None, judges.BASE, judges.BASE_REVISION, None)]  # each model loaded once
    assert judges.BASE_REVISION == judges.bridge().BASE_REVISION
    assert judges.ADAPTER == judges.bridge().CANONICAL_ADAPTER
    assert judges.ADAPTER_REVISION == judges.bridge().CANONICAL_ADAPTER_REVISION
    assert "torch" not in sys.modules
    assert resolve("maintained")().judge is None  # production default


def test_end_to_end_traces_counts_and_scorecard(offline, tmp_path):
    world, oracles = write_mini(tmp_path, oracle=_oracle())
    out, card = runmod.run_benchmark([world], RUN, replicates=1, out_dir=str(tmp_path / "res"), oracles_dir=oracles,
                                     n_boot=50, log=lambda *_: None)
    traces = [json.loads(l) for l in open(f"{out}/traces.jsonl", encoding="utf-8")]
    ends = {t["condition"]: t for t in traces if t["type"] == "run_end"}
    cps = [t for t in traces if t["type"] == "checkpoint"]
    assert all("act_latency_s" in r for r in cps) and not any(r.get("error") for r in cps)

    for cond, model in [("maintained", bb_llm._roles()["judge"]["model"]), ("maintained_teacher", judges.TEACHER_MODEL),
                        ("maintained_tuned", judges.BASE), ("maintained_small_base", judges.BASE)]:
        calls = ends[cond]["judge_calls"]
        assert calls, cond
        for c in calls:
            assert len(c["input_sha256"]) == 64 and c["model"] == model and c["latency_ms"] >= 0
            assert c["raw_output"] and c["phase"] in ("ingest", "maintain") and c["event_id"]
            assert c["condition"] == cond
    assert "append_only" in ends and "judge_calls" not in ends["append_only"]
    assert all(c["adapter_revision"] == judges.ADAPTER_REVISION for c in ends["maintained_tuned"]["judge_calls"])
    assert all(c["usd"] > 0 for c in ends["maintained_teacher"]["judge_calls"])
    assert all(c["parsed"] is None and c["parse_failed"] for c in ends["maintained_small_base"]["judge_calls"])
    assert ends["maintained"]["pair_judge"]["kind"] == "production"

    jc = {c: card["conditions"][c]["judge_comparison"] for c in RUN}
    for cond in ("maintained", "maintained_teacher", "maintained_tuned"):
        assert jc[cond]["maintenance_ops"]["supersede"] >= 1 and jc[cond]["maintenance_ops"]["retired_memories"] >= 1
        assert jc[cond]["pair_judge"]["none"] == 0
    sb = jc["maintained_small_base"]
    assert sb["maintenance_ops"].get("supersede", 0) == 0 and sb["maintenance_ops"]["tentative"] >= 1
    assert sb["pair_judge"]["parse_failed"] == sb["pair_judge"]["calls"] > 0
    assert jc["append_only"]["pair_judge"] is None
    for c in RUN:
        assert jc[c]["stale_fact_use"]["opportunities"] == 1
        assert jc[c]["maintenance_retention"]["in_context"]["n"] == 1
        assert jc[c]["latency_ms"]["answer_n"] == 4 and jc[c]["failures"]["failed_acts"] == 0
    assert jc["maintained"]["latency_ms"]["judge_p50"] is not None
    assert jc["maintained_teacher"]["cost_usd"]["pair_judge"] > 0
    assert card["conditions"]["maintained_teacher"]["cost"]["usd"] >= jc["maintained_teacher"]["cost_usd"]["pair_judge"] * 0.99
    assert set(card["comparisons"]["maintained"]) == set(RUN) - {"maintained"}
    assert "macro" in card["comparisons"]["maintained"]["maintained_tuned"]
    md = open(f"{out}/scorecard.md", encoding="utf-8").read()
    assert "## Maintenance judge comparison" in md and "## Paired bootstrap vs maintained" in md
    assert "| maintained_small_base |" in md


def test_production_traced_judge_is_the_production_call(offline):
    class Mem:
        id, date, text = "m1", "2026-10-02", "The Atlas pilot commitment is November 6."
    cand = {"text": "The Atlas pilot commitment is November 13.", "date": "2026-10-10", "authority": "approved", "scope": "rr"}
    assert bb_maintain.llm_judge(cand, Mem(), "judge") == "conflict"
    j = production_judge()
    assert j(cand, Mem()) == "conflict"
    (r1, m1), (r2, m2) = offline["backend"][-2:]
    assert r1 == r2 == "judge" and m1 == m2 == bb_maintain.judge_messages(cand, Mem())
    c = j.calls[-1]
    assert json.loads(c["raw_output"])["verdict"] == "conflict" and c["billed_via"] == "brainbob.llm"


def test_judge_errors_and_timeouts_are_counted_as_none():
    def boom(cand, mem, msgs):
        raise TimeoutError("slow")
    j = judges.TracedJudge(boom, build=lambda c, m: [{"role": "user", "content": c["text"]}], model_id="x",
                           info={"kind": "test", "model": "x"})
    assert j({"text": "a"}, None) is None
    s = judges.summarize_calls(j.calls)
    assert (s["calls"], s["errors"], s["timeouts"], s["parse_failed"], s["none"]) == (1, 1, 1, 0, 1)


def test_local_judge_load_failure_is_a_recorded_failure(offline, monkeypatch, tmp_path):
    def no_torch(*a, **k):
        raise ModuleNotFoundError("No module named 'torch'")
    monkeypatch.setattr(judges.bridge(), "local_generator", no_torch)
    world, oracles = write_mini(tmp_path, oracle=_oracle())
    out, card = runmod.run_benchmark([world], ["maintained_tuned"], replicates=1, out_dir=str(tmp_path / "res"),
                                     oracles_dir=oracles, n_boot=10, log=lambda *_: None)
    c = card["conditions"]["maintained_tuned"]
    assert c["failed_acts"] == 4 and c["macro"] == 0
    assert c["judge_comparison"]["failures"]["runs_with_errors"] == 1
