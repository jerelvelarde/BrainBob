"""BrainBob HTTP + SSE server for the 3D frontend. See CONTRACT.md."""
from __future__ import annotations

import asyncio
import dataclasses
import json
import queue
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

ORIGINS = ["http://127.0.0.1:3000", "http://localhost:3000"]


def to_dict(o: Any) -> Any:
    if o is None or isinstance(o, (str, int, float, bool)):
        return o
    if isinstance(o, dict):
        return {k: to_dict(v) for k, v in o.items()}
    if isinstance(o, (list, tuple, set)):
        return [to_dict(v) for v in o]
    if dataclasses.is_dataclass(o) and not isinstance(o, type):
        return {f.name: to_dict(getattr(o, f.name)) for f in dataclasses.fields(o)}
    if hasattr(o, "model_dump"):
        return o.model_dump()
    if hasattr(o, "__dict__"):
        return {k: to_dict(v) for k, v in vars(o).items() if not k.startswith("_")}
    return str(o)


class Bus:
    """Fallback in-process event bus (used when no core events module is injected)."""

    def __init__(self) -> None:
        self._h: list[dict] = []
        self._subs: list[queue.Queue] = []
        self._lock = threading.Lock()

    def emit(self, type: str, **data: Any) -> dict:
        ev = {"type": type, "ts": time.time(), **to_dict(data)}
        with self._lock:
            self._h.append(ev)
            for q in self._subs:
                q.put(ev)
        return ev

    def subscribe(self) -> queue.Queue:
        q: queue.Queue = queue.Queue()
        with self._lock:
            self._subs.append(q)
        return q

    def unsubscribe(self, q: queue.Queue) -> None:
        with self._lock:
            if q in self._subs:
                self._subs.remove(q)

    def history(self) -> list:
        with self._lock:
            return list(self._h)


@dataclass
class Episode:
    id: str
    text: str
    date: str
    source: str


@dataclass
class Task:
    id: str
    question: str
    grade: Callable[[str], bool]
    now: str | None = None


def create_app(store, curator, agent, evaluator, judge, *, events=None,
               episode_factory=Episode, task_factory=Task, sse_once=False) -> FastAPI:
    """events: object with emit(type, **data), subscribe(), history(); defaults to a local Bus.
    The core (curator/evaluator/store) is expected to emit memory.* / evidence.* itself via the
    same bus; the server emits episode.ingested, memory.retrieved, answer.produced."""
    bus = events or Bus()
    app = FastAPI(title="BrainBob")
    app.add_middleware(CORSMiddleware, allow_origins=ORIGINS, allow_methods=["*"], allow_headers=["*"])
    tasks: dict[str, dict] = {}
    evidence_log: list[dict] = []
    app.state.bus = bus

    @app.post("/episodes")
    def post_episode(body: dict):
        text = body.get("text")
        if not isinstance(text, str) or not text.strip():
            raise HTTPException(422, "text required")
        ep = episode_factory(id="ep-" + uuid.uuid4().hex[:8], text=text,
                             date=body.get("date") or time.strftime("%Y-%m-%d"),
                             source=body.get("source") or "api")
        mems = curator.ingest(ep, store)
        bus.emit("episode.ingested", episode_id=ep.id, source=ep.source, n_memories=len(mems))
        return {"episode_id": ep.id, "memories": to_dict(mems)}

    @app.post("/ask")
    def post_ask(body: dict):
        q = body.get("question")
        if not isinstance(q, str) or not q.strip():
            raise HTTPException(422, "question required")
        tid = "t-" + uuid.uuid4().hex[:8]
        mems = store.search(q)
        bus.emit("memory.retrieved", task_id=tid, memory_ids=[m.id for m in mems])
        ans = agent.answer(q, mems, body.get("now"))
        bus.emit("answer.produced", task_id=tid, answer=ans.text, cited_ids=list(ans.cited_ids))
        tasks[tid] = {"question": q, "now": body.get("now"), "memories": mems, "answer": ans}
        return {"task_id": tid, "answer": ans.text, "cited_ids": list(ans.cited_ids), "memories": to_dict(mems)}

    @app.post("/feedback")
    def post_feedback(body: dict):
        rec = tasks.get(body.get("task_id"))
        if rec is None:
            raise HTTPException(404, "unknown task_id")
        correct = body.get("correct_answer")
        if not isinstance(correct, str):
            raise HTTPException(422, "correct_answer required")
        q = rec["question"]
        task = task_factory(id=body["task_id"], question=q, now=rec["now"],
                            grade=lambda a: bool(judge(q, correct, a)))
        ev = evaluator.observe(task, rec["memories"], agent.answer)
        out = to_dict(ev)
        evidence_log.extend(out)
        return {"evidence": out}

    @app.post("/review")
    def post_review(body: dict | None = None):
        decisions = evaluator.review(lambda *a, **k: True)
        return {"decisions": to_dict(decisions)}

    @app.get("/memories")
    def get_memories(status: str | None = Query(None)):
        out = []
        for m in store.all():
            d = to_dict(m)
            if status and d.get("status") != status:
                continue
            mine = [e for e in evidence_log if e.get("memory_id") == d.get("id")]
            d["evidence_count"] = len(mine)
            d["evidence_flips"] = sum(1 for e in mine if e.get("correct") is False)
            out.append(d)
        return out

    @app.get("/report")
    def get_report():
        return to_dict(evaluator.report())

    @app.get("/events")
    async def get_events():
        async def gen():
            q = bus.subscribe()
            try:
                for ev in bus.history():
                    yield {"data": json.dumps(ev)}
                if sse_once:
                    return
                while True:
                    try:
                        ev = q.get_nowait()
                    except queue.Empty:
                        await asyncio.sleep(0.1)
                        continue
                    yield {"data": json.dumps(ev)}
            finally:
                if hasattr(bus, "unsubscribe"):
                    bus.unsubscribe(q)
        return EventSourceResponse(gen())

    return app


def main() -> None:
    try:
        from brainbob.curator import ingest
        from brainbob.agent import answer
        from brainbob.evaluator import Evaluator
        from brainbob.memory import MemoryStore
        from brainbob import events, llm, types
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: cannot import the brainbob core ({type(e).__name__}: {e}).\n"
              "Run from backend/ with the venv, and make sure brainbob/ is complete.")
        raise SystemExit(1)
    import types as _t
    import uvicorn

    store = MemoryStore("memory.jsonl")
    evaluator = Evaluator(store)
    curator = _t.SimpleNamespace(ingest=ingest)
    agent = _t.SimpleNamespace(answer=answer)

    def judge(question: str, correct: str, ans: str) -> bool:
        r = llm.complete("judge", [{"role": "user", "content":
            f"Question: {question}\nGold answer: {correct}\nResponse: {ans}\n"
            "Is the response correct? Reply with exactly yes or no."}])
        return r.strip().lower().startswith("yes")

    app = create_app(store, curator, agent, evaluator, judge, events=events,
                     episode_factory=types.Episode, task_factory=types.Task)
    uvicorn.run(app, host="127.0.0.1", port=3001)


if __name__ == "__main__":
    main()
