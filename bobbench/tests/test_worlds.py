"""Structural checks for the pilot worlds and their hidden oracles.

Standard library + json only. Deliberately does not import any other bobbench module:
it re-implements the CONTRACT.md readability rules in a few lines so the data can be
checked independently of the reference policy engine.
"""
import json
import re
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORLD_DIR = ROOT / "worlds"
ORACLE_DIR = ROOT / "oracles"
WORLD_FILES = sorted(WORLD_DIR.glob("*.json"))

STRATA = {"legitimate", "boundary", "maintenance"}
EXPECTS = {"answer", "refuse", "uncertain", "abstain"}
OPS = {"member_add", "member_remove", "grant", "revoke", "approver"}
PERMS = {"read", "write", "approve", "publish"}
SOURCE_FIELDS = ("event_id", "seq", "actor_id", "occurred_at", "received_at", "effective_at",
                 "audience", "source_id", "source_revision", "channel", "content")
POLICY_FIELDS = ("policy_id", "seq", "issuer", "effective_at", "op", "subject", "object",
                 "permissions", "expires_at", "purpose")
CHECKPOINT_FIELDS = ("checkpoint_id", "seq", "principal", "task", "requested_time", "purpose", "budget")
ORACLE_KEYS = ("stratum", "expect", "required", "forbidden", "protected", "evidence", "notes")


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def norm(s):
    return re.sub(r"\s+", " ", s).strip().lower()


def ts(s):
    return datetime.fromisoformat(s)


def world_and_oracle(path):
    world = load(path)
    oracle = load(ORACLE_DIR / path.name)
    return world, oracle


def items(world, kind):
    return [i for i in world["timeline"] if i["type"] == kind]


def readable_scopes(world, principal, at, purpose, before_seq):
    """CONTRACT.md rules: org/team membership reads that scope; individual scope by owner;
    channels and cross-scope access only through unexpired, purpose-matching read grants."""
    scopes = {s["id"]: s for s in world["scopes"]}
    member = {}
    grants = []
    for p in items(world, "policy"):
        if p["seq"] >= before_seq or p["subject"] != principal or ts(p["effective_at"]) > at:
            continue
        if p["op"] == "member_add":
            member[p["object"]] = True
        elif p["op"] == "member_remove":
            member[p["object"]] = False
        elif p["op"] == "grant":
            grants.append(dict(p))
        elif p["op"] == "revoke":
            drop = set(p.get("permissions") or PERMS)
            for g in grants:
                if g["object"] == p["object"]:
                    g["permissions"] = [x for x in g["permissions"] if x not in drop]
    out = {sid for sid, on in member.items() if on and scopes[sid]["kind"] in ("organization", "team")}
    out |= {sid for sid, s in scopes.items() if s["kind"] == "individual" and s.get("owner") == principal}
    for g in grants:
        if "read" not in g["permissions"]:
            continue
        if g.get("expires_at") and at >= ts(g["expires_at"]):
            continue
        if g.get("purpose") and g["purpose"] != purpose:
            continue
        out.add(g["object"])
    return out


def split_sources(world, cp):
    """(readable, unreadable) prior sources for a checkpoint's principal at its requested time."""
    at = ts(cp["requested_time"])
    rs = readable_scopes(world, cp["principal"], at, cp.get("purpose"), cp["seq"])
    prior = [s for s in items(world, "source") if s["seq"] < cp["seq"]]
    readable = [s for s in prior if set(s["audience"]) & rs]
    unreadable = [s for s in prior if not set(s["audience"]) & rs]
    return readable, unreadable


def text_of(sources):
    return " || ".join(norm(s["content"]) for s in sources)


params = pytest.mark.parametrize("path", WORLD_FILES, ids=[p.stem for p in WORLD_FILES])


def test_six_worlds_present():
    assert len(WORLD_FILES) == 6
    for p in WORLD_FILES:
        assert (ORACLE_DIR / p.name).exists(), f"missing oracle for {p.name}"


@params
def test_manifest_and_fields(path):
    world, oracle = world_and_oracle(path)
    for k in ("world_id", "version", "domain", "family", "split", "organizations", "principals", "scopes", "timeline"):
        assert k in world, k
    assert world["split"] in ("public-dev", "pilot")
    assert oracle["world_id"] == world["world_id"]
    assert path.stem == world["world_id"]
    fields = {"source": SOURCE_FIELDS, "policy": POLICY_FIELDS, "checkpoint": CHECKPOINT_FIELDS}
    for it in world["timeline"]:
        assert it["type"] in fields, it
        for f in fields[it["type"]]:
            assert f in it, (it.get("event_id") or it.get("policy_id") or it.get("checkpoint_id"), f)
    for s in items(world, "source"):
        assert s["channel"] in ("trusted", "untrusted")
        assert s["content"].strip()
        assert ts(s["occurred_at"]) <= ts(s["received_at"])
    for p in items(world, "policy"):
        assert p["op"] in OPS
        assert set(p["permissions"] or []) <= PERMS
        if p["op"] == "grant":
            assert p["permissions"], p["policy_id"]
    for c in items(world, "checkpoint"):
        assert c["budget"]["context_tokens"] > 0


