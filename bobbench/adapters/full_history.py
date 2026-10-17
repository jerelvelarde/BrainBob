"""Baseline: authorized full history.

Every raw source the principal can read at ``requested_time`` (judged by the reference
policy engine from the policy events this adapter itself received; this filter is part
of the baseline's definition, not derived from gold), oldest first. When the sources
exceed the context budget, the most recent ones that fit are kept and the omission is
stated in the context and in the session metadata.
"""
from __future__ import annotations

from ..adapter import count_tokens
from ..policy import Policy
from ..schema import parse_time
from .no_memory import NoMemoryAdapter


def render_source(e: dict) -> str:
    head = (f"[{e['event_id']}] {e.get('occurred_at')} | from {e.get('actor_id')} | to {', '.join(e.get('audience') or [])}"
            f" | channel {e.get('channel')} | source {e.get('source_id')} rev {e.get('source_revision')}")
    if e.get("effective_at") and e.get("effective_at") != e.get("occurred_at"):
        head += f" | effective {e.get('effective_at')}"
    return head + "\n" + (e.get("content") or "").strip()


def assemble(sources: list[dict], budget_tokens: int, label: str) -> tuple[str, list[str], list[str]]:
    """Oldest-first context of the most recent sources that fit. Returns (context, included, omitted)."""
    ordered = sorted(sources, key=lambda e: (parse_time(e.get("occurred_at")), e["seq"]))
    blocks = [render_source(e) for e in ordered]

    def header(n_in, n_omit):
        h = f"{label}: {n_in} of {len(ordered)} sources, oldest first."
        if n_omit:
            h += f" TRUNCATED: the {n_omit} oldest sources were omitted to fit the {budget_tokens}-token context budget."
        return h

    keep = len(blocks)
    while keep >= 0:
        chosen = blocks[len(blocks) - keep:] if keep else []
        text = header(keep, len(blocks) - keep) + ("\n\n" + "\n\n".join(chosen) if chosen else "")
        if count_tokens(text) <= budget_tokens:
            break
        keep -= 1
    if keep < 0:  # even the bare header does not fit
        return "", [], [e["event_id"] for e in ordered]
    included = [e["event_id"] for e in ordered[len(ordered) - keep:]] if keep else []
    omitted = [e["event_id"] for e in ordered[:len(ordered) - keep]]
    return text, included, omitted


class FullHistoryAdapter(NoMemoryAdapter):
    name = "full_history"
    parallel_safe = True
    permission_filter = True

    def reset(self, world_manifest: dict, budget: dict, workdir: str) -> None:
        super().reset(world_manifest, budget, workdir)
        self._policy = Policy(world_manifest)
        self._sources: list[dict] = []

    def ingest(self, source_event: dict) -> dict:
        self._sources.append(dict(source_event))
        return {"ok": True, "stored": True, "event_id": source_event.get("event_id")}

    def apply_policy(self, policy_event: dict) -> dict:
        return self._policy.apply(policy_event)

    def open_session(self, principal, task, requested_time, purpose, budget) -> dict:
        if self.permission_filter:
            at = parse_time(requested_time)
            pool = [e for e in self._sources if self._policy.can_read(principal, e, at, purpose)]
            label = f"Sources readable by {principal} at {requested_time}"
        else:
            pool = list(self._sources)
            label = "All sources received so far (no permission filter)"
        limit = int((budget or {}).get("context_tokens", 4000))
        context, included, omitted = assemble(pool, limit, label)
        return self._new_session(principal, requested_time, purpose, context, included,
                                 truncated=bool(omitted), omitted_event_ids=omitted,
                                 candidate_count=len(pool), received_count=len(self._sources))
