"""In-process event bus + append-only events.jsonl. Every event carries a monotonic `seq`."""
import json, os, queue, threading, time

_subs, _hist, _lock = [], [], threading.Lock()
_log_path = None
_seq = 0


def reset():
    """Forget in-memory state (tests)."""
    global _log_path, _seq
    with _lock:
        _hist.clear(); _subs.clear(); _log_path = None; _seq = 0


def set_log(path):
    """Point the log at `path`. An existing file is loaded back as history and numbering continues after its max seq."""
    global _log_path, _seq
    with _lock:
        _log_path = path
        if path and os.path.exists(path):
            loaded = []
            for line in open(path, encoding="utf8"):
                if line.strip():
                    try: loaded.append(json.loads(line))
                    except ValueError: pass
            for i, ev in enumerate(loaded):  # legacy lines without seq get one in file order
                if "seq" not in ev: ev["seq"] = (loaded[i - 1]["seq"] if i else 0) + 1
            _hist[:] = loaded
            _seq = max((e["seq"] for e in loaded), default=0)


def emit(type, **data):
    global _seq
    with _lock:
        _seq += 1
        ev = {"type": type, "ts": time.time(), "seq": _seq, **data}
        _hist.append(ev)
        for q in _subs:
            q.put(ev)
        if _log_path:
            with open(_log_path, "a", encoding="utf8") as f:
                f.write(json.dumps(ev, ensure_ascii=False, default=str) + "\n")
    return ev


def subscribe():
    q = queue.Queue()
    with _lock:
        _subs.append(q)
    return q


def unsubscribe(q):
    with _lock:
        if q in _subs:
            _subs.remove(q)


def history(after=None):
    """All events, or only those with seq > after."""
    with _lock:
        return [e for e in _hist if after is None or e.get("seq", 0) > after]
