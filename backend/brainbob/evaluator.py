"""Evaluator ("change, then look"): task-agnostic evidence + verdicts over a MemoryStore.
Never sees gold answers: only task.grade(answer) -> bool.
answer_fn(question, memories) -> (text, cited_ids) or Answer."""
import random, zlib
from collections import defaultdict
from . import events
from .types import Decision, Evidence


def _call(answer_fn, q, mems):
    r = answer_fn(q, mems)
    return (r.text, r.cited_ids) if hasattr(r, "cited_ids") else r


class Probe:
    """Collects the evaluation.* events of one observe() call. Strategies take it as an optional 4th argument."""
    def __init__(self, task_id=None):
        self.task_id, self.began, self.checked, self.flips = task_id, False, 0, 0

    def started(self, memory_ids):
        self.began = True
        events.emit("evaluation.started", task_id=self.task_id, memory_ids=list(memory_ids))

    def check(self, memory_id, with_correct, without_correct):
        flipped = with_correct != without_correct
        self.checked += 1; self.flips += flipped
        events.emit("memory.checked", task_id=self.task_id, memory_id=memory_id,
                    with_correct=with_correct, without_correct=without_correct, flipped=flipped)


def leave_one_out(task, memories, answer_fn, probe=None):
    """Answer with everything, then once per cited memory with it removed. Evidence only on a correctness flip.
    Events: evaluation.started (the cited memories), memory.checked per cited memory (flip or not)."""
    probe = probe or Probe(task.id)
    ans, cited = _call(answer_fn, task.question, memories)
    ok_full = bool(task.grade(ans)); ids = {m.id for m in memories}; out = []
    todo = [c for c in dict.fromkeys(cited) if c in ids]
    probe.started(todo)
    for cid in todo:
        ans2, _ = _call(answer_fn, task.question, [m for m in memories if m.id != cid])
        ok2 = bool(task.grade(ans2))
        probe.check(cid, ok_full, ok2)
        if ok2 != ok_full:
            out += [Evidence(cid, True, ok_full, task.id), Evidence(cid, False, ok2, task.id)]
    return out


def sample_pct(p, seed=42, base=leave_one_out):
    def strat(task, memories, answer_fn, probe=None):
        # skipped tasks are not evaluated at all, so they emit no evaluation.* events
        return [] if zlib.crc32(f"{seed}:{task.id}".encode()) % 100 >= p else base(task, memories, answer_fn, probe)
    return strat


def random_half_hide(seed=42):
    rng = random.Random(seed)
    def strat(task, memories, answer_fn, probe=None):
        # No paired re-answer here (one answer with a random half hidden), so there is no per-memory
        # with/without comparison: only started and finished are emitted, never memory.checked.
        probe = probe or Probe(task.id)
        trial = [m for m in memories if m.status == "trial"]
        hidden = {m.id for m in rng.sample(trial, len(trial) // 2)}
        probe.started([m.id for m in trial])
        ans, _ = _call(answer_fn, task.question, [m for m in memories if m.id not in hidden])
        ok = bool(task.grade(ans))
        return [Evidence(m.id, m.id not in hidden, ok, task.id) for m in trial]
    return strat


class Evaluator:
    def __init__(self, store, strategy=leave_one_out, min_changes=3, ab_min_n=30, ab_margin=0.1):
        self.store, self.strategy = store, strategy
        self.min_changes, self.ab_min_n, self.ab_margin = min_changes, ab_min_n, ab_margin
        self.evidence, self.decisions = [], []

    def observe(self, task, memories, answer_fn):
        probe = Probe(task.id)
        ev = self.strategy(task, memories, answer_fn, probe)
        for e in ev:
            self.evidence.append(e)
            events.emit("evidence.recorded", memory_id=e.memory_id, author=self.store.get(e.memory_id).author,
                        shown=e.shown, correct=e.correct, task_id=e.task_id)
        if probe.began:
            events.emit("evaluation.finished", task_id=task.id, checked=probe.checked, flips=probe.flips)
        return ev

    def stats(self, mid):
        per_q = defaultdict(dict); acc = {True: [0, 0], False: [0, 0]}
        for e in self.evidence:
            if e.memory_id != mid: continue
            per_q[e.task_id][e.shown] = e.correct
            acc[e.shown][1] += 1; acc[e.shown][0] += e.correct
        flips = {q: d for q, d in per_q.items() if True in d and False in d and d[True] != d[False]}
        return {"helped": [q for q, d in flips.items() if d[True]], "harmed": [q for q, d in flips.items() if not d[True]], "acc": acc}

    def _verdict(self, mid):
        s = self.stats(mid); h, b = len(s["helped"]), len(s["harmed"])
        if h + b >= self.min_changes:
            if b > h: return "harmful", s["harmed"]
            if h > b: return "helpful", s["helped"]
        (cs, ns), (ch, nh) = s["acc"][True], s["acc"][False]
        if ns >= self.ab_min_n and nh >= self.ab_min_n:
            d = cs / ns - ch / nh
            if d <= -self.ab_margin: return "harmful", []
            if d >= self.ab_margin: return "helpful", []
        return None, []

    def review(self, confirm_fn):
        """confirm_fn(memory_id) -> True if a fresh delete-and-rerun still shows it harmful."""
        out = []
        for mid in sorted({e.memory_id for e in self.evidence}):
            m = self.store.get(mid)
            if m.status in ("retired", "promoted"): continue
            v, qids = self._verdict(mid)
            if v == "helpful" and m.status == "trial":
                r = f"helpful on {qids}"; self.store.set_status(mid, "promoted", r)
                d = Decision(mid, "promote", r, qids); events.emit("memory.promoted", memory_id=mid, reason=r)
            elif v == "harmful" and m.status == "locked":
                if m.flagged: continue
                r = f"locked but harmful on {qids}"; self.store.flag(mid, r)
                d = Decision(mid, "flag", r, qids); events.emit("memory.flagged", memory_id=mid, reason=r)
            elif v == "harmful" and m.status != "locked":
                if not confirm_fn(mid):  # stays in trial; say so with a memory.checked carrying reason "confirm failed"
                    events.emit("memory.checked", task_id=qids[-1] if qids else None, memory_id=mid, with_correct=False,
                                without_correct=False, flipped=False, reason="confirm failed")
                    continue
                r = f"harmful on {qids}"; self.store.set_status(mid, "retired", r)
                d = Decision(mid, "retire", r, qids)
                events.emit("memory.retired", memory_id=mid, reason=r, task_ids=qids, confirmed=True)
            else:
                continue
            out.append(d); self.decisions.append(d)
        return out

    def report(self):
        authors = defaultdict(lambda: {"written": 0, "promoted": 0, "retired": 0, "flagged": 0, "helped": 0, "harmed": 0})
        for m in self.store.all():
            a = authors[m.author]; a["written"] += 1; a["promoted"] += m.status == "promoted"
            a["retired"] += m.status == "retired"; a["flagged"] += m.flagged
            st = self.stats(m.id); a["helped"] += len(st["helped"]); a["harmed"] += len(st["harmed"])
        return {"authors": dict(authors),
                "retired": [{"memory_id": m.id, "text": m.text, "author": m.author, "origin": m.origin, "reason": m.reason,
                             "task_ids": self.stats(m.id)["harmed"]} for m in self.store.all() if m.status == "retired"],
                "flagged": [{"memory_id": m.id, "text": m.text, "reason": m.reason} for m in self.store.all() if m.flagged]}
