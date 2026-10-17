"""BrainBob benchmark runner.
  python bench.py locomo --convs 2          three-way comparison (none / all / audited)
  python bench.py locomo --fast             1 conversation, 30 audit + 30 heldout, small tokens, high concurrency
  python bench.py longmemeval --n 50 [--conditions brainbob,full]
"""
import argparse, collections, datetime, json, os, sys, time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from brainbob import agent, curator, events, llm
from brainbob.evaluator import Evaluator
from brainbob.memory import MemoryStore
from adapters import locomo, longmemeval

HERE = os.path.dirname(os.path.abspath(__file__))
POOL = ThreadPoolExecutor(96)  # leaf work only (calls llm); conversation-level threads live in another pool


def pmap(fn, xs):
    return [f.result() for f in [POOL.submit(fn, x) for x in xs]]


def tok(mems): return sum(len(m.text) + len(m.date) + 8 for m in mems) // 4  # ~4 chars/token estimate


def ask(task, store, k=40, with_memory=True):
    mems = store.search(task.question, k) if with_memory else []
    events.emit("memory.retrieved", task_id=task.id, memory_ids=[m.id for m in mems])
    a = agent.answer(task.question, mems, now=task.now)
    events.emit("answer.produced", task_id=task.id, answer=a.text, cited_ids=a.cited_ids)
    return dict(id=task.id, correct=bool(task.grade(a.text)), ctx=tok(mems), cited=a.cited_ids)


