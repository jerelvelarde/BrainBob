"""BrainBob HTTP + SSE server for the 3D frontend. See CONTRACT.md."""
from __future__ import annotations

import asyncio
import dataclasses
import json
import os
import queue
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable

from fastapi import FastAPI, Header, HTTPException, Query
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
        self._seq = 0

    def emit(self, type: str, **data: Any) -> dict:
        with self._lock:
            self._seq += 1
            ev = {"type": type, "ts": time.time(), "seq": self._seq, **to_dict(data)}
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

    def history(self, after: int | None = None) -> list:
        with self._lock:
            return [e for e in self._h if after is None or e["seq"] > after]


class _Scoped:
    """Store view that stamps scope/author on every add (the curator does not take them)."""

    def __init__(self, store, scope, author):
        self._s, self._scope, self._author = store, scope, author

    def add(self, text, **kw):
        if self._scope:
            kw["scope"] = self._scope
        if self._author:
            kw["author"] = self._author
        return self._s.add(text, **kw)

    def __getattr__(self, name):
        return getattr(self._s, name)


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
               episode_factory=Episode, task_factory=Task, sse_once=False,
               episodes_path=None) -> FastAPI:
    """events: object with emit(type, **data), subscribe(), history(after=None); defaults to a local Bus.
    The core (curator/evaluator/store) is expected to emit memory.* / evidence.* itself via the
    same bus; the server emits episode.ingested, memory.retrieved, answer.produced.
    episodes_path: jsonl file where every posted episode is appended (and reloaded from at start)."""
    bus = events or Bus()
    app = FastAPI(title="BrainBob")
    app.add_middleware(CORSMiddleware, allow_origins=ORIGINS, allow_methods=["*"], allow_headers=["*"])
    tasks: dict[str, dict] = {}
    evidence_log: list[dict] = []
    episodes: dict[str, dict] = {}
    app.state.bus = bus
    if episodes_path and os.path.exists(episodes_path):
        with open(episodes_path, encoding="utf8") as f:
            for line in f:
                if line.strip():
                    d = json.loads(line)
                    episodes[d["id"]] = d

    def guarded(fn, *a):
        try:
            return fn(*a)
        except KeyError:
            raise HTTPException(404, "unknown memory id")
        except PermissionError as e:
            raise HTTPException(403, str(e))
        except ValueError as e:
            raise HTTPException(422, str(e))

    @app.post("/episodes")
    def post_episode(body: dict):
        text = body.get("text")
        if not isinstance(text, str) or not text.strip():
            raise HTTPException(422, "text required")
        eid = "ep-" + uuid.uuid4().hex[:8]
        rec = {"id": eid, "text": text, "date": body.get("date") or time.strftime("%Y-%m-%d"),
               "source": body.get("source") or "api", "scope": body.get("scope") or "team",
               "author": body.get("author")}
        episodes[eid] = rec
        if episodes_path:
            with open(episodes_path, "a", encoding="utf8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        # Bug workaround: curator.py writes memory.origin = episode.source (the label), but origin must be
        # the episode id. curator.py is not ours to edit, so the Episode handed to it carries the id as source.
        ep = episode_factory(id=eid, text=text, date=rec["date"], source=eid)
        mems = curator.ingest(ep, _Scoped(store, body.get("scope"), body.get("author")))
        bus.emit("episode.ingested", episode_id=eid, source=rec["source"], n_memories=len(mems))
        return {"episode_id": eid, "memories": to_dict(mems)}

    @app.get("/episodes/{eid}")
    def get_episode(eid: str):
        rec = episodes.get(eid)
        if rec is None:
            raise HTTPException(404, "unknown episode id")
        return {k: rec.get(k) for k in ("id", "text", "date", "source", "scope")}

    @app.post("/ask")
    def post_ask(body: dict):
        q = body.get("question")
        if not isinstance(q, str) or not q.strip():
            raise HTTPException(422, "question required")
        tid = "t-" + uuid.uuid4().hex[:8]
        reader = body.get("reader")
        mems = store.search(q, reader=reader) if reader else store.search(q)
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

    @app.post("/memories/{mid}/correct")
    def post_correct(mid: str, body: dict):
        text = body.get("text")
        if not isinstance(text, str) or not text.strip():
            raise HTTPException(422, "text required")
        new, old = guarded(store.correct, mid, text, body.get("author") or "user")
        return {"memory": to_dict(new), "retired_id": old.id}

    @app.post("/memories/{mid}/retire")
    def post_retire(mid: str, body: dict | None = None):
        body = body or {}
        return {"memory": to_dict(guarded(store.retire, mid, body.get("reason") or "", body.get("author")))}

    @app.post("/memories/{mid}/lock")
    def post_lock(mid: str, body: dict):
        owner = body.get("owner")
        if not isinstance(owner, str) or not owner.strip():
            raise HTTPException(422, "owner required")
        return {"memory": to_dict(guarded(store.lock, mid, owner))}

    @app.post("/memories/{mid}/resolve")
    def post_resolve(mid: str, body: dict):
        owner = body.get("owner")
        if not isinstance(owner, str) or not owner.strip():
            raise HTTPException(422, "owner required")
        return {"memory": to_dict(guarded(store.resolve, mid, owner, body.get("action"), body.get("text")))}

    @app.get("/memories/{mid}/history")
    def get_history(mid: str):
        by_id = {m.id: m for m in store.all()}
        if mid not in by_id:
            raise HTTPException(404, "unknown memory id")
        chain = [by_id[mid]]
        while chain[0].supersedes in by_id:  # back to the root
            chain.insert(0, by_id[chain[0].supersedes])
        while True:  # forward to the newest correction
            nxt = [m for m in by_id.values() if m.supersedes == chain[-1].id]
            if not nxt or nxt[0] in chain:
                break
            chain.append(nxt[0])
        ids = {m.id for m in chain}

        def related(ev):
            refs = [ev.get("memory_id"), ev.get("new_id"), (ev.get("memory") or {}).get("id")]
            return any(r in ids for r in refs if r)
        return {"chain": to_dict(chain), "events": [e for e in bus.history() if related(e)]}

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
    async def get_events(after: int | None = Query(None), last_event_id: str | None = Header(None)):
        if after is None and last_event_id and last_event_id.strip().isdigit():
            after = int(last_event_id)

        async def gen():
            q = bus.subscribe()
            try:
                hist = bus.history(after)
                last = hist[-1]["seq"] if hist else (after or 0)
                for ev in hist:
                    yield {"id": str(ev["seq"]), "data": json.dumps(ev)}
                yield {"id": str(last), "data": json.dumps({"type": "replay.done", "seq": last})}
                if sse_once:
                    return
                while True:
                    try:
                        ev = q.get_nowait()
                    except queue.Empty:
                        await asyncio.sleep(0.1)
                        continue
                    if ev["seq"] <= last:  # already replayed
                        continue
                    last = ev["seq"]
                    yield {"id": str(ev["seq"]), "data": json.dumps(ev)}
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

    events.set_log("events.jsonl")  # reloads history and continues seq after a restart
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
                     episode_factory=types.Episode, task_factory=types.Task,
                     episodes_path="episodes.jsonl")
    uvicorn.run(app, host="127.0.0.1", port=3001)


if __name__ == "__main__":
    main()
