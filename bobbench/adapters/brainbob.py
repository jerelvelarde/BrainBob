"""BrainBob adapter for the Bob (Shared Brain) Benchmark: conditions `append_only` (curator.ingest only) and
`maintained` (maintain.ingest at write time + audit_recent in maintain()). See bobbench/CONTRACT.md.

Translation only, declared here (spec section 10): a source event becomes one BrainBob Episode per audience scope,
text "<actor_id>: <content>" (BrainBob's native transcript format), date = occurred_at, author = actor_id;
authority = "approved" only for trusted-channel sources when policy lets the author approve on that scope at occurred_at,
else "discussion".
Policy events go to brainbob.acl.Org.apply. Nothing reads the oracle; no facts, filters or answers are added.

BrainBob decides only the context: the top memories the principal may read at requested_time, one block per memory
labelled with the event id its origin maps back to ("[evt-..] date | scope | authority | status" + text, like
full_history's source blocks). Answering is the shared Track A answerer (bobbench.answer.answer), so CITED ids are
event ids as the model wrote them.

This is the only file in bobbench/ that imports BrainBob. BrainBob's event bus is process-global: reset() clears it,
so run one BrainBob adapter at a time per process (parallel_safe stays False).
"""
from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
import os
import sys
import types as _types
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
for _p in (str(ROOT), str(BACKEND)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from brainbob import audit as bb_audit, curator as bb_curator  # noqa: E402
from brainbob import events as bb_events, llm as bb_llm, maintain as bb_maintain  # noqa: E402
from brainbob.acl import Org  # noqa: E402
from brainbob.memory import MemoryStore  # noqa: E402
from brainbob.types import Answer, Episode  # noqa: E402

from bobbench.adapter import Adapter as _Base, count_tokens  # noqa: E402
from bobbench.schema import parse_time  # noqa: E402

TOP_K = 10
MODES = ("append_only", "maintained")
SURFACES = ("search", "record", "source", "history", "export", "events", "session_cache")
HINT = ("BrainBob shared memory: {n} memories this principal may read, most relevant first. Each block starts with the "
        "source event id, then date, scope, authority (approved / tentative / discussion) and status. Prefer approved, "
        "active memories; status \"tentative, conflicts with ...\" marks an unresolved conflict.")


def _usage_diff(a: dict, b: dict) -> dict:
    out = {}
    for role, v in b.items():
        p = a.get(role, {})
        d = {k: v[k] - p.get(k, 0) for k in v}
        if d.get("calls"):
            out[role] = d
    return out


def _cost(diff: dict) -> dict:
    tot = lambda k: sum(v.get(k, 0) for v in diff.values())
    return {"usd": tot("usd"), "usd_all": tot("usd_all"), "calls": tot("calls"), "cached": tot("cached"),
            "prompt_tokens": tot("pt"), "completion_tokens": tot("ct"), "by_role": diff}


def _models() -> dict:
    return {r: c["model"] for r, c in bb_llm._roles().items()}


def _jsonable(o):
    return json.loads(json.dumps(o, default=lambda x: dataclasses.asdict(x) if dataclasses.is_dataclass(x) else str(x)))


class BrainBobAdapter(_Base):
    def __init__(self, mode: str = "maintained", seed: int = 0, top_k: int = TOP_K, answer_fn=None, judge=None):
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}")
        self.mode, self.seed, self.top_k = mode, seed, top_k
        self.judge = judge
        if answer_fn is None:
            from bobbench.answer import answer as answer_fn
        self.answer_fn = answer_fn
        self.name = mode
        self.system = "brainbob"
        self.store = None

    # ---- lifecycle -----------------------------------------------------------------------------------------
    def reset(self, world_manifest: dict, budget: dict, workdir: str) -> None:
        self.world = world_manifest
        self.budget = dict(budget or {})
        self.state_dir = os.path.join(workdir, f"brainbob-{self.mode}")
        # Preserve previous run evidence. New worlds/runs get new directories;
        # rerunning into existing candidate state is an error, never a deletion.
        os.makedirs(self.state_dir, exist_ok=False)
        bb_events.reset()
        bb_events.set_log(os.path.join(self.state_dir, "events.jsonl"))
        self.store = MemoryStore(os.path.join(self.state_dir, "memory.jsonl"))
        self.episodes_path = os.path.join(self.state_dir, "episodes.jsonl")
        open(self.episodes_path, "w").close()
        self.acl = Org.from_world(world_manifest)
        self.episodes: list[Episode] = []
        self.ep_event: dict[str, str] = {}     # episode id -> event_id
        self.ep_seq: dict[str, int] = {}
        self.ep_at: dict[str, str] = {}
        self.event_eps: dict[str, list[str]] = {}
        self.sources: dict[str, dict] = {}
        self.clock = None                      # latest received_at / policy effective_at seen
        self.ops: list[dict] = []              # every receipt, in call order
        self.decisions: list[dict] = []
        self.sessions: dict[str, dict] = {}
        self.audits: list[dict] = []           # one row per audit_recent run (maintained only)
        self._u0 = bb_llm.usage()
        self._usage_checkpoint = copy.deepcopy(self._u0)
        self.ops.append({"op": "reset", "world_id": world_manifest.get("world_id"), "mode": self.mode,
                         "seed": self.seed, "state_dir": self.state_dir, "budget": self.budget})

    def _tick(self, t):
        if t and (self.clock is None or parse_time(t) > parse_time(self.clock)):
            self.clock = t

    def _event_ids(self, memories) -> list[str]:
        out = []
        for m in memories:
            e = self.ep_event.get(m.origin)
            if e and e not in out:
                out.append(e)
        return out

    # ---- writes ------------------------------------------------------------------------------------------------
    def ingest(self, source_event: dict) -> dict:
        ev = copy.deepcopy(source_event)
        eid, actor = ev["event_id"], ev.get("actor_id")
        if eid in self.sources:
            if ev != self.sources[eid]:
                raise ValueError(f"source event ID reused with different data: {eid}")
            return {"ok": True, "duplicate": True, "event_id": eid}
        self.sources[eid] = ev
        at = ev.get("occurred_at") or ev.get("effective_at") or ev.get("received_at")
        self._tick(ev.get("received_at") or at)
        u0 = bb_llm.usage()
        rec = {"op": "ingest", "event_id": eid, "seq": ev.get("seq"), "episodes": []}
        for i, scope in enumerate(ev.get("audience") or []):
            epid = f"{eid}@{i}"
            authority = "approved" if ev.get("channel") == "trusted" and self.acl.can_approve(actor, scope, at=at) else "discussion"
            text = f"{actor}: {ev.get('content', '')}" if actor else ev.get("content", "")
            src = f"{ev.get('source_id')}#{ev.get('source_revision')} ({ev.get('channel', 'trusted')})"
            ep = Episode(epid, text, at or "", src, author=actor, scope=scope, authority=authority)
            self.episodes.append(ep)
            self.ep_event[epid], self.ep_seq[epid], self.ep_at[epid] = eid, ev.get("seq", 0), at
            self.event_eps.setdefault(eid, []).append(epid)
            with open(self.episodes_path, "a", encoding="utf8") as f:
                f.write(json.dumps({"id": epid, "text": text, "date": ep.date, "source": src, "scope": scope,
                                    "author": actor, "authority": authority}, ensure_ascii=False) + "\n")
            erec = {"episode_id": epid, "scope": scope, "authority": authority,
                    "author_can_write": self.acl.can_write(actor, scope, at=at)}
            if self.mode == "append_only":
                added = bb_curator.ingest(ep, self.store, author=actor)
                erec["memory_ids"] = [m.id for m in added]
            else:
                ds = bb_maintain.ingest(ep, self.store, self.acl.view(at), judge=self.judge)
                erec["decisions"] = self._keep(ds, epid, "ingest")
                erec["memory_ids"] = [d.memory_id for d in ds if d.memory_id]
            rec["episodes"].append(erec)
        rec["cost"] = _cost(_usage_diff(u0, bb_llm.usage()))
        self.ops.append(rec)
        return rec

    def _keep(self, decisions, epid, phase):
        out = []
        for d in decisions or []:
            row = dict(dataclasses.asdict(d), episode_id=epid, event_id=self.ep_event.get(epid), phase=phase)
            self.decisions.append(row); out.append(row)
        return out

    def apply_policy(self, policy_event: dict) -> dict:
        self._tick(policy_event.get("effective_at"))
        rec = dict(self.acl.apply(policy_event), op_kind="apply_policy", seq=policy_event.get("seq"))
        self.ops.append(rec)
        return rec

    def maintain(self, cutoff_seq: int, budget: dict) -> dict:
        if self.mode != "maintained":
            rec = {"op": "maintain", "mode": self.mode, "ran": False, "cutoff_seq": cutoff_seq,
                   "reason": "append_only: no maintenance"}
            self.ops.append(rec)
            return rec
        eps = [e for e in self.episodes if (self.ep_seq.get(e.id) or 0) <= cutoff_seq]
        u0 = bb_llm.usage()

        def propose(memory, episode):  # audit's default proposer, with the policy as of the episode's time
            ds = bb_maintain.ingest(episode, self.store, self.acl.view(self.ep_at.get(episode.id)), judge=self.judge)
            self._keep(ds, episode.id, "maintain")
            return ds

        rep = bb_audit.audit_recent(self.store, eps, seed=self.seed, propose=propose)
        ev_of = lambda ids: list(dict.fromkeys(self.ep_event.get(i) for i in ids))
        audit = {"seed": self.seed, "cutoff_seq": cutoff_seq, "eligible_ids": rep.eligible_ids,
                 "sampled_ids": rep.sampled_ids, "eligible_event_ids": ev_of(rep.eligible_ids),
                 "sampled_event_ids": ev_of(rep.sampled_ids),
                 "coverage": len(rep.sampled_ids) / len(rep.eligible_ids) if rep.eligible_ids else 0.0,
                 "counts": rep.counts}
        self.audits.append(audit)
        rec = {"op": "maintain", "mode": self.mode, "ran": True, "budget": dict(budget or {}), **audit,
               "checks": rep.checks, "cost": _cost(_usage_diff(u0, bb_llm.usage()))}
        self.ops.append(rec)
        return rec

    def _audit_trace(self):
        """Audit sampling for score.py. coverage = sampled / eligible episodes per run; stale-memory coverage needs the
        oracle's decisive events, so score.py computes it from sampled_event_ids."""
        if self.mode != "maintained":
            return "unsupported"
        ever = list(dict.fromkeys(e for a in self.audits for e in a["sampled_event_ids"]))
        ingested = list(self.event_eps)
        return {"supported": True, "runs": self.audits, "events_ever_sampled": ever,
                "events_ever_sampled_coverage": len(ever) / len(ingested) if ingested else 0.0}

    # ---- sessions ----------------------------------------------------------------------------------------------
    def _readable(self, principal, at, purpose) -> set:
        scopes = set(self.acl.known_scopes()) | {m.scope for m in self.store.all()}
        return {s for s in scopes if self.acl.can_read(principal, s, at=at, purpose=purpose)}

    def _status(self, m, shown):
        if m.status != "tentative":
            return "active"
        refs = [f"[{self.ep_event.get(by.origin)}]" for c in (m.conflicts_with or []) for by in [shown.get(c)] if by]
        return "tentative, conflicts with " + (", ".join(dict.fromkeys(refs)) if refs else "a memory not shown")

    def _context(self, mems) -> str:
        """One block per memory, labelled with its source event id; conflict refs only name memories shown here."""
        if not mems:
            return ""
        shown = {m.id: m for m in mems}
        blocks = [f"[{self.ep_event.get(m.origin, m.origin)}] {m.date} | scope {m.scope} | authority "
                  f"{m.authority or 'discussion'} | status {self._status(m, shown)}\n{m.text.strip()}" for m in mems]
        return HINT.format(n=len(mems)) + "\n\n" + "\n\n".join(blocks)

    def open_session(self, principal: str, task: str, requested_time: str, purpose: str | None, budget: dict) -> dict:
        """Permissions are evaluated now, against the policy at requested_time; nothing is reused from older sessions."""
        readable = self._readable(principal, requested_time, purpose)
        pool = self.store.search(task, k=max(len(self.store.all()), 1))
        mems = [copy.copy(m) for m in pool if m.scope in readable
                and parse_time(self.sources[self.ep_event[m.origin]].get("effective_at") or m.date)
                <= parse_time(requested_time)][: self.top_k]
        limit = (budget or {}).get("context_tokens") or self.budget.get("context_tokens")
        ctx, omitted = self._context(mems), 0
        while limit and mems and count_tokens(ctx) > limit:
            mems.pop(); omitted += 1
            ctx = self._context(mems)
        sid = "s-" + uuid.uuid4().hex[:10]
        s = {"session_id": sid, "context": ctx, "context_tokens": count_tokens(ctx), "source_ids": self._event_ids(mems),
             "memory_ids": [m.id for m in mems], "principal": principal, "requested_time": requested_time,
             "purpose": purpose, "task": task, "readable_scopes": sorted(readable), "omitted_for_budget": omitted,
             "policy_watermark": len(self.acl.log)}
        self.sessions[sid] = {"mems": mems, **s}
        self.ops.append({"op": "open_session", **{k: v for k, v in s.items() if k != "context"},
                         "context_sha256": hashlib.sha256(ctx.encode()).hexdigest()})
        return s

    def act(self, session: dict, task: str) -> dict:
        st = self.sessions[session["session_id"]]
        p, at, pur = st["principal"], st["requested_time"], st["purpose"]
        access_at = at
        if st["policy_watermark"] != len(self.acl.log) and self.clock and parse_time(self.clock) > parse_time(at):
            access_at = self.clock
        mems = [m for m in st["mems"] if self.acl.can_read(p, m.scope, at=access_at, purpose=pur)]  # recheck before acting
        keep = {m.id for m in mems}
        dropped = [m.id for m in st["mems"] if m.id not in keep]
        if dropped:
            st["mems"] = mems
            session["context"] = st["context"] = self._context(mems)
            session["context_tokens"] = count_tokens(session["context"])
            session["source_ids"] = self._event_ids(mems)
        r = self.answer_fn(task, st["context"], principal=p, requested_time=at, purpose=pur,
                           cache_salt=f"rep{getattr(self, 'replicate', 0)}")
        usage = bb_llm.usage()
        memory_cost = _cost(_usage_diff(self._usage_checkpoint, usage))
        self._usage_checkpoint = copy.deepcopy(usage)
        cost = dict(r.get("cost") or {})
        for field in ("usd", "calls", "prompt_tokens", "completion_tokens"):
            cost[field] = cost.get(field, 0) + memory_cost[field]
        cost["backend_roles"] = memory_cost["by_role"]
        cost["backend_retry_count"] = None
        cost["custom_judge_usage_unmeasured"] = self.mode == "maintained" and self.judge is not None
        out = {"answer": r.get("answer", ""), "cited_event_ids": list(r.get("cited_event_ids") or []),
               "cost": cost, "error": r.get("error"), "recheck_dropped": dropped}
        self.ops.append({"op": "act", "session_id": session["session_id"], "principal": p,
                         "answering_cost": dict(r.get("cost") or {}), **out})
        return out

    def close_session(self, session: dict) -> None:
        self.sessions.pop(session.get("session_id"), None)
        self.ops.append({"op": "close_session", "session_id": session.get("session_id")})

    # ---- surfaces ----------------------------------------------------------------------------------------------
    def _client(self, at, purpose, isolated_bus=False):
        import server
        from fastapi.testclient import TestClient
        stub = _types.SimpleNamespace(answer=lambda q, mems, now=None, fresh=False: Answer("", []))
        app = server.create_app(self.store, _types.SimpleNamespace(ingest=None), stub, None, lambda *a: False,
                                events=server.Bus() if isolated_bus else bb_events, sse_once=True,
                                episodes_path=self.episodes_path, org=self.acl.view(at, purpose))
        return TestClient(app)

    def _targets(self, request) -> list[str]:
        ids = list(request.get("memory_ids") or ([request["memory_id"]] if request.get("memory_id") else []))
        for eid in ([request["event_id"]] if request.get("event_id") else []) + list(request.get("event_ids") or []):
            eps = set(self.event_eps.get(eid, []))
            ids += [m.id for m in self.store.all() if m.origin in eps and m.id not in ids]
        return ids

    def inspect_surface(self, principal: str, surface: str, request: dict) -> dict | None:
        """Real responses of BrainBob's HTTP server (create_app, in process, no port) with X-BrainBob-Member.
        None for surfaces the server does not have (export, session_cache) and unknown ones."""
        request = dict(request or {})
        if surface not in ("search", "record", "source", "history", "events"):
            return None
        at = request.get("at") or request.get("requested_time") or self.clock
        H = {"X-BrainBob-Member": principal}
        c = self._client(at, request.get("purpose"), isolated_bus=(surface == "search"))
        calls = []

        def call(method, path, **kw):
            r = c.request(method, path, headers=H, **kw)
            try: body = r.json()
            except ValueError: body = r.text
            calls.append({"method": method, "path": path, "status": r.status_code, "body": body})
            return r.status_code, body

        if surface == "search":  # POST /ask is the server's retrieval surface; the probe agent makes no model call
            call("POST", "/ask", json={"question": request.get("query") or request.get("q") or ""})
        elif surface == "record":
            call("GET", "/memories")
            want = set(self._targets(request))
            if want and calls[-1]["status"] == 200:
                calls[-1]["matched"] = [m for m in calls[-1]["body"] if m.get("id") in want]
        elif surface == "source":
            eps = []
            for eid in ([request["event_id"]] if request.get("event_id") else []) + list(request.get("event_ids") or []):
                eps += self.event_eps.get(eid, [])
            by_id = {m.id: m for m in self.store.all()}
            eps += [by_id[i].origin for i in (request.get("memory_ids") or [request.get("memory_id")]) if i in by_id]
            eps += list(request.get("episode_ids") or [])
            for ep in dict.fromkeys(eps):
                call("GET", f"/episodes/{ep}")
        elif surface == "history":
            for mid in self._targets(request):
                call("GET", f"/memories/{mid}/history")
        elif surface == "events":
            path = "/events" + (f"?after={int(request['after'])}" if request.get("after") is not None else "")
            with c.stream("GET", path, headers=H) as r:
                text, status = "".join(r.iter_text()), r.status_code
            msgs, cur = [], {}
            for line in text.splitlines():
                if line.startswith("id:"): cur["id"] = line[3:].strip()
                elif line.startswith("data:"): cur["data"] = json.loads(line[5:].strip())
                elif not line.strip() and cur: msgs.append(cur); cur = {}
            if cur: msgs.append(cur)
            calls.append({"method": "GET", "path": path, "status": status, "body": [m.get("data") for m in msgs]})
        out = {"surface": surface, "principal": principal, "at": at, "supported": True, "responses": calls}
        self.ops.append({"op": "inspect_surface", "surface": surface, "principal": principal, "at": at,
                         "statuses": [x["status"] for x in calls]})
        return out

    # ---- trace -------------------------------------------------------------------------------------------------
    def export_trace(self) -> dict:
        usage = _usage_diff(self._u0, bb_llm.usage())
        try:
            from bobbench.answer import config as answer_config
            answering = answer_config()
        except Exception:  # noqa: BLE001
            answering = None
        acts = [o for o in self.ops if o.get("op") == "act"]
        mem_roles = ("curator", "judge") if self.mode == "maintained" else ("curator",)
        configuration = bb_llm.configuration()
        pair_model = _models()["judge"]
        if self.mode == "maintained" and self.judge is not None:
            pair_model = getattr(self.judge, "model_id", "custom:unidentified")
            # The audit uses a distinct supported/contradicted/insufficient
            # prompt and still runs on the configured backend judge.
            configuration["memory_pair_judge"] = {"implementation": "injected_callable", "model": pair_model, "usage": None}
        t = {"system": "brainbob", "adapter": "bobbench/adapters/brainbob.py", "condition": self.mode, "seed": self.seed,
             "top_k": self.top_k, "world_id": self.world.get("world_id"),
             "models": {"memory": {**{r: _models()[r] for r in mem_roles}, "pair_judge": pair_model if self.mode == "maintained" else None}, "answering": answering},
             "model_configuration": configuration,
             "cost": {"memory": _cost(usage), "answering_usd": sum((o.get("answering_cost") or {}).get("usd", 0) for o in acts),
                      "answering_calls": len(acts)},
             "audit": self._audit_trace(), "operations": self.ops, "decisions": self.decisions,
             "episode_event_map": dict(self.ep_event), "acl": self.acl.export(),
             "memories": [dataclasses.asdict(m) for m in self.store.all()], "events": bb_events.history(),
             "surfaces": {s: s in ("search", "record", "source", "history", "events") for s in SURFACES},
             "translation": "source -> one Episode per audience scope, text '<actor_id>: <content>', date occurred_at; "
                            "authority approved iff trusted channel and acl.can_approve(actor, scope, at=occurred_at)",
             "limitations": ["export/session-cache HTTP probes unsupported", "physical erasure not measured",
                             "retired-memory historical retrieval unsupported", "retry telemetry incomplete",
                             "custom semantic judge usage unmeasured; audit judge remains separately configured",
                             "extraction/judge disk caches can be reused across replicates"]}
        t = _jsonable(t)
        t["trace_sha256"] = hashlib.sha256(json.dumps(t, sort_keys=True).encode()).hexdigest()
        return t
