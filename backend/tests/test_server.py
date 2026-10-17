import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from dataclasses import dataclass
from fastapi.testclient import TestClient
import server


@dataclass
class M:
    id: str
    text: str
    status: str = "trial"


@dataclass
class E:
    memory_id: str
    shown: bool
    correct: bool
    task_id: str


class Store:
    def __init__(self): self.items = []
    def search(self, q, k=40): return list(self.items)
    def all(self): return list(self.items)


def build():
    bus = server.Bus()
    store = Store()

    class Curator:
        def ingest(self, ep, st):
            m = M(f"m{len(st.items)+1}", ep.text)
            st.items.append(m)
            bus.emit("memory.added", memory=m)
            return [m]

    class Agent:
        def answer(self, q, mems, now=None):
            return type("A", (), {"text": "Oct 24", "cited_ids": [m.id for m in mems]})()

    class Ev:
        def observe(self, task, mems, fn):
            assert task.grade("Oct 24") is True and task.grade("x") is False
            return [E(mems[0].id, True, False, task.id)]
        def review(self, confirm): return [{"memory_id": "m1", "action": "promote", "reason": "r", "task_ids": []}]
        def report(self): return {"authors": {"curator": 1}}

    judge = lambda q, c, a: a == c
    app = server.create_app(store, Curator(), Agent(), Ev(), judge, events=bus, sse_once=True)
    return TestClient(app), bus


def test_flow():
    c, bus = build()
    r = c.post("/episodes", json={"text": "launch Oct 24"}).json()
    assert r["memories"][0]["id"] == "m1"
    a = c.post("/ask", json={"question": "when?"}).json()
    assert a["answer"] == "Oct 24" and a["cited_ids"] == ["m1"] and a["task_id"]
    f = c.post("/feedback", json={"task_id": a["task_id"], "correct_answer": "Oct 24"}).json()
    assert f["evidence"][0]["memory_id"] == "m1"
    assert c.post("/review", json={}).json()["decisions"][0]["action"] == "promote"
    ms = c.get("/memories").json()
    assert ms[0]["evidence_count"] == 1
    assert c.get("/memories", params={"status": "retired"}).json() == []
    assert c.get("/report").json() == {"authors": {"curator": 1}}


