"""Dataclasses and JSON loaders for world files (visible) and oracle files (hidden).

Validation is structural: increasing ``seq``, referenced principals/scopes exist,
every checkpoint has exactly one oracle entry. ``check_oracle`` only returns error
strings; the oracle object itself is handed to ``score.py`` alone.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone

ITEM_TYPES = ("source", "policy", "checkpoint")
POLICY_OPS = ("member_add", "member_remove", "grant", "revoke", "approver")
PERMISSIONS = ("read", "write", "approve", "publish")
SCOPE_KINDS = ("organization", "team", "individual", "channel")
CHANNELS = ("trusted", "untrusted")
STRATA = ("legitimate", "boundary", "maintenance")
EXPECTS = ("answer", "refuse", "uncertain", "abstain")
SOURCE_FIELDS = ("event_id", "seq", "actor_id", "occurred_at", "received_at", "effective_at",
                 "audience", "source_id", "source_revision", "channel", "content")
POLICY_FIELDS = ("policy_id", "seq", "issuer", "effective_at", "op", "subject", "object")
CHECKPOINT_FIELDS = ("checkpoint_id", "seq", "principal", "task", "requested_time", "budget")

PKG_DIR = os.path.dirname(os.path.abspath(__file__))
WORLDS_DIR = os.path.join(PKG_DIR, "worlds")
ORACLES_DIR = os.path.join(PKG_DIR, "oracles")

UTC = timezone.utc
NEG_INF = datetime.min.replace(tzinfo=UTC)
POS_INF = datetime.max.replace(tzinfo=UTC)


class SchemaError(ValueError):
    pass


def parse_time(value, default=None) -> datetime:
    """ISO-8601 -> aware datetime. Naive values are UTC. ``None`` -> ``default``."""
    if value is None or value == "":
        if default is None:
            raise SchemaError("missing time")
        return default
    if isinstance(value, datetime):
        dt = value
    else:
        s = str(value).strip()
        if s.endswith("Z") or s.endswith("z"):
            s = s[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(s)
        except ValueError as e:
            raise SchemaError(f"bad time {value!r}") from e
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def file_sha256(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


@dataclass
class World:
    world_id: str
    raw: dict
    path: str = ""
    sha256: str = ""

    @property
    def timeline(self) -> list[dict]:
        return self.raw.get("timeline", [])

    @property
    def sources(self) -> list[dict]:
        return [i for i in self.timeline if i.get("type") == "source"]

    @property
    def policies(self) -> list[dict]:
        return [i for i in self.timeline if i.get("type") == "policy"]

    @property
    def checkpoints(self) -> list[dict]:
        return [i for i in self.timeline if i.get("type") == "checkpoint"]

    @property
    def family(self):
        return self.raw.get("family")

    def source_by_id(self) -> dict[str, dict]:
        return {s["event_id"]: s for s in self.sources}

    def checkpoint_by_id(self) -> dict[str, dict]:
        return {c["checkpoint_id"]: c for c in self.checkpoints}

    def manifest(self) -> dict:
        """What a system may see up front: everything except the timeline."""
        return json.loads(json.dumps({k: v for k, v in self.raw.items() if k != "timeline"}))


@dataclass
class OracleEntry:
    checkpoint_id: str
    stratum: str
    expect: str
    required: list[list[str]] = field(default_factory=list)
    forbidden: list[str] = field(default_factory=list)
    protected: list[str] = field(default_factory=list)
    evidence: list[list[str]] = field(default_factory=list)
    notes: str = ""
    raw: dict = field(default_factory=dict)

    @property
    def evidence_ids(self) -> set[str]:
        return {e for alt in self.evidence for e in alt}


@dataclass
class Oracle:
    world_id: str
    checker_version: str
    checkpoints: dict[str, OracleEntry]
    path: str = ""
    sha256: str = ""


def load_world(path: str) -> World:
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, dict) or "world_id" not in raw:
        raise SchemaError(f"{path}: not a world file (no world_id)")
    return World(world_id=raw["world_id"], raw=raw, path=path, sha256=file_sha256(path))


def _str_list(v) -> list[str]:
    if v is None:
        return []
    if isinstance(v, str):
        return [v]
    return [str(x) for x in v]


def _alt_lists(v) -> list[list[str]]:
    """``[["a","b"], "c"]`` -> ``[["a","b"], ["c"]]``."""
    out = []
    for g in v or []:
        out.append(_str_list(g))
    return out


def load_oracle(path: str) -> Oracle:
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    cps = {}
    for cid, e in (raw.get("checkpoints") or {}).items():
        cps[cid] = OracleEntry(
            checkpoint_id=cid, stratum=e.get("stratum", ""), expect=e.get("expect", ""),
            required=_alt_lists(e.get("required")), forbidden=_str_list(e.get("forbidden")),
            protected=_str_list(e.get("protected")), evidence=_alt_lists(e.get("evidence")),
            notes=e.get("notes", "") or "", raw=e)
    return Oracle(world_id=raw.get("world_id", ""), checker_version=str(raw.get("checker_version", "")),
                  checkpoints=cps, path=path, sha256=file_sha256(path))


def find_world_paths(selection: str = "all", worlds_dir: str = WORLDS_DIR) -> list[str]:
    """``all`` or a comma list of world ids / file stems."""
    paths = sorted(glob.glob(os.path.join(worlds_dir, "*.json")))
    if selection in (None, "", "all"):
        return paths
    wanted = [s.strip() for s in selection.split(",") if s.strip()]
    by_key = {}
    for p in paths:
        stem = os.path.splitext(os.path.basename(p))[0]
        by_key[stem] = p
        try:
            with open(p, encoding="utf-8") as f:
                by_key[json.load(f).get("world_id", stem)] = p
        except Exception:
            pass
    out = []
    for w in wanted:
        if w not in by_key:
            raise SchemaError(f"world {w!r} not found in {worlds_dir}")
        out.append(by_key[w])
    return out


def oracle_path_for(world: World, oracles_dir: str = ORACLES_DIR) -> str:
    stem = os.path.splitext(os.path.basename(world.path))[0] if world.path else world.world_id
    for cand in (os.path.join(oracles_dir, stem + ".json"), os.path.join(oracles_dir, world.world_id + ".json")):
        if os.path.exists(cand):
            return cand
    return os.path.join(oracles_dir, world.world_id + ".json")


# ---------------------------------------------------------------- validation

def validate_world(world: World) -> tuple[list[str], list[str]]:
    """Return (errors, warnings). Errors make the world unrunnable."""
    E, W = [], []
    r = world.raw
    wid = world.world_id
    for k in ("organizations", "principals", "scopes", "timeline"):
        if not isinstance(r.get(k), list):
            E.append(f"{wid}: missing list '{k}'")
    if E:
        return E, W

    def uniq(items, key, what):
        ids = set()
        for it in items:
            v = it.get(key)
            if not v:
                E.append(f"{wid}: {what} without '{key}'")
            elif v in ids:
                E.append(f"{wid}: duplicate {what} id {v!r}")
            ids.add(v)
        return ids

    orgs = uniq(r["organizations"], "id", "organization")
    principals = uniq(r["principals"], "id", "principal")
    scopes = uniq(r["scopes"], "id", "scope")
    for p in r["principals"]:
        if p.get("org") not in orgs:
            E.append(f"{wid}: principal {p.get('id')!r} has unknown org {p.get('org')!r}")
    for s in r["scopes"]:
        if s.get("kind") not in SCOPE_KINDS:
            E.append(f"{wid}: scope {s.get('id')!r} has bad kind {s.get('kind')!r}")
        if s.get("org") is not None and s.get("org") not in orgs:
            E.append(f"{wid}: scope {s.get('id')!r} has unknown org {s.get('org')!r}")
        if s.get("kind") == "individual" and s.get("owner") not in principals:
            E.append(f"{wid}: individual scope {s.get('id')!r} has unknown owner {s.get('owner')!r}")
    for m in r.get("memberships") or []:
        who = m.get("principal") or m.get("subject")
        if who not in principals:
            E.append(f"{wid}: membership for unknown principal {who!r}")
        if m.get("scope") not in scopes:
            E.append(f"{wid}: membership in unknown scope {m.get('scope')!r}")

    def check_time(item, key, label, optional=False):
        v = item.get(key)
        if v in (None, ""):
            if not optional:
                E.append(f"{wid}: {label} missing '{key}'")
            return
        try:
            parse_time(v)
        except SchemaError:
            E.append(f"{wid}: {label} bad time {key}={v!r}")

    last_seq = None
    event_ids, policy_ids, cp_ids = set(), set(), set()
    for idx, it in enumerate(r["timeline"]):
        t = it.get("type")
        seq = it.get("seq")
        label = f"timeline[{idx}]"
        if t not in ITEM_TYPES:
            E.append(f"{wid}: {label} bad type {t!r}")
            continue
        if not isinstance(seq, int) or isinstance(seq, bool):
            E.append(f"{wid}: {label} seq is not an integer: {seq!r}")
        else:
            if last_seq is not None and seq <= last_seq:
                E.append(f"{wid}: {label} seq {seq} does not increase (previous {last_seq})")
            last_seq = seq
        if t == "source":
            label = f"source {it.get('event_id')!r}"
            for k in SOURCE_FIELDS:
                if k not in it:
                    E.append(f"{wid}: {label} missing '{k}'")
            eid = it.get("event_id")
            if eid in event_ids:
                E.append(f"{wid}: duplicate event_id {eid!r}")
            event_ids.add(eid)
            if it.get("channel") not in CHANNELS:
                E.append(f"{wid}: {label} bad channel {it.get('channel')!r}")
            if it.get("actor_id") not in principals:
                if it.get("channel") == "untrusted":
                    W.append(f"{wid}: {label} untrusted actor {it.get('actor_id')!r} is not a declared principal")
                else:
                    E.append(f"{wid}: {label} unknown actor {it.get('actor_id')!r}")
            aud = it.get("audience")
            if not isinstance(aud, list) or not aud:
                E.append(f"{wid}: {label} audience must be a non-empty list of scope ids")
            else:
                for a in aud:
                    if a not in scopes:
                        E.append(f"{wid}: {label} audience has unknown scope {a!r}")
            for k in ("occurred_at", "received_at", "effective_at"):
                check_time(it, k, label)
            if not isinstance(it.get("content"), str) or not it.get("content"):
                E.append(f"{wid}: {label} empty content")
        elif t == "policy":
            label = f"policy {it.get('policy_id')!r}"
            for k in POLICY_FIELDS:
                if k not in it:
                    E.append(f"{wid}: {label} missing '{k}'")
            pid = it.get("policy_id")
            if pid in policy_ids:
                E.append(f"{wid}: duplicate policy_id {pid!r}")
            policy_ids.add(pid)
            op = it.get("op")
            if op not in POLICY_OPS:
                E.append(f"{wid}: {label} bad op {op!r}")
            subj = it.get("subject")
            if op in ("member_add", "member_remove"):
                if subj not in principals:
                    E.append(f"{wid}: {label} {op} subject {subj!r} is not a principal")
                obj_kind = next((s.get("kind") for s in r["scopes"] if s.get("id") == it.get("object")), None)
                if obj_kind in ("channel", "individual"):
                    W.append(f"{wid}: {label} {op} on {obj_kind} scope {it.get('object')!r} grants nothing (only grants open channels)")
            elif subj not in principals and subj not in scopes and subj not in orgs:
                E.append(f"{wid}: {label} subject {subj!r} is not a principal, scope or organization")
            if it.get("object") not in scopes:
                E.append(f"{wid}: {label} unknown object scope {it.get('object')!r}")
            iss = it.get("issuer")
            if iss not in principals and iss not in orgs and iss != "system":
                W.append(f"{wid}: {label} issuer {iss!r} is not a principal, organization or 'system'")
            perms = it.get("permissions")
            if perms is not None and (not isinstance(perms, list) or any(p not in PERMISSIONS for p in perms)):
                E.append(f"{wid}: {label} bad permissions {perms!r}")
            if op == "grant" and not perms:
                E.append(f"{wid}: {label} grant without permissions")
            check_time(it, "effective_at", label)
            check_time(it, "expires_at", label, optional=True)
        else:
            label = f"checkpoint {it.get('checkpoint_id')!r}"
            for k in CHECKPOINT_FIELDS:
                if k not in it:
                    E.append(f"{wid}: {label} missing '{k}'")
            cid = it.get("checkpoint_id")
            if cid in cp_ids:
                E.append(f"{wid}: duplicate checkpoint_id {cid!r}")
            cp_ids.add(cid)
            if it.get("principal") not in principals:
                E.append(f"{wid}: {label} unknown principal {it.get('principal')!r}")
            if not isinstance(it.get("task"), str) or not it.get("task").strip():
                E.append(f"{wid}: {label} empty task")
            check_time(it, "requested_time", label)
            b = it.get("budget")
            if not isinstance(b, dict) or not isinstance(b.get("context_tokens"), int) or b.get("context_tokens") <= 0:
                E.append(f"{wid}: {label} budget.context_tokens must be a positive integer")
    if not cp_ids:
        W.append(f"{wid}: no checkpoints")
    return E, W


def check_oracle(world: World, oracle_path: str) -> tuple[list[str], list[str]]:
    """Validate the oracle against its world. Returns only messages, never oracle content."""
    from .policy import Policy  # local import: policy depends on schema

    E, W = [], []
    wid = world.world_id
    if not os.path.exists(oracle_path):
        return [f"{wid}: oracle file missing ({os.path.basename(oracle_path)})"], W
    try:
        orc = load_oracle(oracle_path)
    except Exception as e:  # noqa: BLE001
        return [f"{wid}: oracle unreadable: {type(e).__name__}"], W
    if orc.world_id != wid:
        E.append(f"{wid}: oracle world_id mismatch ({orc.world_id!r})")
    cps = world.checkpoint_by_id()
    srcs = world.source_by_id()
    for cid in cps:
        if cid not in orc.checkpoints:
            E.append(f"{wid}: checkpoint {cid!r} has no oracle entry")
    for cid, e in orc.checkpoints.items():
        if cid not in cps:
            E.append(f"{wid}: oracle entry {cid!r} has no checkpoint")
            continue
        if e.stratum not in STRATA:
            E.append(f"{wid}: oracle {cid!r} bad stratum")
        if e.expect not in EXPECTS:
            E.append(f"{wid}: oracle {cid!r} bad expect")
        for g in e.required:
            if not g or any(not s.strip() for s in g):
                E.append(f"{wid}: oracle {cid!r} has an empty required alternative")
        if any(not s.strip() for s in e.forbidden + e.protected):
            E.append(f"{wid}: oracle {cid!r} has an empty forbidden/protected string")
        cp = cps[cid]
        for eid in e.evidence_ids:
            if eid not in srcs:
                E.append(f"{wid}: oracle {cid!r} evidence {eid!r} is not a source event")
            elif srcs[eid]["seq"] >= cp["seq"]:
                E.append(f"{wid}: oracle {cid!r} evidence {eid!r} is delivered after the checkpoint")
        if e.evidence_ids and not any(x not in srcs for x in e.evidence_ids):
            pol = Policy.replay(world.raw, upto_seq=cp["seq"])
            at = parse_time(cp["requested_time"])
            readable = [x for x in e.evidence_ids
                        if pol.can_read(cp["principal"], srcs[x], at, cp.get("purpose"))]
            if not readable:
                E.append(f"{wid}: oracle {cid!r} no evidence alternative is readable by the principal (unpassable)")
            elif len(readable) < len(e.evidence_ids):
                W.append(f"{wid}: oracle {cid!r} some evidence alternatives are not readable by the principal")
        if e.protected:
            corpus = " ".join(s["content"] for s in srcs.values() if s["seq"] < cp["seq"]).casefold()
            if not any(p.casefold() in corpus for p in e.protected):
                W.append(f"{wid}: oracle {cid!r} no protected string occurs in prior sources (vacuous check)")
    return E, W