@params
def test_seq_strictly_increasing_and_ids_unique(path):
    world, _ = world_and_oracle(path)
    seqs = [i["seq"] for i in world["timeline"]]
    assert all(isinstance(s, int) for s in seqs)
    assert all(a < b for a, b in zip(seqs, seqs[1:])), "seq must strictly increase"
    ids = [i.get("event_id") or i.get("policy_id") or i.get("checkpoint_id") for i in world["timeline"]]
    assert len(ids) == len(set(ids))
    # received_at follows delivery order (late messages keep an early occurred_at)
    rec = [ts(s["received_at"]) for s in items(world, "source")]
    assert all(a <= b for a, b in zip(rec, rec[1:]))


@params
def test_size_targets(path):
    world, _ = world_and_oracle(path)
    assert 15 <= len(world["timeline"]) <= 40
    assert 4 <= len(items(world, "checkpoint")) <= 8


@params
def test_references_exist(path):
    world, _ = world_and_oracle(path)
    orgs = {o["id"] for o in world["organizations"]}
    principals = {p["id"] for p in world["principals"]}
    scopes = {s["id"] for s in world["scopes"]}
    for p in world["principals"]:
        assert p["org"] in orgs
    for s in world["scopes"]:
        assert s["kind"] in ("organization", "team", "individual", "channel")
        assert s["org"] is None or s["org"] in orgs
        if s["kind"] == "individual":
            assert s["owner"] in principals
        if s["kind"] == "channel":
            assert s["org"] is None
    for s in items(world, "source"):
        assert s["actor_id"] in principals, s["event_id"]
        assert s["audience"] and set(s["audience"]) <= scopes, s["event_id"]
    for p in items(world, "policy"):
        assert p["subject"] in principals, p["policy_id"]
        assert p["object"] in scopes, p["policy_id"]
        assert p["issuer"] in orgs, p["policy_id"]
    for c in items(world, "checkpoint"):
        assert c["principal"] in principals, c["checkpoint_id"]


@params
def test_authors_could_post_where_they_posted(path):
    """Every source author could read each scope in its audience at the time (no impossible posts)."""
    world, _ = world_and_oracle(path)
    for s in items(world, "source"):
        rs = readable_scopes(world, s["actor_id"], ts(s["received_at"]), None, s["seq"])
        assert set(s["audience"]) <= rs, s["event_id"]


@params
def test_checkpoints_match_oracle(path):
    world, oracle = world_and_oracle(path)
    cps = {c["checkpoint_id"] for c in items(world, "checkpoint")}
    assert cps == set(oracle["checkpoints"])
    for cid, o in oracle["checkpoints"].items():
        for k in ORACLE_KEYS:
            assert k in o, (cid, k)
        assert o["stratum"] in STRATA, cid
        assert o["expect"] in EXPECTS, cid
        assert o["notes"].strip(), cid
        assert all(isinstance(g, list) and g and all(a.strip() for a in g) for g in o["required"]), cid


@params
def test_world_file_carries_no_labels(path):
    world, _ = world_and_oracle(path)
    raw = path.read_text(encoding="utf-8")
    for k in ("stratum", "expect", "required", "forbidden", "protected", "evidence", "notes", "pairs"):
        assert f'"{k}"' not in raw, k


@params
def test_evidence_resolves_and_is_readable(path):
    world, oracle = world_and_oracle(path)
    cps = {c["checkpoint_id"]: c for c in items(world, "checkpoint")}
    srcs = {s["event_id"]: s for s in items(world, "source")}
    for cid, o in oracle["checkpoints"].items():
        cp = cps[cid]
        ids = [e for alt in o["evidence"] for e in alt]
        if o["expect"] in ("answer", "uncertain"):
            assert ids, f"{cid}: answer/uncertain needs evidence"
        else:
            assert not o["required"], f"{cid}: refuse/abstain should not require claims"
        rs = readable_scopes(world, cp["principal"], ts(cp["requested_time"]), cp.get("purpose"), cp["seq"])
        for e in ids:
            assert e in srcs, f"{cid}: unknown evidence {e}"
            assert srcs[e]["seq"] < cp["seq"], f"{cid}: evidence {e} is from the future"
            assert set(srcs[e]["audience"]) & rs, f"{cid}: evidence {e} not readable by {cp['principal']}"


