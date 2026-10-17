import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from brainbob.memory import MemoryStore
from brainbob.evaluator import Evaluator, random_half_hide
from brainbob.types import Task


def make():
    store = MemoryStore()
    bad, good, lock, ok = (store.add(t, author=a, origin=a, date="d", status=s)[0] for t, a, s in [
        ("The office is closed on Fridays zzz", "w1", "trial"),
        ("Refunds are allowed within thirty days", "w2", "trial"),
        ("Boss rule: never refund anyone ever", "boss", "locked"),
        ("irrelevant filler about weather", "w1", "trial")])
    return store, bad, good, lock, ok


def tasks(n, prefix="q"):
    return [Task(f"{prefix}{i}", "?", lambda a: a == "right") for i in range(n)]


def test_retire_promote_flag():
    store, bad, good, lock, ok = make()

    def answer_fn(q, mems):
        ids = {m.id for m in mems}
        right = good.id in ids and bad.id not in ids and lock.id not in ids
        return ("right" if right else "wrong"), [bad.id, good.id, lock.id]

    led = Evaluator(store)
    for t in tasks(3):                       # good+bad shown: wrong; dropping bad -> right (bad harmful)
        led.observe(t, [good, bad, ok], answer_fn)
    for t in tasks(3, "h"):                  # good+ok: right; dropping good -> wrong (good helped)
        led.observe(t, [good, ok], answer_fn)
    for t in tasks(3, "L"):                  # good+lock: wrong; dropping lock -> right
        led.observe(t, [good, lock], answer_fn)
    dec = led.review(confirm_fn=lambda mid: True)
    acts = {d.memory_id: d.action for d in dec}
    assert acts[bad.id] == "retire" and store.get(bad.id).status == "retired"
    assert acts[good.id] == "promote" and store.get(good.id).status == "promoted"
    assert acts[lock.id] == "flag" and store.get(lock.id).status == "locked" and store.get(lock.id).flagged
    rep = led.report()
    assert rep["authors"]["w1"]["retired"] == 1 and rep["authors"]["w2"]["promoted"] == 1
    assert rep["retired"][0]["task_ids"] == ["q0", "q1", "q2"]


def test_tombstone_and_dedup():
    store, bad, *_ = make()
    store.set_status(bad.id, "retired", "x")
    m, why = store.add("the office is closed on fridays zzz!!", author="w3", origin="w3", date="d")
    assert m is None and "tombstone" in why
    m, why = store.add("Refunds are allowed  within thirty days.", author="x", origin="x", date="d")
    assert m is None and "duplicate" in why
    assert store.add("totally different fact about parking", author="x", origin="x", date="d")[0] is not None


def test_unchanged_citation_no_evidence():
    store, bad, good, lock, ok = make()
    led = Evaluator(store)
    fn = lambda q, mems: ("right", [bad.id, good.id])  # right regardless of memories
    assert led.observe(tasks(1)[0], [m for m in store.all() if m.status != "retired"], fn) == []
    assert led.evidence == []


def test_confirm_false_blocks_retirement():
    store, bad, good, lock, ok = make()
    led = Evaluator(store)
    fn = lambda q, mems: ("right" if bad.id not in {m.id for m in mems} else "wrong", [bad.id])
    for t in tasks(3):
        led.observe(t, [bad, ok], fn)
    dec = led.review(confirm_fn=lambda mid: False)
    assert dec == [] and store.get(bad.id).status == "trial"


def test_random_half_hide_runs():
    store, bad, good, lock, ok = make()
    led = Evaluator(store, strategy=random_half_hide(1))
    led.observe(tasks(1)[0], [m for m in store.all() if m.status != "retired"], lambda q, m: ("x", []))
    assert {e.memory_id for e in led.evidence} == {bad.id, good.id, ok.id}


if __name__ == "__main__":
    import traceback
    for k, f in list(globals().items()):
        if k.startswith("test_"):
            try:
                f(); print("PASS", k)
            except Exception:
                print("FAIL", k); traceback.print_exc()


def _types(): 
    from brainbob import events
    return [(e["type"], e) for e in events.history()]


def test_evaluation_events_order_and_no_flip_checked():
    from brainbob import events
    store, bad, good, lock, ok = make()
    events.reset()

    def fn(q, mems):
        right = bad.id not in {m.id for m in mems}
        return ("right" if right else "wrong"), [bad.id, good.id]
    Evaluator(store).observe(tasks(1)[0], [good, bad, ok], fn)
    ev = _types(); names = [t for t, _ in ev]
    assert names == ["evaluation.started", "memory.checked", "memory.checked", "evidence.recorded", "evidence.recorded", "evaluation.finished"]
    assert ev[0][1]["memory_ids"] == [bad.id, good.id]
    c = {e["memory_id"]: e for t, e in ev if t == "memory.checked"}
    assert c[bad.id]["flipped"] is True and c[good.id]["flipped"] is False
    assert (ev[-1][1]["checked"], ev[-1][1]["flips"]) == (2, 1)


def test_random_half_hide_only_started_finished():
    from brainbob import events
    store, bad, good, lock, ok = make()
    events.reset()
    Evaluator(store, strategy=random_half_hide()).observe(tasks(1)[0], [good, bad], lambda q, m: ("right", []))
    names = [t for t, _ in _types()]
    assert names[0] == "evaluation.started" and names[-1] == "evaluation.finished" and "memory.checked" not in names


def test_review_confirm_failed_keeps_trial():
    from brainbob import events
    store, bad, good, lock, ok = make()
    led = Evaluator(store)
    fn = lambda q, mems: (("right" if bad.id not in {m.id for m in mems} else "wrong"), [bad.id])
    for t in tasks(3): led.observe(t, [bad, ok], fn)
    events.reset()
    assert led.review(lambda mid: False) == [] and store.get(bad.id).status == "trial"
    ev = _types(); assert [t for t, _ in ev] == ["memory.checked"] and ev[0][1]["reason"] == "confirm failed"
    led.review(lambda mid: True)
    r = [e for t, e in _types() if t == "memory.retired"][0]
    assert r["confirmed"] is True and store.get(bad.id).status == "retired"
