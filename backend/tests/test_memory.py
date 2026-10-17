import sys, pathlib, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import pytest
from brainbob import events
from brainbob.memory import MemoryStore


@pytest.fixture(autouse=True)
def fresh_events(tmp_path):
    events.reset(); events.set_log(str(tmp_path / "events.jsonl"))
    yield
    events.reset()


def add(s, text, scope="team"):
    return s.add(text, author="a", origin="ep-1", date="2026-10-17", scope=scope)[0]


def test_scope_ancestor_filter():
    s = MemoryStore()
    for t, sc in [("alpha rule krab", "krusty-krab"), ("alpha rule sales", "krusty-krab/sales"),
                  ("alpha rule john", "krusty-krab/sales/john"), ("alpha rule sales2", "krusty-krab/sales2")]:
        add(s, t, sc)
    got = {m.scope for m in s.search("alpha rule", reader="krusty-krab/sales/john")}
    assert got == {"krusty-krab", "krusty-krab/sales", "krusty-krab/sales/john"}  # sales2 not matched by prefix
    assert {m.scope for m in s.search("alpha rule", reader="krusty-krab/sales")} == {"krusty-krab", "krusty-krab/sales"}
    assert len(s.search("alpha rule")) == 4


def test_old_jsonl_without_new_fields(tmp_path):
    p = tmp_path / "m.jsonl"
    p.write_text(json.dumps({"id": "m1", "text": "old fact", "author": "a", "origin": "x", "date": "d"}) + "\n", encoding="utf8")
    m = MemoryStore(str(p)).get("m1")
    assert m.supersedes is None and m.owner is None and m.scope == "team"


def test_correct_lock_resolve():
    s = MemoryStore()
    m = add(s, "launch is Oct 24")
    new, old = s.correct(m.id, "launch is Oct 25", "bob")
    assert new.supersedes == m.id and old.status == "retired" and old.reason == f"superseded by {new.id}"
    r = add(s, "no dogs in kitchen")
    s.lock(r.id, "krabs")
    with pytest.raises(PermissionError): s.resolve(r.id, "squid", "keep")
    with pytest.raises(PermissionError): s.retire(r.id, "x")
    s.resolve(r.id, "krabs", "keep")
    assert s.get(r.id).status == "locked"
    types = [e["type"] for e in events.history()]
    for t in ("memory.added", "memory.retired", "memory.corrected", "memory.locked", "memory.resolved"):
        assert t in types


def test_seq_continues_after_restart(tmp_path):
    p = str(tmp_path / "ev.jsonl")
    events.reset(); events.set_log(p)
    events.emit("a"); events.emit("b")
    events.reset(); events.set_log(p)
    assert [e["seq"] for e in events.history()] == [1, 2]
    assert events.emit("c")["seq"] == 3
    assert [e["type"] for e in events.history(after=2)] == ["c"]
