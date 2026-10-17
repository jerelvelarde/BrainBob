"""Experimental small-model judge bridge (experiments/memops-small, issue #7). No network, no model: the judge's raw
output is faked. Shows that maintain's deterministic rules stay authoritative whatever the classifier says."""
import sys, pathlib, json
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend")); sys.path.insert(0, str(ROOT / "experiments" / "memops-small"))
import pytest
from brainbob import events, curator, maintain, llm
from brainbob.memory import MemoryStore
from brainbob.types import Episode, Memory
import bridge, job_all

ORG = "rusty-rod"
TEAM = {"exec-01": "executive", "sales-01": "sales", "eng-01": "engineering"}


class FakeACL:
    def _paths(self, m): return [ORG, f"{ORG}/{TEAM[m]}", f"{ORG}/{TEAM[m]}/{m}"] if m in TEAM else []
    def can_read(self, m, scope): return scope in self._paths(m)
    def can_approve(self, m, scope):
        if m not in TEAM: return False
        return TEAM[m] == "executive" if scope == ORG else scope in self._paths(m)[1:]


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


def ep(eid, author, scope, authority, date):
    return Episode(eid, "x", date, "test", author=author, scope=scope, authority=authority)


def fake(raw):
    """A fake small model: always emits `raw`; records the messages it was shown."""
    seen = []
    def gen(msgs): seen.append(msgs); return raw
    gen.seen = seen
    return gen


OLD = "The Atlas client pilot is due November 6, 2026."
NEW = "The Atlas client pilot deadline moved to November 13, 2026."


def seeded(facts, acl, status=None):
    s = MemoryStore(); facts["e0"] = [OLD]
    d = maintain.ingest(ep("e0", "exec-01", ORG, "approved", "2026-10-01"), s, acl, judge=lambda c, m: "unrelated")
    old = s.get(d[0].memory_id)
    if status == "locked": s.lock(old.id, "exec-01")
    return s, old


def statuses(s): return {m.id: m.status for m in s.all()}


# ---------- one input format everywhere: Jerel's Bob benchmark messages ----------
EXP = ROOT / "experiments" / "memops-small"
import bob_format


def test_bob_format_rerenders_every_exported_input():
    for split in ("dev", "eval"):
        p = EXP / "bob_inputs" / f"{split}_inputs.jsonl"
        if not p.exists(): pytest.skip("no Bob export")
        for line in open(p, encoding="utf8"):
            r = json.loads(line)
            assert not {"label", "gold", "verdict", "template_id"} & set(r)
            assert bob_format.messages(r["id"], r["existing"], r["candidate"]) == r["messages"]
            assert bob_format.input_hash(r["id"], r["existing"], r["candidate"]) == r["input_sha256"]


def test_training_rows_use_bob_format_and_never_bob_inputs():
    bob_users = set()
    for split in ("dev", "eval"):
        p = EXP / "bob_inputs" / f"{split}_inputs.jsonl"
        if p.exists(): bob_users |= {json.loads(l)["messages"][1]["content"] for l in open(p, encoding="utf8")}
    bob_texts = {json.loads(u)[k]["text"] for u in bob_users for k in ("existing", "candidate")}
    for split in ("train", "dev"):
        p = EXP / f"{split}.jsonl"
        if not p.exists(): continue
        for line in open(p, encoding="utf8"):
            r = json.loads(line)
            assert r["messages"] == bob_format.messages(r["id"], r["existing"], r["candidate"])
            assert r["messages"][1]["content"] not in bob_users
            assert r["existing"]["text"] not in bob_texts and r["candidate"]["text"] not in bob_texts
            assert job_all.parse_strict(r["target"]) == r["label"]


def test_bridge_sends_bob_format():
    g = fake('{"verdict":"conflict"}')
    cand = {"text": NEW, "date": "2026-10-08", "authority": "approved", "scope": ORG}
    mem = Memory("m1", OLD, "exec-01", "e0", "2026-10-01")
    assert bridge.make_judge(g)(cand, mem) == "conflict"
    msgs = g.seen[0]
    assert msgs[0]["content"] == bob_format.PROMPT
    assert json.loads(msgs[1]["content"]) == {"id": "pair-m1", "existing": {"text": OLD, "date": "2026-10-01", "id": "m1"},
                                              "candidate": {"text": NEW, "date": "2026-10-08", "source_id": "candidate"}}


