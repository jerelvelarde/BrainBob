"""Run the whole memory-audit demo over HTTP and record it.

    .venv/Scripts/python demo/reset.py
    .venv/Scripts/python demo/serve.py --port 3002          # in another terminal
    .venv/Scripts/python demo/run_scenario.py --base http://127.0.0.1:3002

Steps: seed (synthetic conversations + seeded history) -> live Ask (wrong, cites the bad memory)
-> Check (correct answer) -> Review (retire bad, promote good) -> live Ask of a different question by a
different reader (right, cited). Subscribes to /events the whole time and writes
results/<timestamp>-demo/{responses.json, events.jsonl, meta.json, state/}. Exit code 1 if a check fails."""
import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import threading
import time

import httpx

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import seed as S  # noqa: E402

LIVE_ASK = dict(reader=S.SALES, question="What time does the Krusty Krab close on weekdays?")
LIVE_CHECK = "10 PM"
NEW_ASK = dict(reader=S.JOHN, question="How late can a customer walk in on a Thursday?")
FRONTEND_TYPES = {"episode.ingested", "memory.added", "memory.rejected", "memory.retrieved", "answer.produced",
                  "evidence.recorded", "evaluation.started", "memory.checked", "evaluation.finished", "memory.promoted",
                  "memory.retired", "memory.flagged", "memory.locked", "memory.resolved", "memory.corrected"}
FRONTEND_STATUS = {"trial", "promoted", "retired", "locked"}


class Tail(threading.Thread):
    """Reads GET /events (SSE) from the start and keeps every stored event."""

    def __init__(self, base):
        super().__init__(daemon=True)
        self.base, self.events, self.replay_done = base, [], threading.Event()

    def run(self):
        with httpx.Client(timeout=None) as c, c.stream("GET", self.base + "/events") as r:
            for line in r.iter_lines():
                if not line.startswith("data:"):
                    continue
                ev = json.loads(line[5:].strip())
                if ev.get("type") == "replay.done":
                    self.replay_done.set()
                else:
                    self.events.append(ev)

    def wait_for(self, pred, timeout=15):
        end = time.time() + timeout
        while time.time() < end:
            if any(pred(e) for e in list(self.events)):
                return True
            time.sleep(0.2)
        return False


