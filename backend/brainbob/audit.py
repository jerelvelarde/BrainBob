"""Recent-conversation audit: random sample of the latest episodes, judge related memories.
Correctness signal only (see SPEC-correctness.md); separate from the evaluator's leave-one-out usefulness signal."""
import json, random, re
from dataclasses import dataclass, field
from . import events, llm

VERDICTS = ("supported", "contradicted", "insufficient")
PROMPT = ("You audit one stored memory against one conversation. Decide if the conversation "
          "'supported' the memory, 'contradicted' it (same subject, different current value), or is "
          "'insufficient' (not mentioned or unclear). Not being mentioned is NEVER contradiction. "
          'Reply with JSON only: {"verdict": "supported|contradicted|insufficient", "reason": "one sentence"}.')


@dataclass
class AuditReport:
    seed: object
    eligible_ids: list
    sampled_ids: list
    checks: list = field(default_factory=list)  # {memory_id, episode_id, verdict, reason, model, proposed}
    counts: dict = field(default_factory=dict)

    def coverage(self, decisive_episode_ids):
        """Fraction of stale memories whose decisive episode was sampled. Accepts a list or {memory_id: episode_id}."""
        ids = list(decisive_episode_ids.values() if isinstance(decisive_episode_ids, dict) else decisive_episode_ids)
        if not ids: return 0.0
        s = set(self.sampled_ids)
        return sum(i in s for i in ids) / len(ids)

    def judgment_accuracy(self, expected):
        """expected: {(memory_id, episode_id): verdict}. Scored only on pairs whose episode was sampled and checked."""
        got = {(c["memory_id"], c["episode_id"]): c["verdict"] for c in self.checks}
        scored = [k for k in expected if k in got]
        if not scored: return None
        return sum(got[k] == expected[k] for k in scored) / len(scored)


def _judge(memory, episode):
    msg = [{"role": "system", "content": PROMPT},
           {"role": "user", "content": f"Memory ({memory.id}): {memory.text}\n\nConversation ({episode.id}, {episode.date}): {episode.text}"}]
    raw = llm.complete("judge", msg)
    try:
        m = re.search(r"\{.*\}", raw, re.S); d = json.loads(m.group(0))
        v = str(d.get("verdict", "")).strip().lower()
        return (v if v in VERDICTS else "insufficient"), str(d.get("reason", ""))
    except Exception:
        return "insufficient", "unparseable judge output"


def _default_propose(store, acl):
    def propose(memory, episode):
        try:
            from .maintain import ingest
        except ImportError:
            return None
        return ingest(episode, store, acl)
    return propose


def audit_recent(store, episodes, latest=50, sample=10, seed=0, acl=None, propose=None, k=5):
    eligible = sorted(episodes, key=lambda e: e.date)[-latest:]
    eligible_ids = [e.id for e in eligible]
    picked = random.Random(seed).sample(eligible, min(sample, len(eligible)))
    rep = AuditReport(seed, eligible_ids, [e.id for e in picked])
    propose = propose or _default_propose(store, acl)
    events.emit("audit.started", seed=seed, eligible_ids=eligible_ids, sampled_ids=rep.sampled_ids)
    n = dict(checked=0, contradicted=0, supported=0, insufficient=0)
    model = llm._roles()["judge"]["model"]
    for ep in picked:
        for mem in store.search(ep.text, k=k):
            if mem.status == "retired": continue
            verdict, reason = _judge(mem, ep)
            proposed = False
            if verdict == "contradicted" and getattr(ep, "authority", "discussion") == "approved":
                propose(mem, ep); proposed = True
            rep.checks.append(dict(memory_id=mem.id, episode_id=ep.id, verdict=verdict, reason=reason, model=model, proposed=proposed))
            n["checked"] += 1; n[verdict] += 1
            events.emit("audit.checked", memory_id=mem.id, episode_id=ep.id, verdict=verdict, model=model, reason=reason)
    rep.counts = n
    events.emit("audit.finished", **n)
    return rep