def test_submission_rows_match_contract():
    rows = [dict(id="eval-001", input_sha256="h1", output='{"verdict":"same"}', latency_ms=3.0, probs={"same": 1}),
            dict(id="eval-002", input_sha256="h2", error="RuntimeError: oom", latency_ms=1.0)]
    assert job_all.submission(rows) == [{"id": "eval-001", "input_sha256": "h1", "response": '{"verdict":"same"}', "latency_ms": 3.0},
                                        {"id": "eval-002", "input_sha256": "h2", "error": "RuntimeError: oom", "latency_ms": 1.0}]


# ---------- parsing ----------

@pytest.mark.parametrize("raw,want", [
    ('{"verdict":"same"}', "same"), (' {"verdict": "conflict"}\n', "conflict"), ('{"verdict":"unrelated"}', "unrelated"),
    ('{"verdict": "conflict", "reason": "x"}', None),
    ('```json\n{"verdict":"same"}\n```', None), ('{"verdict":"Same"}', None), ('{"verdict":"duplicate"}', None),
    ('verdict: same', None), ('', None), ('{"verdict":"same"} extra', None), ('["same"]', None), (None, None)])
def test_parse_strict(raw, want):
    assert job_all.parse_strict(raw) == want == bob_format.verdict(raw)


def test_exceptions_become_none():
    def boom(msgs): raise RuntimeError("model down")
    mem = Memory("m1", OLD, "exec-01", "e0", "2026-10-01")
    assert bridge.make_judge(boom)({"text": NEW, "date": "2026-10-08"}, mem) is None


# ---------- deterministic rules stay authoritative ----------

def test_parse_failure_takes_conservative_path(facts):
    acl = FakeACL(); s, old = seeded(facts, acl)
    facts["e1"] = [NEW]
    d = maintain.ingest(ep("e1", "exec-01", ORG, "approved", "2026-10-08"), s, acl, judge=bridge.make_judge(fake("not json at all")))
    assert d[0].action == "tentative" and s.get(old.id).status == "trial"  # flagged, never overwritten


def test_approved_newer_correction_supersedes(facts):
    acl = FakeACL(); s, old = seeded(facts, acl)
    facts["e1"] = [NEW]
    d = maintain.ingest(ep("e1", "exec-01", ORG, "approved", "2026-10-08"), s, acl, judge=bridge.make_judge(fake('{"verdict":"conflict"}')))
    assert d[0].action == "supersede" and s.get(old.id).status == "retired" and s.get(d[0].memory_id).supersedes == old.id
    assert len(s.all()) == 2  # retired, not deleted


def test_stale_correction_rejected(facts):
    acl = FakeACL(); s, old = seeded(facts, acl)
    facts["e1"] = [NEW]
    d = maintain.ingest(ep("e1", "exec-01", ORG, "approved", "2026-09-01"), s, acl, judge=bridge.make_judge(fake('{"verdict":"conflict"}')))
    assert d[0].action == "reject" and "stale" in d[0].reason and statuses(s) == {old.id: "trial"}


def test_unapproved_conflict_stays_tentative(facts):
    acl = FakeACL(); s, old = seeded(facts, acl)
    facts["e1"] = [NEW]
    d = maintain.ingest(ep("e1", "sales-01", f"{ORG}/sales", "discussion", "2026-10-08"), s, acl, judge=bridge.make_judge(fake('{"verdict":"conflict"}')))
    assert d[0].action == "tentative" and s.get(old.id).status == "trial" and s.get(d[0].memory_id).conflicts_with == [old.id]


def test_approval_without_rights_stays_tentative(facts):
    acl = FakeACL(); s, old = seeded(facts, acl)
    facts["e1"] = [NEW]  # sales-01 claims an approved org-wide correction it cannot give
    d = maintain.ingest(ep("e1", "sales-01", ORG, "approved", "2026-10-08"), s, acl, judge=bridge.make_judge(fake('{"verdict":"conflict"}')))
    assert d[0].action == "tentative" and s.get(old.id).status == "trial"


def test_locked_record_is_never_overwritten(facts):
    acl = FakeACL(); s, old = seeded(facts, acl, status="locked")
    facts["e1"] = [NEW]
    d = maintain.ingest(ep("e1", "exec-01", ORG, "approved", "2026-10-08"), s, acl, judge=bridge.make_judge(fake('{"verdict":"conflict"}')))
    assert d[0].action == "tentative" and s.get(old.id).status == "locked"


