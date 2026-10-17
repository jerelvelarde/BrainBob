"""Diagnostic controls (spec section 11). Neither is a valid maintained baseline.

- ``always_refuse``: declines every task without a model call; should fail useful tasks.
- ``unfiltered``: full history with no permission filter; should fail boundary tasks.
"""
from __future__ import annotations

from .full_history import FullHistoryAdapter
from .no_memory import NoMemoryAdapter

REFUSAL_TEXT = "I can't help with that request."


class AlwaysRefuseAdapter(NoMemoryAdapter):
    name = "always_refuse"

    def act(self, session: dict, task: str) -> dict:
        return {"answer": REFUSAL_TEXT, "cited_event_ids": [],
                "cost": {"model": None, "calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "usd": 0.0,
                         "cached": False, "retries": 0}, "error": None}


class UnfilteredAdapter(FullHistoryAdapter):
    name = "unfiltered"
    permission_filter = False
