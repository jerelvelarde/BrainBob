"""Rusty Rod organization model and permission checks (demo identity, not authentication)."""
from __future__ import annotations

import json
from dataclasses import dataclass

ORG = "rusty-rod"


@dataclass(frozen=True)
class Member:
    id: str
    team: str
    role: str = "member"


class Org:
    def __init__(self, members, org: str = ORG):
        self.org = org
        self.members = {m.id: m for m in members}

    @classmethod
    def load(cls, path) -> "Org":
        with open(path, encoding="utf8") as f:
            d = json.load(f)
        return cls([Member(m["id"], m["team"], m.get("role", "member")) for m in d["members"]], d.get("org", ORG))

    def _m(self, member):
        return self.members.get(member)

    def team_path(self, team: str) -> str:
        return f"{self.org}/{team}"

    def member_path(self, member: str) -> str:
        m = self.members[member]
        return f"{self.org}/{m.team}/{m.id}"

    def readable_scopes(self, member: str) -> list[str]:
        m = self.members[member]
        return [self.org, self.team_path(m.team), self.member_path(member)]

    def can_read(self, member: str, scope: str) -> bool:
        return self._m(member) is not None and scope in self.readable_scopes(member)

    def can_write(self, member: str, scope: str) -> bool:
        return self._m(member) is not None and scope in self.readable_scopes(member)

    def can_approve(self, member: str, scope: str) -> bool:
        m = self._m(member)
        if m is None:
            return False
        if scope == self.org:
            return m.role == "approver"
        if scope == self.team_path(m.team):
            return True
        return scope == self.member_path(member)
