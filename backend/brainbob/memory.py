"""Memory store: add / dedupe / tombstone / status / BM25 search / jsonl persistence. No LLM."""
import itertools, json, os, re, threading
from dataclasses import asdict, fields
from rank_bm25 import BM25Okapi
from . import events
from .types import Memory

STATUSES = ("trial", "promoted", "retired", "locked")


def _norm(t): return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", t.lower())).strip()
def _tok(t): return re.findall(r"\w+", t.lower())
_FIELDS = {f.name for f in fields(Memory)}


def _visible(scope, reader):
    """scope equals the reader path or is an ancestor of it, compared by '/' segments."""
    s, r = [x for x in scope.split("/") if x], [x for x in reader.split("/") if x]
    return r[:len(s)] == s


def _jac(a, b):
    a, b = set(_norm(a).split()), set(_norm(b).split())
    return 1.0 if not a and not b else len(a & b) / len(a | b)


class MemoryStore:
    def __init__(self, path=None, tombstone_jaccard=0.8):
        self.path, self.tj = path, tombstone_jaccard
        self._m, self._n, self._lock = {}, itertools.count(1), threading.RLock()
        self._bm, self._act = None, []
        if path and os.path.exists(path):
            for line in open(path, encoding="utf8"):
                if line.strip():
                    d = json.loads(line); m = Memory(**{k: v for k, v in d.items() if k in _FIELDS}); self._m[m.id] = m
            self._n = itertools.count(len(self._m) + 1)

    def _save(self):
        if self.path:
            with open(self.path, "w", encoding="utf8") as f:
                for m in self._m.values(): f.write(json.dumps(asdict(m), ensure_ascii=False) + "\n")

    def add(self, text, *, author, origin, date, scope="team", status="trial"):
        with self._lock:
            n = _norm(text)
            for m in self._m.values():
                if m.status != "retired" and _norm(m.text) == n:
                    events.emit("memory.rejected", text=text, reason="duplicate"); return None, f"duplicate of {m.id}"
            for m in self._m.values():
                if m.status == "retired" and _jac(m.text, text) >= self.tj:
                    events.emit("memory.rejected", text=text, reason="tombstone"); return None, f"tombstone: similar to retired {m.id}"
            m = Memory(f"m{next(self._n)}", text, author, origin, date, status, scope)
            self._m[m.id] = m; self._bm = None
            if self.path:
                with open(self.path, "a", encoding="utf8") as f: f.write(json.dumps(asdict(m), ensure_ascii=False) + "\n")
        events.emit("memory.added", memory=asdict(m))
        return m, "ok"

    def search(self, query, k=40, reader=None):
        with self._lock:
            if self._bm is None:
                self._act = [m for m in self._m.values() if m.status != "retired"]
                self._bm = BM25Okapi([_tok(m.text) or ["_"] for m in self._act]) if self._act else False
            if not self._bm: return []
            sc = self._bm.get_scores(_tok(query)); act = self._act
        idx = range(len(act)) if reader is None else [i for i in range(len(act)) if _visible(act[i].scope, reader)]
        top = sorted(idx, key=lambda i: -sc[i])[:k]
        return [act[i] for i in top]

    def get(self, mid): return self._m[mid]
    def all(self): return list(self._m.values())

    def set_status(self, mid, status, reason=""):
        assert status in STATUSES
        with self._lock:
            m = self._m[mid]; m.status, m.reason = status, reason; self._bm = None; self._save()

    def flag(self, mid, reason=""):
        with self._lock:
            m = self._m[mid]; m.flagged, m.reason = True, reason; self._save()

    def _new(self, old, text, author, status, owner=None):
        m = Memory(f"m{next(self._n)}", text, author, old.origin, old.date, status, old.scope, supersedes=old.id, owner=owner)
        self._m[m.id] = m
        return m

    def _retire(self, m, reason):
        m.status, m.reason, m.flagged = "retired", reason, False
        self._bm = None

    def correct(self, mid, text, author):
        """New memory superseding `mid`; the old one is retired. Returns (new, old). Locked memories need resolve()."""
        with self._lock:
            old = self._m[mid]
            if old.status == "locked": raise PermissionError(f"{mid} is locked; its owner must resolve it")
            new = self._new(old, text, author, "trial")
            self._retire(old, f"superseded by {new.id}"); self._save()
        events.emit("memory.added", memory=asdict(new))
        events.emit("memory.retired", memory_id=old.id, reason=old.reason, task_ids=[])
        events.emit("memory.corrected", memory_id=old.id, new_id=new.id, author=author)
        return new, old

    def retire(self, mid, reason="", author=None):
        with self._lock:
            m = self._m[mid]
            if m.status == "locked": raise PermissionError(f"{mid} is locked; its owner must resolve it")
            self._retire(m, reason); self._save()
        events.emit("memory.retired", memory_id=mid, reason=reason, task_ids=[], author=author)
        return m

    def lock(self, mid, owner):
        with self._lock:
            m = self._m[mid]
            if m.status == "locked" and m.owner != owner: raise PermissionError(f"{mid} is locked by someone else")
            m.status, m.owner, m.reason = "locked", owner, f"locked by {owner}"; self._bm = None; self._save()
        events.emit("memory.locked", memory_id=mid, owner=owner)
        return m

    def resolve(self, mid, owner, action, text=None):
        """Owner decides about a locked memory: keep (clears the flag), retire, or correct (needs text). Returns the resulting memory."""
        if action not in ("keep", "retire", "correct"): raise ValueError("action must be keep, retire or correct")
        if action == "correct" and not (text and text.strip()): raise ValueError("text required for correct")
        with self._lock:
            m = self._m[mid]
            if m.owner is None or m.owner != owner: raise PermissionError(f"{owner} is not the owner of {mid}")
            new_id = None
            if action == "keep":
                m.flagged = False
            elif action == "retire":
                self._retire(m, f"retired by owner {owner}")
            else:
                new = self._new(m, text, owner, "locked", owner=owner); new_id = new.id
                self._retire(m, f"superseded by {new.id}")
            self._save()
            result = self._m[new_id] if new_id else m
        if new_id: events.emit("memory.added", memory=asdict(result))
        if action != "keep": events.emit("memory.retired", memory_id=mid, reason=m.reason, task_ids=[])
        events.emit("memory.resolved", memory_id=mid, owner=owner, action=action, new_id=new_id)
        return result
