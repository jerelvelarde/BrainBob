"""Write-time maintenance (SPEC-correctness.md): wraps curator.extract and decides, per candidate, whether it is a
duplicate, a stale value, an authorized correction, an unresolved conflict, or new. Deterministic rules after one
judge call per (candidate, existing memory) pair. Never deletes for missing evidence; when unsure it marks tentative.

ingest(episode, store, acl) -> list[Decision]
  acl: anything with can_read(member, scope) and can_approve(member, scope); None = everything readable, nobody approves.
"""
import contextvars, json, re
from dataclasses import asdict
from . import curator, events, llm
from .memory import _visible
from .types import Decision

VERDICTS = ("same", "conflict", "unrelated")
ACTIVE = ("trial", "promoted", "locked")  # comparable statuses: never retired, never tentative
TOP_K = 5
RANK = {"discussion": 0, "tentative": 1, "approved": 2}

PROMPT = ("You compare one EXISTING memory with one NEW candidate memory from a company's shared notes. Decide:\n"
          "- \"same\": the candidate states the same fact with the same value (it adds nothing materially new).\n"
          "- \"conflict\": same subject and attribute, but a different current value (e.g. a different date, number, owner or decision).\n"
          "- \"unrelated\": different subjects or attributes, or compatible information that can both be true. A statement explicitly "
          "about a past or original value (\"was originally\", \"previously\") is not a conflict.\n"
          'Reply with JSON only: {"verdict": "same|conflict|unrelated", "reason": "one sentence"}')


def parse_verdict(raw):
    """Verdict from judge text that may carry reasoning, <think> blocks or ```json fences. None if unparseable."""
    t = re.sub(r"<think>.*?</think>", " ", raw or "", flags=re.S)
    if "</think>" in t: t = t.split("</think>")[-1]
    t = re.sub(r"```[a-zA-Z]*", " ", t)
    dec, found = json.JSONDecoder(), None
    for i, ch in enumerate(t):
        if ch != "{": continue
        try: d, _ = dec.raw_decode(t[i:])
        except ValueError: continue
        if isinstance(d, dict) and "verdict" in d: found = d  # keep the last JSON object that has a verdict
    if found is not None:
        v = str(found.get("verdict", "")).strip().lower()
        return v if v in VERDICTS else None
    m = re.findall(r'"?verdict"?\s*[:=]\s*"?(same|conflict|unrelated)\b', t, re.I)
    return m[-1].lower() if m else None


# Observation only: a caller (bobbench's judge trace) may set a list here to receive each raw judge reply.
JUDGE_RAW = contextvars.ContextVar("maintain_judge_raw", default=None)


def judge_messages(candidate, memory):
    """The production judge prompt for one (candidate, existing memory) pair."""
    return [{"role": "system", "content": PROMPT},
            {"role": "user", "content": f"EXISTING memory ({memory.date}): {memory.text}\n\nNEW candidate ({candidate['date']}): {candidate['text']}"}]


def llm_judge(candidate, memory, role="judge"):
    """One judge call for one pair. Returns 'same' / 'conflict' / 'unrelated' or None (unparseable)."""
    raw = llm.complete(role, judge_messages(candidate, memory))
    sink = JUDGE_RAW.get()
    if sink is not None: sink.append(raw)
    return parse_verdict(raw)


