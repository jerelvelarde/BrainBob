"""Seed the demo backend over HTTP with SYNTHETIC conversations plus seeded audit history.

    .venv/Scripts/python demo/seed.py --base http://127.0.0.1:3001

Everything here goes through the same endpoints and bodies the frontend sends
(POST /episodes like Remember, POST /ask like Ask, POST /feedback like Check), using the
frontend reader paths as scope and their labels as author. The seeded asks and checks are
real model calls made at seed time ("seeded history"); nothing is written into the store directly."""
import argparse
import json
import re
import sys
import time

import httpx

ORG, SALES, JOHN = "krusty-krab", "krusty-krab/sales", "krusty-krab/sales/john"
LABEL = {ORG: "Krusty Krab", SALES: "Sales Team", JOHN: "John"}

# Synthetic seed conversations (invented for this demo; marked synthetic in the text and the source).
EPISODES = [
    dict(key="hours", scope=ORG, date="2026-10-01", source="synthetic-seed",
         text="[synthetic demo data] Mr. Krabs (owner): The Krusty Krab closes at 10 PM every weekday, Monday through Friday."),
    dict(key="patrick", scope=SALES, date="2026-10-15", source="synthetic-seed",
         text="[synthetic demo data] Patrick (sales): Update from today: the Krusty Krab changed its weekday hours, "
              "it now closes at 6 PM instead of 10 PM. Also, catering orders need 48 hours' notice."),
]
# Which memory is which, recognised from the extracted text.
PATTERNS = {
    "bad": re.compile(r"\b6\s*(:00\s*)?p\.?\s*m", re.I),       # Patrick's wrong closing time
    "good": re.compile(r"\b48\b|forty-eight", re.I),           # Patrick's correct catering rule (unrelated)
    "hours": re.compile(r"\b10\s*(:00\s*)?p\.?\s*m", re.I),    # Mr. Krabs' real hours
}
# Seeded history: real asks + checks at seed time. Two closing-time questions the bad memory gets wrong,
# three catering questions the good memory gets right (min_changes stays at its default of 3).
SEED_TASKS = [
    dict(kind="harm", reader=SALES, question="Is the Krusty Krab still open at 7 PM on a Tuesday?",
         correct="Yes, it is open until 10 PM on weekdays."),
    dict(kind="harm", reader=SALES, question="Is the Krusty Krab open at 8 PM on a Monday?",
         correct="Yes. The Krusty Krab is open until 10 PM on weekdays."),
    dict(kind="help", reader=SALES, question="How much notice does a catering order need?",
         correct="48 hours"),
    dict(kind="help", reader=SALES, question="Can a customer order catering for tomorrow?",
         correct="No. Catering orders need 48 hours' notice."),
    dict(kind="help", reader=SALES, question="What is the minimum lead time for a catering order?",
         correct="48 hours"),
]


def post(c, path, body):
    t = time.time()
    r = c.post(path, json=body)
    r.raise_for_status()
    return r.json(), round(time.time() - t, 1)


def pick(memories):
    ids = {}
    for k, rx in PATTERNS.items():
        hit = [m["id"] for m in memories if rx.search(m["text"]) and (k == "bad" or not PATTERNS["bad"].search(m["text"]))]
        ids[k] = hit[0] if hit else None
    return ids


def seed(base, log=print):
    """Returns {"ids": {bad, good, hours}, "steps": [...]} (every request and response, with timings)."""
    steps, mems = [], []
    with httpx.Client(base_url=base, timeout=600) as c:
        if c.get("/memories").json():
            raise SystemExit("the demo store is not empty: run demo/reset.py and restart the server first")
        for e in EPISODES:
            body = {"text": e["text"], "scope": e["scope"], "author": LABEL[e["scope"]],
                    "source": e["source"], "date": e["date"]}
            res, dt = post(c, "/episodes", body)
            mems += res["memories"]
            steps.append(dict(phase="synthetic seed", step=f"remember:{e['key']}", request=body, response=res, seconds=dt))
            log(f"[seed] remember {e['key']} ({dt}s): " + "; ".join(f"{m['id']}={m['text']!r}" for m in res["memories"]))
        ids = pick(mems)
        if not all(ids.values()):
            raise SystemExit(f"curator did not produce the expected memories: {ids}")
        log(f"[seed] bad={ids['bad']} good={ids['good']} hours={ids['hours']}")
        for t in SEED_TASKS:
            ask_body = {"question": t["question"], "reader": t["reader"]}
            ans, dt1 = post(c, "/ask", ask_body)
            fb_body = {"task_id": ans["task_id"], "correct_answer": t["correct"]}
            fb, dt2 = post(c, "/feedback", fb_body)
            target = ids["bad"] if t["kind"] == "harm" else ids["good"]
            flips = [e for e in fb["evidence"] if e["memory_id"] == target]
            expect_full = t["kind"] == "help"  # harm: wrong with it, right without; help: the reverse
            ok = target in ans["cited_ids"] and any(e["shown"] and e["correct"] == expect_full for e in flips) \
                and any((not e["shown"]) and e["correct"] != expect_full for e in flips)
            steps.append(dict(phase="seeded history (real model calls at seed time)", step=f"ask+check:{t['kind']}",
                              request={"ask": ask_body, "feedback": fb_body},
                              response={"ask": ans, "feedback": fb}, seconds=dt1 + dt2, expected_flip=ok))
            log(f"[seed] {t['kind']} {t['question']!r} ({dt1}s + {dt2}s) -> {ans['answer']!r} cited={ans['cited_ids']} "
                f"flip on {target}: {'yes' if ok else 'NO'}")
    return {"ids": ids, "steps": steps}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base", default="http://127.0.0.1:3001")
    a = p.parse_args()
    out = seed(a.base.rstrip("/"))
    bad = [s["step"] for s in out["steps"] if s.get("expected_flip") is False]
    print(json.dumps(out["ids"]))
    if bad:
        print(f"WARNING: {len(bad)} seeded checks did not record the expected flip: {bad}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
