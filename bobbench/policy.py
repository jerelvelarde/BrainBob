"""Reference policy engine (trusted). Time-aware, replayed in ``seq`` order.

Rules (bobbench/CONTRACT.md):
- membership of an organization or team scope gives ``read`` on that scope;
- an individual scope is readable by its owner;
- channel and any other cross-scope access only through grants;
- ``grant``: subject gets ``permissions`` on ``object`` from ``effective_at`` until
  ``expires_at`` (exclusive), only for ``purpose`` when one is set;
- ``revoke``: ends matching earlier grants (all permissions, or only those listed)
  from its ``effective_at``; ``approver`` is an ``approve`` grant;
- ``member_remove`` ends membership from its ``effective_at``; access is judged at
  the requested time, so removal changes future delivery only.

A grant subject may be a principal, a scope (its members at that time) or an
organization (its principals). Membership is never implied by ``principal.org``;
it comes from ``member_add`` events or the optional manifest ``memberships`` list.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from .schema import NEG_INF, POS_INF, parse_time

READ = "read"


@dataclass
class _Grant:
    seq: int
    subject: str
    object: str
    perms: frozenset
    start: datetime
    end: datetime
    purpose: str | None
    policy_id: str


@dataclass
class _Revoke:
    seq: int
    subject: str
    object: str
    perms: frozenset | None  # None = every permission
    at: datetime
    purpose: str | None


class Policy:
    def __init__(self, world: dict):
        self.principals = {p["id"]: p for p in world.get("principals", [])}
        self.scopes = {s["id"]: s for s in world.get("scopes", [])}
        self.orgs = {o["id"] for o in world.get("organizations", [])}
        self._members: dict[tuple, list] = defaultdict(list)  # (principal, scope) -> [(at, seq, is_member)]
        self._grants: list[_Grant] = []
        self._revokes: list[_Revoke] = []
        self._sources: dict[str, dict] = {}
        self.applied: list[str] = []
        self.watermark = -1
        for m in world.get("memberships") or []:
            who = m.get("principal") or m.get("subject")
            self._members[(who, m["scope"])].append((parse_time(m.get("since"), NEG_INF), -1, True))
            if m.get("until"):
                self._members[(who, m["scope"])].append((parse_time(m["until"]), -1, False))

    # ------------------------------------------------------------ replay

    @classmethod
    def replay(cls, world: dict, upto_seq: int | None = None) -> "Policy":
        """Policy state after every timeline item with ``seq < upto_seq`` (all if None)."""
        p = cls(world)
        for it in world.get("timeline", []):
            if upto_seq is not None and it["seq"] >= upto_seq:
                break
            if it.get("type") == "policy":
                p.apply(it)
            elif it.get("type") == "source":
                p.observe_source(it)
        return p

    def apply(self, ev: dict) -> dict:
        op = ev.get("op")
        seq = int(ev.get("seq", self.watermark + 1))
        if seq <= self.watermark:
            raise ValueError(f"policy event {ev.get('policy_id')!r} out of order (seq {seq} <= {self.watermark})")
        at = parse_time(ev.get("effective_at"), NEG_INF)
        subj, obj = ev.get("subject"), ev.get("object")
        perms = ev.get("permissions")
        purpose = ev.get("purpose") or None
        if op == "member_add":
            self._members[(subj, obj)].append((at, seq, True))
        elif op == "member_remove":
            self._members[(subj, obj)].append((at, seq, False))
        elif op in ("grant", "approver"):
            ps = frozenset(perms or []) if op == "grant" else frozenset(perms or []) | {"approve"}
            self._grants.append(_Grant(seq, subj, obj, ps, at, parse_time(ev.get("expires_at"), POS_INF),
                                       purpose, ev.get("policy_id", "")))
        elif op == "revoke":
            self._revokes.append(_Revoke(seq, subj, obj, frozenset(perms) if perms else None, at, purpose))
        else:
            raise ValueError(f"unknown policy op {op!r}")
        self.watermark = seq
        self.applied.append(ev.get("policy_id", ""))
        return {"ok": True, "policy_id": ev.get("policy_id"), "op": op}

    def observe_source(self, ev: dict) -> None:
        self._sources[ev["event_id"]] = ev
        self.watermark = max(self.watermark, int(ev.get("seq", self.watermark)))

    # ------------------------------------------------------------ queries

    def is_member(self, principal: str, scope: str, at) -> bool:
        at = parse_time(at)
        state = False
        for t, _seq, val in sorted(self._members.get((principal, scope), []), key=lambda x: (x[0], x[1])):
            if t <= at:
                state = val
        return state

    def _subject_covers(self, subject: str, principal: str, at: datetime) -> bool:
        if subject == principal:
            return True
        if subject in self.scopes and self.is_member(principal, subject, at):
            return True
        if subject in self.orgs and self.principals.get(principal, {}).get("org") == subject:
            return True
        return False

    def _grant_active(self, g: _Grant, perm: str, principal: str, at: datetime, purpose: str | None) -> bool:
        if perm not in g.perms or not (g.start <= at < g.end):
            return False
        if g.purpose is not None and g.purpose != purpose:
            return False
        if not self._subject_covers(g.subject, principal, at):
            return False
        for r in self._revokes:
            if (r.seq > g.seq and r.at <= at and r.subject == g.subject and r.object == g.object
                    and (r.perms is None or perm in r.perms)
                    and (r.purpose is None or r.purpose == g.purpose)):
                return False
        return True

    def can(self, principal: str, perm: str, scope: str, at, purpose: str | None = None) -> bool:
        s = self.scopes.get(scope)
        if s is None or principal not in self.principals:
            return False
        at = parse_time(at)
        if perm == READ:
            kind = s.get("kind")
            if kind in ("organization", "team") and self.is_member(principal, scope, at):
                return True
            if kind == "individual" and s.get("owner") == principal:
                return True
        return any(self._grant_active(g, perm, principal, at, purpose) for g in self._grants if g.object == scope)

    def can_read(self, principal: str, event: dict, at, purpose: str | None = None) -> bool:
        """A source is readable if any scope in its audience is readable."""
        return any(self.can(principal, READ, a, at, purpose) for a in event.get("audience") or [])

    def readable_scopes(self, principal: str, at, purpose: str | None = None) -> list[str]:
        return [sid for sid in self.scopes if self.can(principal, READ, sid, at, purpose)]

    def readable_events(self, principal: str, at, purpose: str | None = None) -> list[dict]:
        """Observed sources (delivered so far) readable by ``principal`` at ``at``, in seq order."""
        return sorted((e for e in self._sources.values() if self.can_read(principal, e, at, purpose)),
                      key=lambda e: e["seq"])
