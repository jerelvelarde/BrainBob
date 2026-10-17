"""Baseline: no persistent memory. The fresh answerer gets only the task envelope."""
from __future__ import annotations

from ..adapter import Adapter


def _default_answer_fn():
    from ..answer import answer
    return answer


class NoMemoryAdapter(Adapter):
    name = "no_memory"
    parallel_safe = True

    def __init__(self, answer_fn=None):
        self._answer_fn = answer_fn
        self._sessions = 0
        self._log: list[dict] = []

    @property
    def answer_fn(self):
        if self._answer_fn is None:
            self._answer_fn = _default_answer_fn()
        return self._answer_fn

    def reset(self, world_manifest: dict, budget: dict, workdir: str) -> None:
        self.world_id = world_manifest.get("world_id")
        self._sessions = 0
        self._log = []

    def ingest(self, source_event: dict) -> dict:
        return {"ok": True, "stored": False}

    def apply_policy(self, policy_event: dict) -> dict:
        return {"ok": True, "stored": False}

    def _new_session(self, principal, requested_time, purpose, context, source_ids, **meta) -> dict:
        self._sessions += 1
        from ..adapter import count_tokens
        return {"session_id": f"{self.name}-{self._sessions}", "context": context,
                "context_tokens": count_tokens(context), "source_ids": list(source_ids),
                "principal": principal, "requested_time": requested_time, "purpose": purpose, **meta}

    def open_session(self, principal, task, requested_time, purpose, budget) -> dict:
        return self._new_session(principal, requested_time, purpose, "", [])

    def act(self, session: dict, task: str) -> dict:
        r = self.answer_fn(task, session["context"], principal=session.get("principal"),
                           requested_time=session.get("requested_time"), purpose=session.get("purpose"),
                           cache_salt=f"rep{self.replicate}")
        self._log.append({"session_id": session["session_id"], "error": r.get("error")})
        return {"answer": r.get("answer", ""), "cited_event_ids": r.get("cited_event_ids", []),
                "cost": r.get("cost", {}), "error": r.get("error")}

    def export_trace(self) -> dict:
        return {"adapter": self.name, "sessions": self._sessions, "acts": self._log}