def _date_key(s):
    m = re.search(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", s or "")
    return tuple(int(x) for x in m.groups()) if m else None


class _OpenACL:
    """No ACL given: everything readable, nobody can approve (so nothing is ever superseded)."""
    def can_read(self, member, scope): return True
    def can_approve(self, member, scope): return False


def _neighbors(store, text, author, origin, acl):
    """Active memories (not retired, not tentative) in scopes the author can read, BM25 top 5.
    Memories from the same episode are skipped: one source cannot correct itself."""
    pool = store.search(text, k=max(len(store.all()), 1), include_tentative=False)
    out = [m for m in pool if m.status in ACTIVE and m.origin != origin and acl.can_read(author, m.scope)]
    return out[:TOP_K]


def _covers(old, cand):
    """A 'same' old memory makes the candidate a duplicate only if it already reaches every reader of the candidate's
    scope (its scope is the candidate's scope or an ancestor) with at least the candidate's authority; otherwise
    dropping the candidate would lose a publication or an approval, so the pair counts as unrelated."""
    return _visible(old.scope, cand["scope"]) and RANK.get(old.authority, 0) >= RANK.get(cand["authority"], 0)


def _pair_action(cand, old, verdict, author, acl):
    """Rule table row for one conflicting pair: 'supersede' | 'stale' | 'tentative'."""
    if verdict is None: return "tentative"  # unparseable judge output: flag, never overwrite
    if cand["authority"] != "approved": return "tentative"
    cd, od = _date_key(cand["date"]), _date_key(old.date)
    if cd is not None and od is not None and cd < od: return "stale"
    if not acl.can_approve(author, old.scope): return "tentative"
    if not _visible(cand["scope"], old.scope): return "tentative"  # the correction must reach every reader of the old one
    if old.status == "locked": return "tentative"  # only its owner may retire a locked memory
    if cd is None or od is None: return "tentative"  # cannot show the candidate is newer
    return "supersede"


def ingest(episode, store, acl, role="curator", judge=None, judge_role="judge", judge_model=None):
    """Apply the SPEC rule table. Custom callbacks may supply model_id or judge_model
    for honest decision/event provenance; the production judge route is unchanged.
    """
    acl = acl or _OpenACL()
    if judge is None:
        jm = judge_model or curator.model_for(judge_role)
        judge = lambda cand, mem: llm_judge(cand, mem, judge_role)
    else:
        jm = judge_model or getattr(judge, "model_id", None) or "custom:unidentified"
    author = getattr(episode, "author", None)
    scope = getattr(episode, "scope", None) or "team"
    authority = getattr(episode, "authority", None) or "discussion"
    if authority == "approved" and not acl.can_approve(author, scope):
        authority = "tentative"  # an approval the author cannot give is only a proposal
    kw = {**curator.stamp(episode, role), "authority": authority, "scope": scope}
    who = author or role
    decisions, added = [], 0

    def add(text, **extra):
        m, why = store.add(text, author=who, origin=episode.id, date=episode.date, **kw, **extra)
        return m, why

    for text in curator.extract(episode, role):
        cand = {"text": text, "date": episode.date, "authority": authority, "scope": scope}
        verdicts = [(m, judge(cand, m)) for m in _neighbors(store, text, author, episode.id, acl)]
        same = [m for m, v in verdicts if v == "same" and _covers(m, cand)]
        if same:
            events.emit("memory.rejected", text=text, reason="duplicate", duplicate_of=same[0].id, model=jm)
            decisions.append(Decision(None, "reject", f"duplicate of {same[0].id}", text=text, related=[same[0].id], model=jm))
            continue
        conflicts = [(m, v) for m, v in verdicts if v not in ("unrelated", "same")]  # conflict, or unparseable (None)
        acts = [(m, _pair_action(cand, m, v, author, acl)) for m, v in conflicts]
        stale = [m for m, a in acts if a == "stale"]
        if stale:
            events.emit("memory.rejected", text=text, reason="stale", stale_vs=[m.id for m in stale], model=jm)
            decisions.append(Decision(None, "reject", f"stale: older than {', '.join(m.id for m in stale)}",
                                      text=text, related=[m.id for m in stale], model=jm))
            continue
        if acts and all(a == "supersede" for _, a in acts):
            olds = [m.id for m, _ in acts]
            m, why = add(text, supersedes=olds[0])
            if m is None:
                decisions.append(Decision(None, "reject", why, text=text, related=olds, model=jm)); continue
            store.supersede(m.id, olds, author=who, model=jm)
            added += 1
            decisions.append(Decision(m.id, "supersede", f"approved correction of {', '.join(olds)}", text=text, related=olds, model=jm))
            continue
        if acts:  # at least one pair cannot be overwritten: keep every old memory active, flag the candidate
            olds = [m.id for m, _ in acts]
            m, why = add(text, status="tentative", conflicts_with=olds)
            if m is None:
                decisions.append(Decision(None, "reject", why, text=text, related=olds, model=jm)); continue
            for (o, v), (_, a) in zip(conflicts, acts):
                events.emit("memory.conflict", new_id=m.id, old_id=o.id, model=jm,
                            reason="judge output unparseable" if v is None else f"conflict; candidate {authority}, {a}")
            added += 1
            decisions.append(Decision(m.id, "tentative", f"conflicts with {', '.join(olds)}", text=text, related=olds, model=jm))
            continue
        m, why = add(text)
        if m is None:
            decisions.append(Decision(None, "reject", why, text=text, model=jm)); continue
        added += 1
        decisions.append(Decision(m.id, "add", "unrelated to existing memories", text=text, model=jm))
    events.emit("episode.ingested", episode_id=episode.id, source=getattr(episode, "source", ""), n_memories=added,
                author=author, scope=scope, authority=authority)
    return decisions
