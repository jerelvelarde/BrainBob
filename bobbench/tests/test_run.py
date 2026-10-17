import json
import os

import pytest

from bobbench import run as runmod
from bobbench.adapter import Adapter, count_tokens
from bobbench.adapters import Unsupported
from bobbench.adapters.controls import AlwaysRefuseAdapter, UnfilteredAdapter
from bobbench.adapters.full_history import FullHistoryAdapter
from bobbench.adapters.no_memory import NoMemoryAdapter
from bobbench.policy import Policy
from bobbench.schema import World, check_oracle, validate_world
from core_fixtures import CLIENT, MAYA, T, fake_answer, mini_oracle, mini_world, write_mini

SENTINELS = ["ORC-REQ-SENTINEL", "ORC-ALT-SENTINEL", "ORC-FORBID-SENTINEL", "ORC-PROT-SENTINEL",
             "ORC-NOTES-SENTINEL", "ORC-EXTRA-SENTINEL", "ORC-EVID-SENTINEL"]
ORACLE_ONLY_KEYS = ["stratum", "expect", "required", "forbidden", "protected", "evidence", "notes",
                    "checker_version"]


class Spy(Adapter):
    """Records everything the runner hands it."""
    name = "spy"
    parallel_safe = True
    log: list = []
    instances: list = []

    def __init__(self):
        Spy.instances.append(id(self))

    def _rec(self, op, *args):
        Spy.log.append((id(self), op, json.loads(json.dumps(args, default=str))))

    def reset(self, world_manifest, budget, workdir):
        self._rec("reset", world_manifest, budget)

    def ingest(self, e):
        self._rec("ingest", e)
        return {"ok": True}

    def apply_policy(self, e):
        self._rec("apply_policy", e)
        return {"ok": True}

    def maintain(self, cutoff_seq, budget):
        self._rec("maintain", cutoff_seq, budget)
        return {"ok": True}

    def open_session(self, principal, task, requested_time, purpose, budget):
        self._rec("open_session", principal, task, requested_time, purpose, budget)
        return {"session_id": "s", "context": "", "context_tokens": 0, "source_ids": []}

    def act(self, session, task):
        self._rec("act", session, task)
        return {"answer": "I don't have that information.", "cited_event_ids": [], "cost": {}}

    def inspect_surface(self, principal, surface, request):
        self._rec("inspect_surface", principal, surface, request)
        return None


@pytest.mark.parametrize("operation", ["ingest", "apply_policy", "maintain", "open_session"])
def test_failed_receipts_and_missing_sessions_cannot_pass(operation, tmp_path):
    class Failed(Spy):
        pass

    setattr(Failed, operation, lambda self, *args: None if operation == "open_session" else {"ok": False})
    records = runmod.run_world(World("mini-core", mini_world()), "failed", Failed, 0, str(tmp_path), probes=False)
    checkpoints = [r for r in records if r["type"] == "checkpoint"]
    assert len(checkpoints) == 4
    assert all(r["error"] for r in checkpoints)
    if operation in ("ingest", "apply_policy"):
        assert all(r["delivery_errors"] for r in checkpoints)


@pytest.mark.parametrize("operation", ["ingest", "apply_policy"])
def test_failed_delivery_exceptions_taint_later_checkpoints(operation, tmp_path):
    class Failed(Spy):
        pass

    def fail(self, *args):
        raise RuntimeError("injected delivery failure")

    setattr(Failed, operation, fail)
    records = runmod.run_world(World("mini-core", mini_world()), "failed", Failed, 0, str(tmp_path), probes=False)
    checkpoints = [r for r in records if r["type"] == "checkpoint"]
    assert len(checkpoints) == 4
    assert all("prior delivery failed" in r["error"] for r in checkpoints)


def sentinel_oracle():
    o = mini_oracle()
    for cid, e in o["checkpoints"].items():
        e["required"] = [["ORC-REQ-SENTINEL", "ORC-ALT-SENTINEL"]]
        e["forbidden"] = ["ORC-FORBID-SENTINEL"]
        e["protected"] = ["ORC-PROT-SENTINEL"]
        e["notes"] = "ORC-NOTES-SENTINEL"
        e["extra"] = "ORC-EXTRA-SENTINEL"
    return o


