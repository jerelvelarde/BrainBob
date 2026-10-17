"""Memory store: add / dedupe / tombstone / status / BM25 search / jsonl persistence. No LLM."""
import itertools, json, os, re, threading
from dataclasses import asdict
from rank_bm25 import BM25Okapi
from . import events
from .types import Memory

STATUSES = ("trial", "promoted", "retired", "locked")


def _norm(t): return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", t.lower())).strip()
def _tok(t): return re.findall(r"\w+", t.lower())
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
                    m = Memory(**json.loads(line)); self._m[m.id] = m
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

    def search(self, query, k=40):
        with self._lock:
            if self._bm is None:
                self._act = [m for m in self._m.values() if m.status != "retired"]
                self._bm = BM25Okapi([_tok(m.text) or ["_"] for m in self._act]) if self._act else False
            if not self._bm: return []
            sc = self._bm.get_scores(_tok(query)); act = self._act
        top = sorted(range(len(act)), key=lambda i: -sc[i])[:k]
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
