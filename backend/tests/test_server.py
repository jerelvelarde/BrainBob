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