def test_errors_and_cors():
    c, _ = build()
    assert c.post("/feedback", json={"task_id": "nope", "correct_answer": "x"}).status_code == 404
    assert c.post("/ask", json={}).status_code == 422
    h = c.options("/ask", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"})
    assert h.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_sse_replays_memory_added():
    c, _ = build()
    c.post("/episodes", json={"text": "hello"})
    c.post("/ask", json={"question": "q"})
    with c.stream("GET", "/events") as r:
        body = "".join(r.iter_text())
    for t in ("episode.ingested", "memory.added", "memory.retrieved", "answer.produced"):
        assert t in body


# ---- real MemoryStore + real events module, fake curator/agent (no network) ----
from brainbob import events as core_events
from brainbob.memory import MemoryStore


def build_real(tmp_path):
    core_events.reset(); core_events.set_log(str(tmp_path / "events.jsonl"))
    store = MemoryStore(str(tmp_path / "memory.jsonl"))

    class Curator:
        def ingest(self, ep, st):
            m, _ = st.add(ep.text, author="curator", origin=ep.id, date=ep.date)
            return [m] if m else []

    class Agent:
        def answer(self, q, mems, now=None):
            return type("A", (), {"text": "x", "cited_ids": [m.id for m in mems]})()

    app = server.create_app(store, Curator(), Agent(), None, lambda *a: True, events=core_events,
                            sse_once=True, episodes_path=str(tmp_path / "episodes.jsonl"))
    return TestClient(app)


def test_episode_origin_scope_and_get(tmp_path):
    c = build_real(tmp_path)
    r = c.post("/episodes", json={"text": "rule one", "source": "slack", "scope": "kk/sales", "author": "pat"}).json()
    m = r["memories"][0]
    assert m["origin"] == r["episode_id"] and m["scope"] == "kk/sales" and m["author"] == "pat"
    e = c.get(f"/episodes/{r['episode_id']}").json()
    assert e["text"] == "rule one" and e["source"] == "slack" and e["scope"] == "kk/sales"
    assert (tmp_path / "episodes.jsonl").read_text(encoding="utf8").count("\n") == 1
    assert c.get("/episodes/nope").status_code == 404


def test_ask_reader(tmp_path):
    c = build_real(tmp_path)
    c.post("/episodes", json={"text": "alpha sales fact", "scope": "kk/sales"})
    c.post("/episodes", json={"text": "alpha sales2 fact", "scope": "kk/sales2"})
    a = c.post("/ask", json={"question": "alpha fact", "reader": "kk/sales/john"}).json()
    assert [m["scope"] for m in a["memories"]] == ["kk/sales"]


def test_correct_retire_history(tmp_path):
    c = build_real(tmp_path)
    m1 = c.post("/episodes", json={"text": "launch Oct 24"}).json()["memories"][0]["id"]
    r = c.post(f"/memories/{m1}/correct", json={"text": "launch Oct 25", "author": "bob"}).json()
    assert r["retired_id"] == m1 and r["memory"]["supersedes"] == m1
    h = c.get(f"/memories/{r['memory']['id']}/history").json()
    assert [m["id"] for m in h["chain"]] == [m1, r["memory"]["id"]]
    assert {"memory.added", "memory.retired", "memory.corrected"} <= {e["type"] for e in h["events"]}
    m3 = c.post("/episodes", json={"text": "another fact"}).json()["memories"][0]["id"]
    out = c.post(f"/memories/{m3}/retire", json={"reason": "stale", "author": "bob"}).json()["memory"]
    assert out["status"] == "retired" and out["reason"] == "stale"
    assert c.post("/memories/zzz/retire", json={}).status_code == 404


def test_lock_resolve_403(tmp_path):
    c = build_real(tmp_path)
    mid = c.post("/episodes", json={"text": "no dogs"}).json()["memories"][0]["id"]
    m = c.post(f"/memories/{mid}/lock", json={"owner": "krabs"}).json()["memory"]
    assert m["status"] == "locked" and m["owner"] == "krabs"
    assert c.post(f"/memories/{mid}/resolve", json={"owner": "squid", "action": "retire"}).status_code == 403
    r = c.post(f"/memories/{mid}/resolve", json={"owner": "krabs", "action": "correct", "text": "no pets"}).json()["memory"]
    assert r["supersedes"] == mid and r["owner"] == "krabs" and r["status"] == "locked"


def _sse(c, url, headers=None):
    with c.stream("GET", url, headers=headers or {}) as r:
        body = "".join(r.iter_text())
    msgs, cur = [], {}
    for line in body.splitlines():
        if line.startswith("id:"): cur["id"] = line[3:].strip()
        elif line.startswith("data:"): cur["data"] = json.loads(line[5:].strip())
        elif not line.strip() and cur: msgs.append(cur); cur = {}
    if cur: msgs.append(cur)
    return msgs


import json


def test_sse_seq_replay_done_and_after(tmp_path):
    c = build_real(tmp_path)
    c.post("/episodes", json={"text": "one"}); c.post("/episodes", json={"text": "two"})
    msgs = _sse(c, "/events")
    types = [m["data"]["type"] for m in msgs]
    assert types[-1] == "replay.done" and types.index("replay.done") == len(types) - 1
    assert all(m["id"] == str(m["data"]["seq"]) for m in msgs if m["data"]["type"] != "replay.done")
    last = msgs[-1]["data"]["seq"]
    assert last == max(m["data"]["seq"] for m in msgs[:-1])
    again = _sse(c, "/events?after=2")
    assert [m["data"]["seq"] for m in again[:-1]] == list(range(3, last + 1))
    hdr = _sse(c, "/events", headers={"Last-Event-ID": str(last)})
    assert len(hdr) == 1 and hdr[0]["data"] == {"type": "replay.done", "seq": last}


def test_review_confirm_uses_fresh_and_origin(tmp_path):
    from brainbob.evaluator import Evaluator
    core_events.reset(); core_events.set_log(str(tmp_path / "events.jsonl"))
    store = MemoryStore(str(tmp_path / "memory.jsonl"))
    calls = []

    class Curator:
        def ingest(self, ep, st):
            m, _ = st.add(ep.text, author="curator", origin=ep.id, date=ep.date)
            core_events.emit("episode.ingested", episode_id=ep.id, source=ep.source, n_memories=1)
            return [m]

    class Agent:
        def __init__(self): self.passes = False
        def answer(self, q, mems, now=None, fresh=False):
            calls.append(fresh)
            return type("A", (), {"text": "ok" if fresh and self.passes else "no", "cited_ids": [m.id for m in mems]})()
    agent = Agent()
    ev = Evaluator(store, min_changes=1)
    c = TestClient(server.create_app(store, Curator(), agent, ev, lambda q, g, a: a == "ok" or (a == "no" and False),
                                     events=core_events, sse_once=True, episodes_path=str(tmp_path / "e.jsonl")))
    r = c.post("/episodes", json={"text": "bad fact", "source": "slack"}).json()
    mid = r["memories"][0]["id"]
    assert r["memories"][0]["origin"] == r["episode_id"]
    assert c.get(f"/episodes/{r['episode_id']}").json()["source"] == "slack"
    assert [e["source"] for e in core_events.history() if e["type"] == "episode.ingested"] == ["slack"]
    a = c.post("/ask", json={"question": "q"}).json()
    # make the memory look harmful on this task: judge grades full answer wrong, answer without it right
    class Fn:  # evaluator answer_fn comes from agent.answer; emulate flip via stored evidence
        pass
    from brainbob.types import Evidence
    ev.evidence += [Evidence(mid, True, False, a["task_id"]), Evidence(mid, False, True, a["task_id"])]
    c.post("/feedback", json={"task_id": a["task_id"], "correct_answer": "ok"})
    ev.evidence += [Evidence(mid, True, False, a["task_id"]), Evidence(mid, False, True, a["task_id"])]
    calls.clear()
    assert c.post("/review").json()["decisions"] == [] and store.get(mid).status == "trial" and calls == [True]
    agent.passes = True
    d = c.post("/review").json()["decisions"]
    assert d[0]["action"] == "retire" and store.get(mid).status == "retired"
    assert [e for e in core_events.history() if e["type"] == "memory.retired"][0]["confirmed"] is True
