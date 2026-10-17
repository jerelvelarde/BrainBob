"""Rusty Rod correctness suite (SPEC-correctness.md): scenario loading, deterministic grading, end-of-scenario
state checks and audit gold. No model calls here; gold never leaves this module except through grade()."""
import json, os, re
from brainbob.types import Episode, Memory

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(ROOT, "fixtures", "rusty_rod")
SCENARIOS = os.path.join(FIX, "scenarios.json")
ORG_JSON = os.path.join(FIX, "org.json")
GROUPS = ["Extraction", "Updates", "Retention", "Forgetting", "Shared handoff", "Insufficient evidence"]
AUTHORITIES = ("approved", "tentative", "discussion")

ABSTAIN = ["i don t know", "i do not know", "don t know", "do not know", "not sure", "no information", "no record",
           "not mentioned", "not specified", "not stated", "not provided", "not available", "not in the memories",
           "no memories", "no memory", "cannot determine", "can t determine", "cannot find", "can t find", "unknown",
           "unclear", "not been decided", "hasn t been decided", "not yet decided", "no decision", "not confirmed",
           "unconfirmed", "doesn t say", "does not say", "no details", "not recorded", "not known", "no data",
           "not shared", "not yet shared", "hasn t shared", "has not shared", "haven t shared", "not been shared",
           "not disclosed", "no mention", "not been provided", "doesn t mention", "does not mention", "isn t mentioned",
           "not been mentioned", "no specific", "not given", "not indicated", "not documented"]
CONFLICT = ["conflict", "tentative", "unresolved", "not yet approved", "pending approval", "awaiting approval",
            "not been approved", "hasn t been approved", "not finalized", "not final", "disagree", "two different",
            "inconsistent", "contradict", "not confirmed", "unconfirmed", "still open", "not decided", "undecided"]


RETRACT = ["no longer", "replaced", "replaces", "cancel", "called off", "obsolete", "decommission", "retired", "retiring",
           "dropped", "deleted", "removed", "moved from", "changed from", "switched", "switching", "previously", "originally",
           "is out", "is off", "instead of", "has left", "left the"]


def load(path=SCENARIOS):
    return json.load(open(path, encoding="utf-8"))


def scenarios(split="heldout", fast=False, path=SCENARIOS):
    """Scenarios of one split in group order; fast keeps the first 2 of each group."""
    out = []
    for g in GROUPS:
        xs = [s for s in load(path)["scenarios"] if s["group"] == g and s["split"] == split]
        out += xs[:2] if fast else xs
    return out


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", str(s).lower())).strip()


def has(text, s):
    """Normalized phrase match: left word boundary; on the right only a digit blocks (nov 1 != nov 13, error ~ errors)."""
    n = norm(s)
    return bool(n) and re.search(r"(?<![a-z0-9])" + re.escape(n) + r"(?![0-9])", norm(text)) is not None


def any_has(text, variants): return any(has(text, v) for v in variants)


def grade(q, text):
    """-> dict(correct, stale, kind). Deterministic; see results.md for the rules."""
    exp, forbid = q["expect"], q.get("forbid", [])
    stale = any_has(text, forbid)
    if exp == "abstain":
        kind, ok = "abstain", any_has(text, ABSTAIN) and not stale
    elif exp == "uncertain":
        kind = "uncertain"
        ok = all(any_has(text, g) for g in q["values"]) or any_has(text, CONFLICT)
    else:
        kind, ok = "fact", any_has(text, exp)
    return dict(correct=bool(ok), stale=bool(stale), kind=kind)


def episodes(sc):
    out = []
    for i, e in enumerate(sc["episodes"], 1):
        ep = Episode(f"{sc['id']}-e{i}", e["text"], e["date"], "rusty_rod")
        ep.author, ep.scope, ep.authority = e["author"], e["scope"], e["authority"]  # works with old or new Episode
        ep.decisive = bool(e.get("decisive"))
        out.append(ep)
    return out


def readable_episodes(sc, member, org):
    """Raw history for the full_history condition: every episode the member can read, oldest first."""
    eps = [e for e in episodes(sc) if org.can_read(member, e.scope)]
    return sorted(eps, key=lambda e: e.date)


def as_memories(eps):
    """Raw episodes in memory form so full_history uses the same answering prompt (no retrieval, no maintenance)."""
    out = []
    for e in eps:
        m = Memory(e.id, e.text, e.author, e.id, e.date, "trial", e.scope)
        m.authority = e.authority
        out.append(m)
    return out


def active(store): return [m for m in store.all() if m.status != "retired"]


def state_check(sc, store):
    """End-of-scenario store checks.
    updated: correct if an active non-tentative memory has a new value and no active memory states an old value
             without also stating a new one or a retraction word (RETRACT: "no longer", "cancelled", "replaced" ...). keep: forgotten if only retired memories carry it."""
    st, act = sc.get("state", {}), active(store)
    firm = [m for m in act if m.status != "tentative"]
    ups = []
    for u in st.get("updated", []):
        new_ok = any(any_has(m.text, u["new"]) for m in firm)
        old_left = [m.id for m in act if any_has(m.text, u["old"]) and not any_has(m.text, u["new"] + RETRACT)]
        ups.append(dict(new=u["new"][0], old=u["old"][0], correct=new_ok and not old_left, new_present=new_ok, old_active=old_left))
    keeps = []
    for k in st.get("keep", []):
        live = any(any_has(m.text, k) for m in act)
        dead = [m.id for m in store.all() if m.status == "retired" and any_has(m.text, k)]
        keeps.append(dict(value=k[0], active=live, forgotten=bool(dead) and not live, retired_ids=dead))
    return dict(updates=ups, keeps=keeps)


def audit_gold(sc, mem, ep_id):
    """Expected verdict for one audit check, or None when the fixture does not decide it.
    Same source episode -> supported; a later decisive episode vs a memory still holding that update's old value
    -> contradicted; an episode that never mentions the memory's subject is scored only when the memory came from
    another scenario (-> insufficient)."""
    if not mem.origin.startswith(sc["id"] + "-e"): return "insufficient"
    if mem.origin == ep_id: return "supported"
    idx = int(ep_id.rsplit("-e", 1)[1]) - 1
    e = sc["episodes"][idx]
    if e.get("decisive"):
        for u in sc.get("state", {}).get("updated", []):
            if any_has(mem.text, u["old"]) and not any_has(mem.text, u["new"]) and any_has(e["text"], u["new"]):
                return "contradicted"
    return None


def decisive_ids(sc): return [f"{sc['id']}-e{i}" for i, e in enumerate(sc["episodes"], 1) if e.get("decisive")]