def test_same_needs_coverage_and_unrelated_adds(facts):
    acl = FakeACL(); s, old = seeded(facts, acl)
    facts["e1"] = ["Atlas pilot deadline: November 6, 2026 (confirmed)."]
    d = maintain.ingest(ep("e1", "sales-01", f"{ORG}/sales", "discussion", "2026-10-05"), s, acl, judge=bridge.make_judge(fake('{"verdict":"same"}')))
    assert d[0].action == "reject" and "duplicate" in d[0].reason and s.get(old.id).status == "trial"
    # a narrower-scope old memory does not cover an org-wide candidate: `same` is not allowed to drop it
    s2 = MemoryStore(); facts["e2"] = [OLD]
    maintain.ingest(ep("e2", "sales-01", f"{ORG}/sales", "discussion", "2026-10-01"), s2, acl, judge=lambda c, m: "unrelated")
    facts["e3"] = [OLD.replace("is due", "is due on")]
    d = maintain.ingest(ep("e3", "sales-01", ORG, "tentative", "2026-10-02"), s2, acl, judge=bridge.make_judge(fake('{"verdict":"same"}')))
    assert d[0].action == "add"
    facts["e4"] = ["The Borealis office opens March 2, 2027."]
    d = maintain.ingest(ep("e4", "exec-01", ORG, "approved", "2026-10-09"), s, acl, judge=bridge.make_judge(fake('{"verdict":"unrelated"}')))
    assert d[0].action == "add" and s.get(old.id).status == "trial"


def test_no_judge_output_ever_deletes(facts):
    """Whatever the model emits, memories are only ever retired via the approved-supersede rule, never removed."""
    for raw in ('{"verdict":"same"}', '{"verdict":"conflict"}', '{"verdict":"unrelated"}', "garbage", '{"verdict":"delete"}'):
        acl = FakeACL(); s, old = seeded(facts, acl)
        facts["e1"] = [NEW]
        d = maintain.ingest(ep("e1", "sales-01", f"{ORG}/sales", "tentative", "2026-10-08"), s, acl, judge=bridge.make_judge(fake(raw)))
        assert s.get(old.id).status == "trial", raw
        assert all(m.status != "retired" for m in s.all())


# ---------- job_all helpers (pure python) ----------

def test_operation_matches_pair_action():
    acl = maintain._OpenACL(); acl.can_approve = lambda m, sc: True
    for auth in ("approved", "tentative", "discussion"):
        for cd in ("2026-09-01", "2026-10-08"):
            old = Memory("m1", OLD, "a", "e0", "2026-10-01", scope=ORG)
            cand = {"text": NEW, "date": cd, "authority": auth, "scope": ORG}
            want = maintain._pair_action(cand, old, "conflict", "a", acl)
            assert job_all.operation("conflict", auth, cd, old.date) == want
            assert job_all.operation(None, auth, cd, old.date) == maintain._pair_action(cand, old, None, "a", acl)


def test_label_first_tokens_with_fake_tokenizer():
    class Tok:
        def __call__(self, text, add_special_tokens=False):
            # split like a BPE would: {" verdict ":" <label pieces> "}
            label = json.loads(text)["verdict"]
            pieces = {"same": [10], "conflict": [11], "unrelated": [12, 13]}[label]
            return {"input_ids": [1, 2, 3] + pieces + [4]}
    pre, first = job_all.label_first_tokens(Tok())
    assert pre == [1, 2, 3] and first == {"same": 10, "conflict": 11, "unrelated": 12}


def test_metrics_and_threshold():
    rows = [dict(gold="same", pred="same", probs={"same": .9, "conflict": .05, "unrelated": .05}),
            dict(gold="conflict", pred="conflict", probs={"same": .1, "conflict": .85, "unrelated": .05}),
            dict(gold="conflict", pred="same", probs={"same": .6, "conflict": .3, "unrelated": .1}),
            dict(gold="unrelated", pred=None, probs={"same": .2, "conflict": .7, "unrelated": .1})]
    for r in rows: r.update(authority="approved", cand_date="2026-10-08", old_date="2026-10-01", latency_ms=10.0)
    m = job_all.metrics(rows, threshold=0.8)
    assert m["accuracy"] == 0.5 and m["invalid_rate"] == 0.25 and m["confusion"]["unrelated"]["None"] == 1
    assert m["thresholded"]["same"] == dict(n_argmax=2, n_kept=1, coverage=0.5, precision=1.0, recall_vs_gold=1.0)
    assert m["thresholded"]["conflict"]["n_kept"] == 1 and m["thresholded"]["conflict"]["precision"] == 1.0
    assert m["operations"]["harmful_overwrites"] == 0 and m["operations"]["wrongful_noop_drops"] == 1
