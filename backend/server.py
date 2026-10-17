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

from fastapi import FastAPI, Header, HTTPException, Query, Request
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
               episodes_path=None, org=None, ingest=None) -> FastAPI:
    """events: object with emit(type, **data), subscribe(), history(after=None); defaults to a local Bus.
    The core (curator/evaluator/store) is expected to emit memory.* / evidence.* itself via the
    same bus; the server emits episode.ingested, memory.retrieved, answer.produced.
    episodes_path: jsonl file where every posted episode is appended (and reloaded from at start).
    org: brainbob.acl.Org or None. None = no permission checks. With an org, the viewer comes from header
    X-BrainBob-Member (or ?member=, for EventSource): a demo identity, NOT authentication.
    ingest: optional fn(episode, store, org) -> decisions, used instead of curator.ingest (maintain.ingest)."""
    bus = events or Bus()
    app = FastAPI(title="BrainBob")
    app.add_middleware(CORSMiddleware, allow_origins=ORIGINS, allow_methods=["*"], allow_headers=["*"])
    password = os.environ.get("BRAINBOB_DEMO_PASSWORD", "")
    if os.environ.get("BRAINBOB_REQUIRE_AUTH") == "1" and len(password) < 16:
        raise RuntimeError("Set BRAINBOB_DEMO_PASSWORD to at least 16 characters before hosting")
    if password:
        from brainbob.demo_auth import DemoAuth
        app.add_middleware(DemoAuth, password=password)
    sse_max_seconds = float(os.environ.get("BRAINBOB_SSE_MAX_SECONDS", "240"))

    @app.get("/healthz")
    def health():
        # Process readiness only; provider access is checked separately.
        return {"status": "ok"}

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

    def who(request: Request, required: bool = True):
        if org is None:
            return None
        m = request.headers.get("x-brainbob-member") or request.query_params.get("member")
        if not m or m not in org.members:
            if required:
                raise HTTPException(401, "X-BrainBob-Member header required (demo identity)")
            return None
        return m

    def mem_scopes() -> dict:
        return {m.id: getattr(m, "scope", None) for m in store.all()}

    def can_see_mem(viewer, scope) -> bool:
        return org is None or (isinstance(scope, str) and org.can_read(viewer, scope))

    def visible_mem(viewer, mid) -> bool:
        return org is None or can_see_mem(viewer, mem_scopes().get(mid))

    def need_mem(viewer, mid):
        if org is not None and not visible_mem(viewer, mid):
            raise HTTPException(404, "unknown memory id")

    def need_write(viewer, mid):
        need_mem(viewer, mid)
        if org is not None and not org.can_write(viewer, mem_scopes().get(mid)):
            raise HTTPException(403, "no write permission")

    def acting_member(viewer, supplied, field, fallback=None):
        if org is not None:
            if supplied is not None and supplied != viewer:
                raise HTTPException(403, f"{field} must be the acting member")
            return viewer
        return supplied or fallback

    def event_visible(viewer, ev, ms=None) -> bool:
        if org is None:
            return True
        # Answers can contain private questions or uncited information. Memory
        # references alone cannot establish who may read the answer text.
        if ev.get("type") in ("answer.produced", "memory.retrieved") and ev.get("viewer") != viewer:
            return False
        # Old/core rejection events have text but no scope. Do not broadcast
        # unscoped source text to every account; the writer gets HTTP decisions.
        if ev.get("type") == "memory.rejected" and not can_see_mem(viewer, ev.get("scope")):
            return False
        ms = ms if ms is not None else mem_scopes()
        mids = [ev.get(k) for k in ("memory_id", "new_id", "old_id")]
        mids.append(ev["memory"].get("id") if isinstance(ev.get("memory"), dict) else None)
        mids += list(ev.get("memory_ids") or []) + list(ev.get("cited_ids") or [])
        for r in mids:
            if r and not can_see_mem(viewer, ms.get(r)):
                return False
        eid = ev.get("episode_id")
        if eid:
            rec = episodes.get(eid)
            if rec is None or not org.can_read(viewer, rec.get("scope") or ""):
                return False
        return True

    def filter_report(o, viewer, ms):
        if isinstance(o, list):
            out = []
            for x in o:
                if isinstance(x, dict):
                    mid = x.get("memory_id") or (x.get("id") if x.get("id") in ms else None)
                    if mid and not can_see_mem(viewer, ms.get(mid)):
                        continue
                out.append(filter_report(x, viewer, ms))
            return out
        if isinstance(o, dict):
            return {k: filter_report(v, viewer, ms) for k, v in o.items() if not (k in ms and not can_see_mem(viewer, ms[k]))}
        return o

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
    def post_episode(body: dict, request: Request):
        if org is not None:
            viewer = who(request, required=False) or (body.get("author") if body.get("author") in org.members else None)
            if viewer is None:
                raise HTTPException(401, "X-BrainBob-Member header required (demo identity)")
            if body.get("author") and body["author"] != viewer:
                raise HTTPException(403, "author must be the acting member")
            body = dict(body, author=viewer, scope=body.get("scope") or org.member_path(viewer))
            if not org.can_write(viewer, body["scope"]):
                raise HTTPException(403, "no write permission for scope")
            if body.get("authority") == "approved" and not org.can_approve(viewer, body["scope"]):
                raise HTTPException(403, "no approve permission for scope")
        text = body.get("text")
        if not isinstance(text, str) or not text.strip():
            raise HTTPException(422, "text required")
        eid = "ep-" + uuid.uuid4().hex[:8]
        rec = {"id": eid, "text": text, "date": body.get("date") or time.strftime("%Y-%m-%d"),
               "source": body.get("source") or "api", "scope": body.get("scope") or "team",
               "author": body.get("author"), "authority": body.get("authority") or "discussion"}
        episodes[eid] = rec
        if episodes_path:
            with open(episodes_path, "a", encoding="utf8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        ep = episode_factory(id=eid, text=text, date=rec["date"], source=rec["source"])
        scoped = _Scoped(store, body.get("scope"), body.get("author"))
        if org is not None and ingest is not None:
            for k in ("author", "scope", "authority"):
                try:
                    setattr(ep, k, rec[k])
                except Exception:  # noqa: BLE001
                    pass
            res = ingest(ep, scoped, org)
            mems = [getattr(d, "memory", d) for d in (res or []) if getattr(d, "memory", d) is not None]
        else:
            mems = curator.ingest(ep, scoped)
        if not any(e.get("type") == "episode.ingested" and e.get("episode_id") == eid for e in bus.history()):
            bus.emit("episode.ingested", episode_id=eid, source=rec["source"], n_memories=len(mems))  # curator did not
        return {"episode_id": eid, "memories": to_dict(mems)}

    @app.get("/episodes/{eid}")
    def get_episode(eid: str, request: Request):
        viewer = who(request)
        rec = episodes.get(eid)
        if rec is None or (org is not None and not org.can_read(viewer, rec.get("scope") or "")):
            raise HTTPException(404, "unknown episode id")
        keys = ("id", "text", "date", "source", "scope") + (("author", "authority") if org is not None else ())
        return {k: rec.get(k) for k in keys}

    @app.post("/ask")
    def post_ask(body: dict, request: Request):
        viewer = who(request)
        q = body.get("question")
        if not isinstance(q, str) or not q.strip():
            raise HTTPException(422, "question required")
        tid = "t-" + uuid.uuid4().hex[:8]
        reader = body.get("reader")
        if org is not None:
            try:
                mems = store.search(q, k=200)
            except TypeError:
                mems = store.search(q)
            mems = [m for m in mems if can_see_mem(viewer, getattr(m, "scope", None))]
        else:
            mems = store.search(q, reader=reader) if reader else store.search(q)
        bus.emit("memory.retrieved", task_id=tid, memory_ids=[m.id for m in mems], viewer=viewer)
        ans = agent.answer(q, mems, body.get("now"))
        bus.emit("answer.produced", task_id=tid, answer=ans.text, cited_ids=list(ans.cited_ids), viewer=viewer)
        tasks[tid] = {"viewer": viewer, "question": q, "now": body.get("now"), "memories": mems, "answer": ans}
        return {"task_id": tid, "answer": ans.text, "cited_ids": list(ans.cited_ids), "memories": to_dict(mems)}

    @app.post("/feedback")
    def post_feedback(body: dict, request: Request):
        viewer = who(request)
        rec = tasks.get(body.get("task_id"))
        if rec is None or (org is not None and rec.get("viewer") != viewer):
            raise HTTPException(404, "unknown task_id")
        correct = body.get("correct_answer")
        if not isinstance(correct, str):
            raise HTTPException(422, "correct_answer required")
        q = rec["question"]
        rec["correct_answer"] = correct
        task = task_factory(id=body["task_id"], question=q, now=rec["now"],
                            grade=lambda a: bool(judge(q, correct, a)))
        ev = evaluator.observe(task, rec["memories"], agent.answer)
        out = to_dict(ev)
        evidence_log.extend(out)
        return {"evidence": out}

    @app.post("/review")
    def post_review(request: Request, body: dict | None = None):
        viewer = who(request)
        def confirm(mid):
            """Remove the memory, re-answer a task it harmed with fresh=True, grade with the same judge."""
            for tid in evaluator.stats(mid)["harmed"]:
                rec = tasks.get(tid)
                if rec is None or "correct_answer" not in rec:
                    continue
                ans = agent.answer(rec["question"], [m for m in rec["memories"] if m.id != mid], rec["now"], fresh=True)
                if judge(rec["question"], rec["correct_answer"], ans.text):
                    return True
            return False
        decisions = evaluator.review(confirm)
        out = to_dict(decisions)
        if org is not None:
            out = filter_report(out, viewer, mem_scopes())
        return {"decisions": out}

    @app.post("/memories/{mid}/correct")
    def post_correct(mid: str, body: dict, request: Request):
        viewer = who(request)
        need_write(viewer, mid)
        author = acting_member(viewer, body.get("author"), "author", "user")
        text = body.get("text")
        if not isinstance(text, str) or not text.strip():
            raise HTTPException(422, "text required")
        new, old = guarded(store.correct, mid, text, author)
        return {"memory": to_dict(new), "retired_id": old.id}

    @app.post("/memories/{mid}/retire")
    def post_retire(mid: str, request: Request, body: dict | None = None):
        viewer = who(request)
        need_write(viewer, mid)
        body = body or {}
        author = acting_member(viewer, body.get("author"), "author")
        return {"memory": to_dict(guarded(store.retire, mid, body.get("reason") or "", author))}

    @app.post("/memories/{mid}/lock")
    def post_lock(mid: str, body: dict, request: Request):
        viewer = who(request)
        need_write(viewer, mid)
        owner = body.get("owner")
        if not isinstance(owner, str) or not owner.strip():
            raise HTTPException(422, "owner required")
        owner = acting_member(viewer, owner, "owner")
        return {"memory": to_dict(guarded(store.lock, mid, owner))}

    @app.post("/memories/{mid}/resolve")
    def post_resolve(mid: str, body: dict, request: Request):
        viewer = who(request)
        need_write(viewer, mid)
        owner = body.get("owner")
        if not isinstance(owner, str) or not owner.strip():
            raise HTTPException(422, "owner required")
        owner = acting_member(viewer, owner, "owner")
        return {"memory": to_dict(guarded(store.resolve, mid, owner, body.get("action"), body.get("text")))}

    @app.get("/memories/{mid}/history")
    def get_history(mid: str, request: Request):
        viewer = who(request)
        by_id = {m.id: m for m in store.all()}
        if mid not in by_id or not visible_mem(viewer, mid):
            raise HTTPException(404, "unknown memory id")
        chain = [by_id[mid]]
        while chain[0].supersedes in by_id:  # back to the root
            chain.insert(0, by_id[chain[0].supersedes])
        while True:  # forward to the newest correction
            nxt = [m for m in by_id.values() if m.supersedes == chain[-1].id]
            if not nxt or nxt[0] in chain:
                break
            chain.append(nxt[0])
        if org is not None:  # unreadable revisions are cut out of the chain
            chain = [m for m in chain if can_see_mem(viewer, getattr(m, "scope", None))]
        ids = {m.id for m in chain}
        ms = mem_scopes()

        def related(ev):
            refs = [ev.get("memory_id"), ev.get("new_id"), (ev.get("memory") or {}).get("id")]
            return any(r in ids for r in refs if r)
        return {"chain": to_dict(chain), "events": [e for e in bus.history() if related(e) and event_visible(viewer, e, ms)]}

    @app.get("/memories")
    def get_memories(request: Request, status: str | None = Query(None)):
        viewer = who(request)
        out = []
        for m in store.all():
            if not can_see_mem(viewer, getattr(m, "scope", None)):
                continue
            d = to_dict(m)
            if status and d.get("status") != status:
                continue
            mine = [e for e in evidence_log if e.get("memory_id") == d.get("id")]
            d["evidence_count"] = len(mine)
            d["evidence_flips"] = sum(1 for e in mine if e.get("correct") is False)
            out.append(d)
        return out

    @app.get("/report")
    def get_report(request: Request):
        viewer = who(request)
        data = to_dict(evaluator.report())
        return filter_report(data, viewer, mem_scopes()) if org is not None else data

    @app.get("/events")
    async def get_events(request: Request, after: int | None = Query(None), last_event_id: str | None = Header(None)):
        viewer = who(request)
        if after is None and last_event_id and last_event_id.strip().isdigit():
            after = int(last_event_id)

        async def gen():
            q = bus.subscribe()
            try:
                hist = bus.history(after)
                last = hist[-1]["seq"] if hist else (after or 0)
                for ev in hist:
                    if not event_visible(viewer, ev):
                        continue
                    yield {"id": str(ev["seq"]), "data": json.dumps(ev)}
                yield {"id": str(last), "data": json.dumps({"type": "replay.done", "seq": last})}
                if sse_once:
                    return
                deadline = time.monotonic() + sse_max_seconds
                while time.monotonic() < deadline:
                    try:
                        ev = q.get_nowait()
                    except queue.Empty:
                        await asyncio.sleep(0.1)
                        continue
                    if ev["seq"] <= last:  # already replayed
                        continue
                    last = ev["seq"]
                    if not event_visible(viewer, ev):
                        continue
                    yield {"id": str(ev["seq"]), "data": json.dumps(ev)}
            finally:
                if hasattr(bus, "unsubscribe"):
                    bus.unsubscribe(q)
        # Prevent a frontend reverse proxy from compressing/buffering small SSE
        # frames; replay.done must arrive even when the stream remains idle.
        return EventSourceResponse(gen(), headers={"Cache-Control": "no-store, no-transform"})

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

    # --legacy: no permissions and no write-time maintenance, i.e. the contract the
    # frontend was first integrated against (no member header, no tentative status).
    import sys
    legacy = "--legacy" in sys.argv
    org, ingest_fn = None, None
    if not legacy:
        from brainbob.acl import Org
        org = Org.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "rusty_rod", "org.json"))
        try:
            from brainbob import maintain
            ingest_fn = maintain.ingest
        except Exception:  # noqa: BLE001
            ingest_fn = None
    print("BrainBob backend:", "legacy (no permissions, no maintenance)" if legacy
          else "Rusty Rod permissions + write-time maintenance")
    app = create_app(store, curator, agent, evaluator, judge, events=events,
                     episode_factory=types.Episode, task_factory=types.Task,
                     episodes_path="episodes.jsonl", org=org, ingest=ingest_fn)
    uvicorn.run(app, host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "3001")), workers=1)


if __name__ == "__main__":
    main()