def git(*args):
    try:
        return subprocess.run(["git", *args], cwd=BACKEND, capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:  # noqa: BLE001
        return None


def models():
    sys.path.insert(0, BACKEND)
    from brainbob import llm  # role map only; no call is made
    return {r: llm._roles()[r]["model"] for r in ("curator", "agent", "judge")}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base", default="http://127.0.0.1:3002")
    p.add_argument("--state", default=os.path.join(HERE, "state"), help="server state dir, snapshotted at the end")
    p.add_argument("--out", default=os.path.join(BACKEND, "results"))
    a = p.parse_args()
    base = a.base.rstrip("/")
    started = dt.datetime.now().astimezone()
    out_dir = os.path.join(a.out, started.strftime("%Y%m%d-%H%M%S") + "-demo")

    tail = Tail(base)
    tail.start()
    if not tail.replay_done.wait(10):
        raise SystemExit(f"no SSE from {base}/events")

    seeded = S.seed(base)
    ids, steps = seeded["ids"], seeded["steps"]
    checks = {"seeded history recorded the expected flips": all(s.get("expected_flip", True) for s in steps)}

    def step(name, phase, path, body, c):
        t = time.time()
        r = c.post(path, json=body)
        r.raise_for_status()
        res, secs = r.json(), round(time.time() - t, 1)
        steps.append(dict(phase=phase, step=name, request={"path": path, **body}, response=res, seconds=secs))
        print(f"[{phase}] {name} ({secs}s): {json.dumps(res)[:400]}")
        return res

    with httpx.Client(base_url=base, timeout=600) as c:
        a1 = step("1 ask (Sales Team)", "live", "/ask", LIVE_ASK, c)
        checks["live answer cites the bad memory"] = ids["bad"] in a1["cited_ids"]
        checks["live answer says 6 PM (wrong)"] = bool(S.PATTERNS["bad"].search(a1["answer"]))
        fb = step("2 check", "live", "/feedback", {"task_id": a1["task_id"], "correct_answer": LIVE_CHECK}, c)
        checks["check: wrong with bad memory, right without"] = any(
            e["memory_id"] == ids["bad"] and e["shown"] and not e["correct"] for e in fb["evidence"]) and any(
            e["memory_id"] == ids["bad"] and not e["shown"] and e["correct"] for e in fb["evidence"])
        rv = step("3 review", "live", "/review", {}, c)
        acts = {(d["memory_id"], d["action"]) for d in rv["decisions"]}
        checks["review retires the bad memory"] = (ids["bad"], "retire") in acts
        checks["review does not retire the good memory"] = (ids["good"], "retire") not in acts
        checks["review promotes the good memory"] = (ids["good"], "promote") in acts
        a2 = step("4 ask a different question (John, new agent)", "live", "/ask", NEW_ASK, c)
        checks["new answer says 10 PM, not 6 PM"] = bool(S.PATTERNS["hours"].search(a2["answer"])) and not S.PATTERNS["bad"].search(a2["answer"])
        checks["new answer cites the real hours memory"] = ids["hours"] in a2["cited_ids"]
        checks["new answer does not use the bad memory"] = ids["bad"] not in a2["cited_ids"] and \
            ids["bad"] not in [m["id"] for m in a2["memories"]]
        tail.wait_for(lambda e: e.get("type") == "answer.produced" and e.get("task_id") == a2["task_id"])
        mems = {m["id"]: m for m in c.get("/memories").json()}

    events = sorted(tail.events, key=lambda e: e["seq"])
    retired = [e for e in events if e["type"] == "memory.retired" and e.get("memory_id") == ids["bad"]]
    checks["memory.retired event for the bad memory, confirmed=true"] = bool(retired) and all(e.get("confirmed") for e in retired)
    checks["bad memory status retired"] = mems[ids["bad"]]["status"] == "retired"
    checks["good memory status promoted"] = mems[ids["good"]]["status"] == "promoted"
    checks["only frontend event types"] = all(e["type"] in FRONTEND_TYPES for e in events)
    checks["only frontend memory statuses"] = all(m["status"] in FRONTEND_STATUS for m in mems.values()) and all(
        e["memory"]["status"] in FRONTEND_STATUS for e in events if e["type"] == "memory.added")

    os.makedirs(out_dir)
    with open(os.path.join(out_dir, "events.jsonl"), "w", encoding="utf8") as f:
        for e in events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    with open(os.path.join(out_dir, "responses.json"), "w", encoding="utf8") as f:
        json.dump({"ids": ids, "steps": steps, "final_memories": list(mems.values())}, f, indent=2, ensure_ascii=False)
    snap = os.path.join(out_dir, "state")
    os.makedirs(snap)
    for fn in ("memory.jsonl", "events.jsonl", "episodes.jsonl"):  # what reset.py --restore copies back
        if os.path.exists(os.path.join(a.state, fn)):
            shutil.copy(os.path.join(a.state, fn), os.path.join(snap, fn))
    meta = {"started": started.isoformat(), "finished": dt.datetime.now().astimezone().isoformat(), "base": base,
            "git_commit": git("rev-parse", "HEAD"), "git_dirty_files": len((git("status", "--porcelain") or "").splitlines()),
            "models": models(), "agent_model_env": os.environ.get("BRAINBOB_AGENT_MODEL"),
            "server_mode": "server.py --legacy (no permissions, no write-time maintenance), Evaluator min_changes=3",
            "data": "seed conversations are synthetic; seeded asks/checks are real model calls at seed time; steps 1-4 are live",
            "ids": ids, "checks": checks, "passed": all(checks.values()),
            "seconds": {s["step"]: s["seconds"] for s in steps}}
    with open(os.path.join(out_dir, "meta.json"), "w", encoding="utf8") as f:
        json.dump(meta, f, indent=2)
    for k, v in checks.items():
        print(("PASS " if v else "FAIL ") + k)
    print(f"results: {out_dir}")
    sys.exit(0 if meta["passed"] else 1)


if __name__ == "__main__":
    main()
