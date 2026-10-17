"""Organization model and permission checks (demo identity, not authentication).

Two layers:
- Static Rusty Rod rules (org.json): a member reads/writes the org, their team and their own path; approves on their
  team and own path, and on the org scope only with role "approver". Unchanged; at=None behaves exactly as before.
- Dynamic policy (bobbench policy events): several organizations, channel scopes, time-bounded memberships, grants
  (optionally purpose-bound) and approvers. `apply(policy_event)` takes the event dict; member_add / member_remove /
  grant / revoke / add_approver are the same operations as calls.

Rules of the dynamic layer (same as bobbench/policy.py): membership of an organization or team scope (or a scope of
unknown kind) gives read, and here also write, on that scope only (no inheritance up or down); an individual scope is
readable and writable by its owner; channels and other cross-scope access only through grants; approve only from an
`approver` entry or a grant with `approve`. A grant / approver subject may be a principal, a scope (its members at
that time) or an organization (its principals). Membership never follows from a principal's org field; it comes from
member_add or the manifest's optional `memberships` list.

Time: `at` is an ISO 8601 string (date or datetime; naive = UTC). An entry is active at `at` when
effective_at <= at < end, where end is the earlier of expires_at and the effective_at of the remove/revoke that closed it.
at=None means the latest state: every applied entry not closed by a remove/revoke counts, timestamps are ignored.
Purpose: a grant with a purpose only counts when the caller passes that same purpose; memberships ignore purpose.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

ORG = "rusty-rod"
PERMS = ("read", "write", "approve", "publish")


@dataclass(frozen=True)
class Member:
    id: str
    team: str | None = None   # None = a principal with no static team (dynamic policy only)
    role: str = "member"
    org: str | None = None


def _t(s):
    """ISO 8601 string -> aware datetime (naive = UTC); None stays None."""
    if s is None:
        return None
    d = s if isinstance(s, datetime) else datetime.fromisoformat(str(s).strip().replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


@dataclass
class Entry:
    kind: str                 # membership | grant | approver | static_removal
    subject: str
    scope: str
    perms: frozenset = frozenset()
    start: object = None      # aware datetime or None (= always)
    expires: object = None
    closed: object = None     # set by member_remove / revoke: datetime, or True when closed with no time
    purpose: str | None = None
    policy_id: str | None = None
    closed_by: str | None = None

    def active(self, at, purpose=None) -> bool:
        if self.purpose is not None and purpose != self.purpose:
            return False
        if at is None:
            return self.closed is None
        if self.start is not None and at < self.start:
            return False
        if self.expires is not None and at >= self.expires:
            return False
        if self.closed is True or (self.closed is not None and at >= self.closed):
            return False
        return True


class Org:
    def __init__(self, members, org: str = ORG, *, organizations=None, scopes=None):
        self.org = org
        self.members = {m.id: m for m in members}
        self.organizations = dict(organizations or {})      # org id -> name
        self.scopes: dict[str, dict] = {}                    # scope id -> {"org", "kind", "owner"}
        for s in scopes or []:
            self.add_scope(s["id"], s.get("org"), s.get("kind"), s.get("owner"))
        self.entries: list[Entry] = []
        self.log: list[dict] = []                            # applied policy receipts, in order

    @classmethod
    def load(cls, path) -> "Org":
        with open(path, encoding="utf8") as f:
            d = json.load(f)
        return cls([Member(m["id"], m["team"], m.get("role", "member")) for m in d["members"]], d.get("org", ORG))

    @classmethod
    def from_world(cls, manifest: dict) -> "Org":
        """Organizations, principals and scopes of a bobbench world; memberships and rights come only from policy."""
        orgs = {o["id"]: o.get("name", o["id"]) for o in manifest.get("organizations", [])}
        members = [Member(p["id"], None, "member", p.get("org")) for p in manifest.get("principals", [])]
        o = cls(members, next(iter(orgs), ORG), organizations=orgs, scopes=manifest.get("scopes", []))
        for m in manifest.get("memberships") or []:
            o.entries.append(Entry("membership", m.get("principal") or m.get("subject"), m["scope"],
                                   start=_t(m.get("since")), expires=_t(m.get("until"))))
        return o

    # ---- registry -------------------------------------------------------------------------------------------
    def add_scope(self, sid, org=None, kind=None, owner=None):
        self.scopes[sid] = {"org": org, "kind": kind, "owner": owner}

    def add_principal(self, pid, org=None):
        if pid not in self.members:
            self.members[pid] = Member(pid, None, "member", org)

    def known_scopes(self) -> list[str]:
        out = list(self.scopes)
        for m in self.members.values():
            for s in self._static(m.id):
                if s not in out: out.append(s)
        for e in self.entries:
            if e.scope not in out: out.append(e.scope)
        return out

    # ---- static (Rusty Rod) layer ------------------------------------------------------------------------------
    def _m(self, member):
        return self.members.get(member)

    def team_path(self, team: str) -> str:
        return f"{self.org}/{team}"

    def member_path(self, member: str) -> str:
        m = self.members[member]
        if m.team is None:
            own = [s for s, d in self.scopes.items() if d.get("owner") == member]
            return own[0] if own else member
        return f"{self.org}/{m.team}/{m.id}"

    def _static(self, member) -> list[str]:
        m = self._m(member)
        if m is None or m.team is None:
            return []
        return [self.org, self.team_path(m.team), self.member_path(member)]

    def _static_ok(self, member, scope, at) -> bool:
        """Static scope, not closed by a member_remove effective at or before `at`."""
        if scope not in self._static(member):
            return False
        for e in self.entries:
            if e.kind == "static_removal" and e.subject == member and e.scope == scope:
                if at is None or e.start is None or at >= e.start:
                    return False
        return True

    # ---- dynamic layer -----------------------------------------------------------------------------------------
    def _active(self, kind, member, scope, at, purpose=None, perm=None):
        at = _t(at)
        return any(e.kind == kind and e.scope == scope and (perm is None or perm in e.perms) and e.active(at, purpose)
                   and (e.subject == member if kind == "membership" else self._covers(e.subject, member, at))
                   for e in self.entries)

    def _covers(self, subject, member, at) -> bool:
        """A grant subject reaches `member`: the member itself, a scope it belongs to at `at`, or its organization."""
        if subject == member:
            return True
        if subject in self.organizations and (self._m(member) is not None and self._m(member).org == subject):
            return True
        return (subject in self.scopes or subject in self._static(member)) and (
            self._static_ok(member, subject, at) or self._active("membership", member, subject, at))

    def _owner(self, member, scope) -> bool:
        return (self.scopes.get(scope) or {}).get("owner") == member

    def _dynamic(self, member, perm, scope, at, purpose) -> bool:
        if perm in ("read", "write"):
            if self._owner(member, scope):
                return True
            kind = (self.scopes.get(scope) or {}).get("kind")
            if kind in (None, "organization", "team") and self._active("membership", member, scope, at):
                return True
        if perm == "approve" and self._active("approver", member, scope, at):
            return True
        return self._active("grant", member, scope, at, purpose, perm)

    def readable_scopes(self, member: str, at=None, purpose=None) -> list[str]:
        out = [s for s in self._static(member) if self._static_ok(member, s, _t(at))]
        return out + [s for s in self.known_scopes() if s not in out and self.can_read(member, s, at, purpose)]

    def can(self, member, perm, scope, at=None, purpose=None) -> bool:
        if perm == "read": return self.can_read(member, scope, at, purpose)
        if perm == "write": return self.can_write(member, scope, at, purpose)
        if perm == "approve": return self.can_approve(member, scope, at, purpose)
        return self._m(member) is not None and self._dynamic(member, perm, scope, at, purpose)

    def can_read(self, member: str, scope: str, at=None, purpose=None) -> bool:
        if self._m(member) is None:
            return False
        return self._static_ok(member, scope, _t(at)) or self._dynamic(member, "read", scope, at, purpose)

    def can_write(self, member: str, scope: str, at=None, purpose=None) -> bool:
        if self._m(member) is None:
            return False
        return self._static_ok(member, scope, _t(at)) or self._dynamic(member, "write", scope, at, purpose)

    def can_approve(self, member: str, scope: str, at=None, purpose=None) -> bool:
        m = self._m(member)
        if m is None:
            return False
        if m.team is not None and self._static_ok(member, scope, _t(at)):
            if scope == self.org:
                if m.role == "approver":
                    return True
            elif scope in (self.team_path(m.team), self.member_path(member)):
                return True
        return self._dynamic(member, "approve", scope, at, purpose)

    # ---- policy operations -------------------------------------------------------------------------------------
    @staticmethod
    def _closable(e, when) -> bool:
        """Open, or closed later than `when` (a backdated remove/revoke moves the end earlier); never a future entry."""
        if e.start is not None and when is not None and e.start > when:
            return False
        return e.closed is None or (when is not None and e.closed is not True and when < e.closed)

    def _close(self, pred, when, pid):
        n = 0
        for e in self.entries:
            if pred(e) and self._closable(e, when):
                e.closed, e.closed_by = (when if when is not None else True), pid
                n += 1
        return n

    def member_add(self, subject, scope, at=None, expires_at=None, policy_id=None):
        if subject not in self.scopes and subject not in self.organizations:
            self.add_principal(subject)
        self.entries.append(Entry("membership", subject, scope, start=_t(at), expires=_t(expires_at), policy_id=policy_id))

    def member_remove(self, subject, scope, at=None, policy_id=None):
        when = _t(at)
        n = self._close(lambda e: e.kind == "membership" and e.subject == subject and e.scope == scope, when, policy_id)
        if scope in self._static(subject):  # a static Rusty Rod membership ends at `at`
            self.entries.append(Entry("static_removal", subject, scope, start=when, policy_id=policy_id)); n += 1
        return n

    def grant(self, subject, scope, permissions, at=None, expires_at=None, purpose=None, policy_id=None):
        perms = frozenset(permissions or ("read",))
        bad = perms - set(PERMS)
        if bad:
            raise ValueError(f"unknown permissions {sorted(bad)}")
        self.entries.append(Entry("grant", subject, scope, perms, _t(at), _t(expires_at), purpose=purpose, policy_id=policy_id))

    def add_approver(self, subject, scope, at=None, expires_at=None, policy_id=None):
        self.entries.append(Entry("approver", subject, scope, frozenset({"approve"}), _t(at), _t(expires_at), policy_id=policy_id))

    def revoke(self, subject, scope, permissions=None, at=None, purpose=None, policy_id=None):
        """Ends grants of `permissions` (all when empty) on `scope` from `at`; a grant that keeps other permissions
        is re-issued with those. Revoking approve (or everything) also ends approver entries."""
        when, perms = _t(at), frozenset(permissions or PERMS)
        hit = [e for e in self.entries if e.kind == "grant" and e.subject == subject and e.scope == scope
               and self._closable(e, when) and (purpose is None or e.purpose == purpose) and e.perms & perms]
        for e in hit:
            was_open = e.closed is None
            e.closed, e.closed_by = (when if when is not None else True), policy_id
            rest = e.perms - perms
            if rest and was_open:
                self.entries.append(Entry("grant", subject, scope, rest, when if when is not None else e.start, e.expires,
                                          purpose=e.purpose, policy_id=e.policy_id))
        n = len(hit)
        if "approve" in perms:
            n += self._close(lambda e: e.kind == "approver" and e.subject == subject and e.scope == scope, when, policy_id)
        return n

    def apply(self, ev: dict) -> dict:
        """bobbench policy event -> receipt. op: member_add, member_remove, grant, revoke, approver."""
        op, sub, obj, pid = ev.get("op"), ev.get("subject"), ev.get("object"), ev.get("policy_id")
        at, exp, purpose, perms = ev.get("effective_at"), ev.get("expires_at"), ev.get("purpose"), ev.get("permissions")
        if obj is not None and obj not in self.scopes and obj not in self.known_scopes():
            self.add_scope(obj)
        n = 1
        if op == "member_add": self.member_add(sub, obj, at, exp, pid)
        elif op == "member_remove": n = self.member_remove(sub, obj, at, pid)
        elif op == "grant": self.grant(sub, obj, perms, at, exp, purpose, pid)
        elif op == "revoke": n = self.revoke(sub, obj, perms, at, purpose, pid)
        elif op == "approver": self.add_approver(sub, obj, at, exp, pid)
        else: raise ValueError(f"unknown policy op {op!r}")
        rec = {"policy_id": pid, "op": op, "subject": sub, "object": obj, "effective_at": at, "expires_at": exp,
               "purpose": purpose, "permissions": list(perms or []), "applied": True, "entries_changed": n}
        self.log.append(rec)
        return rec

    def view(self, at=None, purpose=None) -> "OrgView":
        return OrgView(self, at, purpose)

    def export(self) -> dict:
        iso = lambda d: d.isoformat() if isinstance(d, datetime) else d
        return {"organizations": dict(self.organizations), "scopes": {k: dict(v) for k, v in self.scopes.items()},
                "members": {k: {"team": m.team, "role": m.role, "org": m.org} for k, m in self.members.items()},
                "entries": [{"kind": e.kind, "subject": e.subject, "scope": e.scope, "perms": sorted(e.perms),
                             "start": iso(e.start), "expires": iso(e.expires), "closed": iso(e.closed),
                             "purpose": e.purpose, "policy_id": e.policy_id, "closed_by": e.closed_by} for e in self.entries],
                "log": list(self.log)}


class OrgView:
    """An Org with `at` and `purpose` bound: the two-argument can_read / can_write / can_approve that maintain.py and
    server.py call. `at` may be moved between calls (the surface probe sets it to the requested time)."""

    def __init__(self, org: Org, at=None, purpose=None):
        self.org, self.at, self.purpose = org, at, purpose

    @property
    def members(self): return self.org.members
    def member_path(self, member): return self.org.member_path(member)
    def readable_scopes(self, member): return self.org.readable_scopes(member, self.at, self.purpose)
    def can_read(self, member, scope): return self.org.can_read(member, scope, self.at, self.purpose)
    def can_write(self, member, scope): return self.org.can_write(member, scope, self.at, self.purpose)
    def can_approve(self, member, scope): return self.org.can_approve(member, scope, self.at, self.purpose)
