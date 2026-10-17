"""In-process event bus + append-only events.jsonl."""
import json, queue, threading, time

_subs, _hist, _lock = [], [], threading.Lock()
_log_path = None


def set_log(path):
    global _log_path
    _log_path = path


def emit(type, **data):
    ev = {"type": type, "ts": time.time(), **data}
    with _lock:
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


def history():
    with _lock:
        return list(_hist)