def test_run_refuses_existing_artifact_directory(tmp_path):
    world_path, oracles_dir = write_mini(tmp_path)
    output = tmp_path / "existing"
    output.mkdir()
    trace = output / "traces.jsonl"
    trace.write_text("original evidence\n")
    with pytest.raises(FileExistsError):
        runmod.run_benchmark([world_path], ["always_refuse"], out_dir=str(output),
                             oracles_dir=oracles_dir, log=lambda *_: None)
    assert trace.read_text() == "original evidence\n"


def test_oracle_never_reaches_adapter(tmp_path):
    Spy.log, Spy.instances = [], []
    world_path, oracles_dir = write_mini(tmp_path, oracle=sentinel_oracle())
    out, card = runmod.run_benchmark([world_path], ["spy"], replicates=2, out_dir=str(tmp_path / "res"),
                                     oracles_dir=oracles_dir, factories={"spy": Spy}, log=lambda *_: None)
    blob = json.dumps(Spy.log)
    for s in SENTINELS:
        assert s not in blob
    for k in ORACLE_ONLY_KEYS:
        assert f'"{k}"' not in blob, k
    # oracle was used by the scorer (so the sentinels were really there to leak)
    assert card["conditions"]["spy"]["components"]["required"]["pass"] == 0
    # fresh adapter per replicate, items in seq order, no future items before a checkpoint
    assert len(set(Spy.instances)) == 2
    for inst in set(Spy.instances):
        ops = [(op, a) for i, op, a in Spy.log if i == inst]
        assert ops[0][0] == "reset" and "timeline" not in ops[0][1][0]
        seqs = [a[0]["seq"] for op, a in ops if op in ("ingest", "apply_policy")]
        assert seqs == sorted(seqs) and len(seqs) == 14
        names = [op for op, _ in ops if op in ("ingest", "apply_policy", "open_session")]
        first_cp = names.index("open_session")
        assert len([n for n in names[:first_cp] if n != "open_session"]) == 13  # seq < 20 only
    assert os.path.exists(os.path.join(out, "scorecard.md"))
    assert os.path.exists(os.path.join(out, "scorecard.json"))


def test_baselines_and_controls_end_to_end(tmp_path, monkeypatch):
    world_path, oracles_dir = write_mini(tmp_path)

    def fake_resolve(c):
        raise Unsupported("BrainBobAdapter import failed: test")
    monkeypatch.setattr(runmod, "resolve", fake_resolve)
    factories = {"no_memory": lambda: NoMemoryAdapter(answer_fn=fake_answer),
                 "full_history": lambda: FullHistoryAdapter(answer_fn=fake_answer),
                 "always_refuse": AlwaysRefuseAdapter,
                 "unfiltered": lambda: UnfilteredAdapter(answer_fn=fake_answer)}
    conds = ["no_memory", "full_history", "append_only", "maintained", "always_refuse", "unfiltered"]
    out, card = runmod.run_benchmark([world_path], conds, replicates=2, out_dir=str(tmp_path / "res"),
                                     oracles_dir=oracles_dir, factories=factories, log=lambda *_: None)
    c = card["conditions"]

    def strata(name):
        return tuple(c[name]["strata"][s]["cats"] for s in ("legitimate", "boundary", "maintenance"))
    assert strata("full_history") == (1.0, 1.0, 1.0)
    assert strata("unfiltered") == (0.0, 0.0, 0.0)  # protected text or inaccessible source IDs
    assert strata("no_memory") == (0.0, 1.0, 0.0)
    assert strata("always_refuse") == (0.0, 1.0, 0.0)
    assert set(card["unsupported"]) == {"append_only", "maintained"}
    # components count only applicable records: 2 checkpoints list required claims x 2 replicates
    assert c["no_memory"]["components"]["required"] == {"pass": 0, "n": 4, "rate": 0.0}
    assert "forbidden" not in c["no_memory"]["components"]
    assert {x["expected_behavior"] for x in card["checkpoints"]} == {"answer", "refuse", "abstain"}
    assert c["unfiltered"]["protected_disclosure"]["disclosures"] > 0
    assert c["full_history"]["protected_disclosure"]["disclosures"] == 0
    assert c["full_history"]["surfaces"]["search"] == "unsupported"
    md = open(os.path.join(out, "scorecard.md"), encoding="utf-8").read()
    assert "append_only: BrainBobAdapter import failed" in md
    traces = [json.loads(l) for l in open(os.path.join(out, "traces.jsonl"), encoding="utf-8")]
    cps = [t for t in traces if t["type"] == "checkpoint"]
    assert len(cps) == 4 * 4 * 2
    assert all(len(t["context_sha256"]) == 64 and "seed" in t for t in cps)
    assert traces[0]["type"] == "run_meta" and traces[0]["answer_config"]["model"]
    # replicate seeds differ, same seed for the same (world, condition, replicate)
    seeds = {(t["condition"], t["replicate"]): t["seed"] for t in cps}
    assert seeds[("full_history", 0)] != seeds[("full_history", 1)]