def run_conv(conv_id, eps, a):
    t0 = time.time()
    writers = list(a.writers)  # roles, careful first so it wins dedup
    store, store_c = MemoryStore(), MemoryStore()
    for r in writers: pmap(lambda e: curator.extract(e, r), eps)  # parallel model calls (cached) ...
    for e in eps:                                                    # ... then ordered adds, ids deterministic
        for r in writers:
            curator.ingest(e, store, role=r)
        if "curator" in writers: curator.ingest(e, store_c, role="curator")
    lim = a.limit
    audit, held = locomo.tasks(conv_id, "audit", limit=lim), locomo.tasks(conv_id, "heldout", limit=lim)
    ev = Evaluator(store)
    ctx = {}

    def observe(t):
        mems = store.search(t.question, 40); ctx[t.id] = (t, mems)
        ev.observe(t, mems, lambda q, m: agent.answer(q, m, now=t.now))

    f_none = [POOL.submit(ask, t, store, 40, False) for t in held]
    f_all = [POOL.submit(ask, t, store, 40, True) for t in held]
    f_car = [POOL.submit(ask, t, store_c) for t in held] if len(writers) > 1 else []
    f_obs = [POOL.submit(observe, t) for t in audit]
    out = dict(none=[f.result() for f in f_none])
    if f_car: out["careful_only"] = [f.result() for f in f_car]
    out["all"] = [f.result() for f in f_all]
    for f in f_obs: f.result()

    def confirm(mid):  # delete the memory and re-answer with a fresh model call (no cache)
        for tid in ev.stats(mid)["harmed"]:
            t, mems = ctx[tid]
            r = agent.answer(t.question, [m for m in mems if m.id != mid], now=t.now, fresh=True)
            return bool(t.grade(r.text))
        return False

    orig = {m.id: m.status for m in store.all()}
    tiers = {}
    for mc in (3, 2, 1):  # same evidence, review re-run per threshold; store restored between tiers
        ev.min_changes = mc; ev.decisions = []
        decisions = ev.review(confirm)
        rows = [f.result() for f in [POOL.submit(ask, t, store) for t in held]]
        tiers[mc] = dict(rows=rows, decisions=decisions, report=ev.report())
        for mid, st in orig.items():
            m = store.get(mid)
            if m.status != st or m.flagged: store.set_status(mid, st, ""); m.flagged = False
    out.update({f"audited_min{mc}": t["rows"] for mc, t in tiers.items()})
    return dict(conv=conv_id, ev=ev, out=out, tiers=tiers, n_audit=len(audit), n_heldout=len(held), n_mem=len(store.all()),
                n_flips=len(ev.evidence) // 2, wall=time.time() - t0)


def pct(rows):
    return f"{sum(r['correct'] for r in rows)}/{len(rows)} ({100 * sum(r['correct'] for r in rows) / max(1, len(rows)):.0f}%)"


def cost_total():
    u = llm.usage()
    return u, sum(v["usd"] for v in u.values()), sum(v["usd_all"] for v in u.values())


def locomo_main(a):
    a.writers = [{"careful": "curator", "sloppy": "curator_sloppy"}[w] for w in a.writers.split(",")]
    noisy = "curator_sloppy" in a.writers
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + "-locomo" + ("-fast" if a.fast else "")
    rd = os.path.join(HERE, "results", ts); os.makedirs(rd)
    events.set_log(os.path.join(rd, "events.jsonl"))
    if a.fast:
        a.convs, a.limit = 1, 30
        for r in ("curator", "curator_sloppy", "judge"): llm.configure(r, concurrency=32)
        llm.configure("agent", concurrency=32, max_tokens=256)
    t0 = time.time()
    convs = locomo.conversations(a.convs)
    with ThreadPoolExecutor(len(convs)) as ex:
        res = [f.result() for f in [ex.submit(run_conv, cid, eps, a) for cid, eps in convs]]
    wall = time.time() - t0
    cond = {c: [r for x in res for r in x["out"][c]] for c in res[0]["out"]}
    u, usd, usd_all = cost_total()
    cats = sorted(set(locomo.category(r["id"]) for r in cond["none"]))
    bycat = {c: {k: pct([r for r in rows if locomo.category(r["id"]) == c]) for k, rows in cond.items()} for c in cats}
    tier_sum = {}
    for mc in (3, 2, 1):
        authors, retired = {}, []
        for x in res:
            t = x["tiers"][mc]
            for au, v in t["report"]["authors"].items(): authors.setdefault(au, collections.Counter()).update(v)
            retired += t["report"]["retired"]
        ds = [d for x in res for d in x["tiers"][mc]["decisions"]]
        tier_sum[mc] = dict(retired=sum(d.action == "retire" for d in ds), promoted=sum(d.action == "promote" for d in ds),
                            flagged=sum(d.action == "flag" for d in ds), authors={k: dict(v) for k, v in authors.items()}, retired_memories=retired)
    summary = dict(mode="fast" if a.fast else "full", writers=a.writers, convs=[x["conv"] for x in res], agent_model=llm._roles()["agent"]["model"],
                   sloppy_temperature=llm._roles()["curator_sloppy"]["temperature"],
                   accuracy={k: pct(v) for k, v in cond.items()}, by_category=bycat,
                   n_heldout=sum(x["n_heldout"] for x in res), n_audit=sum(x["n_audit"] for x in res),
                   n_memories=sum(x["n_mem"] for x in res), n_flips=sum(x["n_flips"] for x in res), tiers=tier_sum,
                   avg_ctx_tokens={k: round(sum(r["ctx"] for r in v) / max(1, len(v))) for k, v in cond.items()},
                   cost_usd_fresh=round(usd, 4), cost_usd_incl_cached=round(usd_all, 4),
                   cost_by_role={k: {kk: (round(vv, 4) if isinstance(vv, float) else vv) for kk, vv in v.items()} for k, v in u.items()}, wall_s=round(wall, 1))
    json.dump(summary, open(os.path.join(rd, "summary.json"), "w"), indent=1, ensure_ascii=False)
    title = "LoCoMo + noisy writer (stress test)" if noisy else "BrainBob on LoCoMo"
    L = [f"# {title} ({ts})", "", f"Convs: {summary['convs']}; writers {a.writers} (sloppy temp {summary['sloppy_temperature']}); agent {summary['agent_model']}; heldout n={summary['n_heldout']}, audit n={summary['n_audit']}, memories={summary['n_memories']}, flips={summary['n_flips']}.", "",
         "| group | accuracy | avg ctx tokens (est.) | " + " | ".join(cats) + " |", "|" + "---|" * (3 + len(cats))]
    for k in cond: L.append(f"| {k} | {summary['accuracy'][k]} | {summary['avg_ctx_tokens'][k]} | " + " | ".join(bycat[c][k] for c in cats) + " |")
    L += ["", "## Threshold (min_changes) -> retire / promote / flag", ""]
    for mc, t in tier_sum.items(): L.append(f"- min_changes={mc}: retired {t['retired']}, promoted {t['promoted']}, flagged {t['flagged']}")
    for mc, t in tier_sum.items():
        L += ["", f"## Author ledger (min_changes={mc})", "", "| author | written | helped | harmed | promoted | retired | flagged |", "|---|---|---|---|---|---|---|"]
        for au, v in t["authors"].items(): L.append(f"| {au} | {v['written']} | {v['helped']} | {v['harmed']} | {v['promoted']} | {v['retired']} | {v['flagged']} |")
    L += ["", f"Cost fresh ${usd:.4f} (incl. cached ${usd_all:.4f}); wall {wall:.0f}s.", "", "| role | calls | cached | prompt tok | completion tok | USD fresh |", "|---|---|---|---|---|---|"]
    for k, v in u.items(): L.append(f"| {k} | {v['calls']} | {v['cached']} | {v['pt']} | {v['ct']} | {v['usd']:.4f} |")
    for mc, t in tier_sum.items():
        L += ["", f"## Retired memories (min_changes={mc})"] + [f"- {r['memory_id']} ({r['author']}): {r['text']} -- {r['reason']}" for r in t["retired_memories"]]
    open(os.path.join(rd, "results.md"), "w", encoding="utf-8").write("\n".join(L))
    print(f"\n{'group':16} heldout acc")
    for k in cond: print(f"{k:16} {summary['accuracy'][k]:16} ctx~{summary['avg_ctx_tokens'][k]}")
    for mc, t in tier_sum.items():
        print(f"min_changes={mc}: retired={t['retired']} promoted={t['promoted']} flagged={t['flagged']} | " + "; ".join(f"{au}: wrote {v['written']} helped {v['helped']} harmed {v['harmed']} prom {v['promoted']} ret {v['retired']}" for au, v in t["authors"].items()))
    print(f"flips={summary['n_flips']} mem={summary['n_memories']} | ${usd:.4f} fresh (${usd_all:.4f} incl cached) | {wall:.0f}s | {rd}")


DIAG = """Below is a chat session and one memory statement that was extracted from it. Decide whether the statement is supported by the session (faithful to what was actually said: names, numbers, dates, who did what). Reply with exactly one word: SUPPORTED or UNSUPPORTED (wrong, invented, garbled, or unrelated).

SESSION:
{s}

MEMORY: {m}"""


def diag_main(a):
    """Diagnostic only: how sloppy is the sloppy writer? Judge 20 random memories against their source session."""
    import random, re
    cid, eps = locomo.conversations(1)[0]
    byid = {e.id: e for e in eps}
    pmap(lambda e: curator.extract(e, "curator_sloppy"), eps)
    store = MemoryStore()
    for e in eps: curator.ingest(e, store, role="curator_sloppy")
    mems = random.Random(3).sample(store.all(), 20)

    def j(m):
        c = llm.complete("judge", [{"role": "user", "content": DIAG.format(s=byid[m.origin].text, m=m.text)}], max_tokens=1024)
        f = re.findall(r"\b(UNSUPPORTED|SUPPORTED)\b", c.upper()); return bool(f) and f[-1] == "SUPPORTED"
    ok = pmap(j, mems)
    print(f"sloppy temp {llm._roles()['curator_sloppy']['temperature']}: {len(store.all())} memories in {cid}; sampled 20, unsupported {20 - sum(ok)}/20")
    for m, o in zip(mems, ok): print(("OK  " if o else "BAD ") + m.text[:140])


def lme_one(q, conds):
    out = {}
    if "brainbob" in conds:
        store = MemoryStore()
        for e in longmemeval.episodes(q): curator.ingest(e, store)
        mems = sorted(store.search(q["question"], 40), key=lambda m: m.date)
        r = agent.answer(q["question"], mems, now=q["question_date"])
        out["brainbob"] = dict(correct=longmemeval.judge(q, r.text), ctx=tok(mems))
    if "full" in conds:
        ctx = "\n\n".join(f"[Session date: {e.date}]\n{e.text}" for e in longmemeval.episodes(q))
        p = ("You are answering a question about a user based on their past chat history with an assistant.\n\nBelow is the complete chat history, ordered by time.\n\n"
             f"{ctx}\n\nCurrent date: {q['question_date']}\nQuestion: {q['question']}\nAnswer concisely. If the information needed is not present, say you don't know / the information was not provided.")
        t = llm.complete("agent", [{"role": "user", "content": p}], max_tokens=4096, temperature=None, extra_body=None)
        out["full"] = dict(correct=longmemeval.judge(q, t), ctx=len(p) // 4)
    return dict(qid=q["question_id"], qtype=q["question_type"], **out)


def lme_main(a):
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + "-longmemeval"
    rd = os.path.join(HERE, "results", ts); os.makedirs(rd)
    events.set_log(os.path.join(rd, "events.jsonl"))
    conds = a.conditions.split(",")
    qs = longmemeval.subset(a.n); t0 = time.time()
    with ThreadPoolExecutor(len(qs)) as ex:
        rows = [f.result() for f in [ex.submit(lme_one, q, conds) for q in qs]]
    wall = time.time() - t0; u, usd, usd_all = cost_total()
    summ = dict(n=len(rows), agent_model=llm._roles()["agent"]["model"], wall_s=round(wall), cost_usd_fresh=round(usd, 4), cost_usd_incl_cached=round(usd_all, 4))
    L = [f"# LongMemEval_S ({ts})", "", f"agent {summ['agent_model']}; judge gpt-oss-120b; n={len(rows)}", ""]
    for c in conds:
        rs = [r for r in rows if c in r]
        summ[c] = pct([r[c] for r in rs]); L.append(f"- {c}: {summ[c]}")
        for t in sorted({r['qtype'] for r in rs}): L.append(f"    - {t}: {pct([r[c] for r in rs if r['qtype'] == t])}")
    L.append(f"\nCost fresh ${usd:.4f} (incl cached ${usd_all:.4f}); wall {wall:.0f}s")
    json.dump(summ, open(os.path.join(rd, "summary.json"), "w"), indent=1)
    open(os.path.join(rd, "results.md"), "w", encoding="utf-8").write("\n".join(L)); print("\n".join(L)); print(rd)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    l = sp.add_parser("locomo"); l.add_argument("--convs", type=int, default=2); l.add_argument("--fast", action="store_true"); l.add_argument("--writers", default="careful"); l.set_defaults(limit=None)
    sp.add_parser("diag")
    m = sp.add_parser("longmemeval"); m.add_argument("--n", type=int, default=50); m.add_argument("--conditions", default="brainbob")
    a = ap.parse_args()
    {"locomo": locomo_main, "diag": diag_main, "longmemeval": lme_main}[a.cmd](a)
    sys.stdout.flush(); os._exit(0)