@params
def test_protected_only_in_unreadable_sources(path):
    world, oracle = world_and_oracle(path)
    cps = {c["checkpoint_id"]: c for c in items(world, "checkpoint")}
    for cid, o in oracle["checkpoints"].items():
        if not o["protected"]:
            continue
        cp = cps[cid]
        readable, unreadable = split_sources(world, cp)
        rtext, utext = text_of(readable), text_of(unreadable)
        for p in o["protected"]:
            n = norm(p)
            assert n not in rtext, f"{cid}: protected {p!r} appears in a source readable by {cp['principal']}"
            assert n not in norm(cp["task"]), f"{cid}: protected {p!r} appears in the task text"
        assert any(norm(p) in utext for p in o["protected"]), f"{cid}: no protected string occurs in any unreadable source"


@params
def test_required_claims_derivable_from_readable_sources(path):
    world, oracle = world_and_oracle(path)
    cps = {c["checkpoint_id"]: c for c in items(world, "checkpoint")}
    for cid, o in oracle["checkpoints"].items():
        readable, _ = split_sources(world, cps[cid])
        rtext = text_of(readable)
        for group in o["required"]:
            assert any(norm(a) in rtext for a in group), f"{cid}: required {group} not in any readable source"


@params
def test_claim_sets_do_not_contradict(path):
    _, oracle = world_and_oracle(path)
    for cid, o in oracle["checkpoints"].items():
        alts = [norm(a) for g in o["required"] for a in g]
        for bad in o["forbidden"] + o["protected"]:
            b = norm(bad)
            for a in alts:
                assert b not in a, f"{cid}: {bad!r} would block required alternative {a!r}"
        # each required group must be satisfiable without tripping a forbidden or protected string
        for g in o["required"]:
            assert any(not any(norm(b) in norm(a) for b in o["forbidden"] + o["protected"]) for a in g), cid


@params
def test_strata_and_counterfactual_pairs(path):
    world, oracle = world_and_oracle(path)
    cps = {c["checkpoint_id"]: c for c in items(world, "checkpoint")}
    entries = oracle["checkpoints"]
    assert {o["stratum"] for o in entries.values()} == STRATA
    pairs = oracle.get("pairs", [])
    cf = [p for p in pairs if p["type"] == "counterfactual"]
    assert cf, "each world needs at least one counterfactual pair"
    for p in pairs:
        a, b = p["checkpoints"]
        assert a in cps and b in cps and a != b
        assert p["deciding_condition"].strip()
        assert p["type"] in ("counterfactual", "allowed_match")
    for p in cf:
        a, b = p["checkpoints"]
        ca, cb = cps[a], cps[b]
        assert ca["task"] == cb["task"], f"{a}/{b}: counterfactual pair must ask the identical task"
        assert (ca["principal"], ca["seq"], ca.get("purpose")) != (cb["principal"], cb["seq"], cb.get("purpose"))
        oa, ob = entries[a], entries[b]
        changed = (oa["expect"] != ob["expect"]
                   or sorted(map(tuple, oa["required"])) != sorted(map(tuple, ob["required"])))
        assert changed, f"{a}/{b}: counterfactual outcome must change"
    # every boundary checkpoint is paired with a same-subject checkpoint that is answered
    for cid, o in entries.items():
        if o["stratum"] != "boundary":
            continue
        partners = [x for p in pairs if cid in p["checkpoints"] for x in p["checkpoints"] if x != cid]
        assert any(entries[x]["expect"] == "answer" for x in partners), f"{cid}: boundary case lacks an allowed pair"


def test_worlds_are_structurally_distinct():
    """w2-w6 are not renamed copies of w1: different organizations, scope sets and vocabulary."""
    worlds = [load(p) for p in WORLD_FILES]
    org_sets = [frozenset(o["id"] for o in w["organizations"]) for w in worlds]
    assert len(set(org_sets)) == len(worlds)
    shapes = set()
    for w in worlds:
        kinds = tuple(sorted(s["kind"] for s in w["scopes"]))
        shapes.add((len(w["organizations"]), kinds, w["domain"]))
    assert len(shapes) == len(worlds)
    first = norm(" ".join(s["content"] for s in items(worlds[0], "source")))
    for w in worlds[1:]:
        assert "atlas" not in norm(" ".join(s["content"] for s in items(w, "source")))
        assert "rusty rod" not in norm(" ".join(s["content"] for s in items(w, "source")))
    assert "atlas" in first
