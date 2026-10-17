"""Adapter base class (spec section 10 operations) and the benchmark token counter.

The runner sets ``seed`` and ``replicate`` on the instance before ``reset``. An adapter
never receives oracle data: only the world manifest (no timeline), timeline items as
they are delivered, and the checkpoint's visible fields through ``open_session``.
"""
from __future__ import annotations

import math

SURFACES = ("search", "record", "source", "history", "export", "events", "session_cache")


def count_tokens(text: str) -> int:
    """Benchmark token count: ceil(characters / 4). Provider-neutral and deterministic;
    the scorer recomputes it on the delivered context rather than trusting the adapter."""
    return math.ceil(len(text or "") / 4)


class Adapter:
    name: str = "base"
    parallel_safe: bool = False  # True lets the runner run several worlds of this condition at once
    seed: int = 0
    replicate: int = 0

    def reset(self, world_manifest: dict, budget: dict, workdir: str) -> None:
        raise NotImplementedError

    def ingest(self, source_event: dict) -> dict:
        return {"ok": True}

    def apply_policy(self, policy_event: dict) -> dict:
        return {"ok": True}

    def maintain(self, cutoff_seq: int, budget: dict) -> dict:
        return {"ok": True, "op": "noop"}

    def open_session(self, principal: str, task: str, requested_time: str, purpose: str | None,
                     budget: dict) -> dict:
        """Return ``{"session_id", "context", "context_tokens", "source_ids"}`` (extra keys allowed)."""
        raise NotImplementedError

    def act(self, session: dict, task: str) -> dict:
        """Return ``{"answer", "cited_event_ids", "cost"}``; ``error`` when the act failed."""
        raise NotImplementedError

    def inspect_surface(self, principal: str, surface: str, request: dict) -> dict | None:
        return None  # unsupported

    def export_trace(self) -> dict:
        return {}

    def close_session(self, session: dict) -> None:
        return None
