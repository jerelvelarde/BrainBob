"""BrainBob core candidate, using the actual store, ACL, curator and maintenance.

This is an in-process component adapter, not an HTTP conformance claim. Its
serialization, authority mapping, retrieval and budget selection are declared
candidate behavior. No oracle or reference policy engine is imported here.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import sys

# The application imports this package as `brainbob`; use that same module
# identity so hooks, events, usage and role configuration are not duplicated.
_BACKEND = str(Path(__file__).resolve().parents[2] / "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)
from brainbob import curator, events, llm, maintain
from brainbob.acl import Org
from brainbob.memory import MemoryStore
from brainbob.types import Episode

from bobbench.schema import parse_time
from bobbench.adapters.full_history import assemble
from bobbench.adapters.no_memory import NoMemoryAdapter


class BrainBobAdapter(NoMemoryAdapter):
    parallel_safe = False  # backend usage and event logs are process-global

    def __init__(self, mode="maintained", answer_fn=None):
        if mode not in ("append_only", "maintained"):
            raise ValueError(f"unknown BrainBob mode: {mode}")
        super().__init__(answer_fn=answer_fn)
        self.mode = self.name = mode

    def reset(self, world_manifest, budget, workdir):
        super().reset(world_manifest, budget, workdir)
        self.org = Org.from_world(deepcopy(world_manifest))
        # Never reload a previous world's persistent state, including reruns.
        path = Path(workdir) / "brainbob-memories.jsonl"
        if path.exists():
            raise FileExistsError(f"candidate state already exists: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        self.store = MemoryStore(str(path))
        self.sources = {}
        self.receipts = []
        self._policy_revision = 0
        self._usage_start = llm.usage()
        self._usage_checkpoint = deepcopy(self._usage_start)
        history = events.history()
        self._event_start = history[-1]["seq"] if history else 0

    def apply_policy(self, policy_event):
        receipt = self.org.apply(deepcopy(policy_event))
        self._policy_revision += 1
        self.receipts.append({"operation": "policy", **receipt})
        return {"ok": True, **receipt}

    def ingest(self, source_event):
        event = deepcopy(source_event)
        eid = event["event_id"]
        if eid in self.sources:
            if event != self.sources[eid]:
                raise ValueError(f"source event ID reused with different data: {eid}")
            return {"ok": True, "duplicate": True, "event_id": eid}
        self.sources[eid] = event
        actor = event["actor_id"]
        # Approval is mapped only from trusted delivery + authenticated policy;
        # the word 'approved' in document text never confers permission.
        at = event["received_at"]
        acl = self.org.view(at=at)
        before = len(self.store.all())
        results = []
        episodes = []
        for scope in event["audience"]:
            approved = event.get("channel") == "trusted" and acl.can_approve(actor, scope)
            episode = Episode(id=eid, text=event["content"], date=event["occurred_at"],
                              source=event["source_id"], author=actor, scope=scope,
                              authority="approved" if approved else "discussion")
            episodes.append(asdict(episode))
            if self.mode == "maintained":
                rows = maintain.ingest(episode, self.store, acl)
            else:
                rows = curator.ingest(episode, self.store, author=actor)
            results.extend(asdict(row) for row in rows)
        receipt = {"ok": True, "event_id": eid, "added": len(self.store.all()) - before,
                   "operation": "ingest", "mode": self.mode, "episodes": episodes, "results": results}
        self.receipts.append(receipt)
        return receipt

    def maintain(self, cutoff_seq, budget):
        # Core maintenance occurs at write time, without task/gold feedback.
        return {"ok": True, "mode": self.mode, "operation": "write_time_only", "cutoff_seq": cutoff_seq}

    def open_session(self, principal, task, requested_time, purpose, budget):
        candidates = self.store.search(task, k=max(1, len(self.store.all())))
        grouped = defaultdict(list)
        for memory in candidates:
            if not self.org.can_read(principal, memory.scope, requested_time, purpose):
                continue
            event = self.sources.get(memory.origin)
            if event is None:
                continue
            if parse_time(event["effective_at"]) > parse_time(requested_time):
                continue
            grouped[memory.origin].append(memory)
        selected = []
        for eid, memories in grouped.items():
            # Preserve citation lineage; deliver extracted memory, not the full
            # original source (which may include a superseded statement).
            source = deepcopy(self.sources[eid])
            source["audience"] = sorted({m.scope for m in memories})
            source["content"] = "\n".join(
                f"Memory {m.id}; authority={m.authority}; status={m.status}: {m.text}"
                for m in memories
            )
            selected.append(source)
        limit = int((budget or {}).get("context_tokens", 4000))
        context, included, omitted = assemble(selected, limit, f"BrainBob {self.mode} extracted memories")
        return self._new_session(principal, requested_time, purpose, context, included,
                                 policy_revision=self._policy_revision, budget=deepcopy(budget),
                                 truncated=bool(omitted), omitted_event_ids=omitted,
                                 candidate_count=len(selected), received_count=len(self.sources))

    def act(self, session, task):
        # A cached context is not valid after policy changes. Require a new
        # session/time envelope rather than replaying potentially revoked data.
        if session.get("policy_revision") != self._policy_revision:
            session.update(context="", source_ids=[], context_tokens=0)
            return {"answer": "", "cited_event_ids": [], "cost": {}, "error": "policy changed; reopen session"}
        result = super().act(session, task)
        usage = llm.usage()
        delta = self._usage_delta(usage, self._usage_checkpoint)
        self._usage_checkpoint = deepcopy(usage)
        cost = dict(result.get("cost") or {})
        for output, field in (("calls", "calls"), ("prompt_tokens", "pt"), ("completion_tokens", "ct"), ("usd", "usd")):
            cost[output] = cost.get(output, 0) + sum(row[field] for row in delta.values())
        cost["backend_roles"] = delta
        cost["backend_retry_count"] = None  # core usage does not expose attempts
        result["cost"] = cost
        return result

    @staticmethod
    def _usage_delta(current, previous):
        return {role: {key: row.get(key, 0) - previous.get(role, {}).get(key, 0)
                       for key in ("calls", "cached", "pt", "ct", "usd", "usd_all")}
                for role, row in current.items()}

    def inspect_surface(self, principal, surface, request):
        return None  # no claim about production HTTP, exports, streams or caches

    def export_trace(self):
        return {**super().export_trace(), "mode": self.mode, "receipts": deepcopy(self.receipts),
                "memories": [asdict(m) for m in self.store.all()], "policy": self.org.export(),
                "operations": events.history(after=self._event_start),
                "model_configuration": llm.configuration(),
                "backend_usage": self._usage_delta(llm.usage(), self._usage_start),
                "limitations": ["component adapter; HTTP surfaces untested", "no automatic dependency propagation",
                                "historical retired-memory retrieval unsupported", "core retries incompletely counted",
                                "backend extraction/judge caches can be reused across replicates"]}