def test_full_history_filters_by_policy_and_discloses_truncation():
    w = World("mini-core", mini_world())
    a = FullHistoryAdapter(answer_fn=fake_answer)
    a.reset(w.manifest(), {"context_tokens": 4000}, ".")
    for it in w.timeline:
        if it["seq"] >= 20:
            break
        (a.ingest if it["type"] == "source" else a.apply_policy)(dict(it))
    s = a.open_session(MAYA, "t", T(12), "client-update", {"context_tokens": 4000})
    assert s["source_ids"] == ["e1", "e3", "e4"] and "blue-heron" not in s["context"]
    assert "[e4]" in s["context"] and not s["truncated"]
    s = a.open_session(CLIENT, "t", T(12), "project-update", {"context_tokens": 4000})
    assert s["source_ids"] == ["e5"]
    small = a.open_session(MAYA, "t", T(12), "client-update", {"context_tokens": 110})
    assert small["truncated"] and count_tokens(small["context"]) <= 110
    assert small["source_ids"] == ["e4"] and small["omitted_event_ids"] == ["e1", "e3"]
    assert "TRUNCATED" in small["context"]
    u = UnfilteredAdapter(answer_fn=fake_answer)
    u.reset(w.manifest(), {}, ".")
    for it in w.timeline[:13]:
        (u.ingest if it["type"] == "source" else u.apply_policy)(dict(it))
    assert "blue-heron" in u.open_session(CLIENT, "t", T(12), None, {"context_tokens": 4000})["context"]


def test_schema_validation_catches_bad_worlds(tmp_path):
    w = World("mini-core", mini_world())
    assert validate_world(w) == ([], [])
    world_path, oracles_dir = write_mini(tmp_path)
    assert check_oracle(w, os.path.join(oracles_dir, "mini-core.json"))[0] == []
    bad = mini_world()
    bad["timeline"][9]["seq"] = 5  # not increasing
    bad["timeline"][10]["audience"] = ["no-such-scope"]
    bad["timeline"][13]["principal"] = "ghost"
    errs, _ = validate_world(World("mini-core", bad))
    assert any("does not increase" in e for e in errs)
    assert any("unknown scope 'no-such-scope'" in e for e in errs)
    assert any("unknown principal 'ghost'" in e for e in errs)
    o = mini_oracle()
    del o["checkpoints"]["cp-maint"]
    o["checkpoints"]["cp-removed"]["evidence"] = [["e4"]]  # maya can no longer read it: unpassable
    p = tmp_path / "bad_oracle.json"
    p.write_text(json.dumps(o))
    errs, _ = check_oracle(w, str(p))
    assert any("'cp-maint' has no oracle entry" in e for e in errs)
    assert any("'cp-removed' no evidence alternative is readable" in e for e in errs)
    with pytest.raises(SystemExit):
        bp = tmp_path / "w2"
        bp.mkdir()
        (bp / "mini-core.json").write_text(json.dumps(mini_world()))
        runmod.run_benchmark([str(bp / "mini-core.json")], ["spy"], 1, str(tmp_path / "r2"), str(tmp_path / "none"),
                             factories={"spy": Spy}, log=lambda *_: None)


def test_reset_failure_is_a_recorded_failure_not_an_exclusion(tmp_path):
    class Broken(NoMemoryAdapter):
        def reset(self, *a):
            raise RuntimeError("boom")
    world_path, oracles_dir = write_mini(tmp_path)
    _, card = runmod.run_benchmark([world_path], ["broken"], 1, str(tmp_path / "res"), oracles_dir,
                                   factories={"broken": Broken}, log=lambda *_: None)
    b = card["conditions"]["broken"]
    assert b["failed_acts"] == 4 and b["macro"] == 0.0


def test_policy_used_by_baseline_matches_scorer_policy():
    w = mini_world()
    p = Policy.replay(w, upto_seq=24)
    assert [e["event_id"] for e in p.readable_events(MAYA, T(15))] == ["e3"]
