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
    store = MemoryStore()
    pmap(curator.extract, eps)  # parallel model calls (cached), then ordered adds so memory ids are deterministic
    for e in eps: curator.ingest(e, store)
    lim = a.limit
    audit, held = locomo.tasks(conv_id, "audit", limit=lim), locomo.tasks(conv_id, "heldout", limit=lim)
    ev = Evaluator(store)
    ctx = {}

    def observe(t):
        mems = store.search(t.question, 40); ctx[t.id] = (t, mems)
        ev.observe(t, mems, lambda q, m: agent.answer(q, m, now=t.now))

    f_none = [POOL.submit(ask, t, store, 40, False) for t in held]
    f_all = [POOL.submit(ask, t, store, 40, True) for t in held]
    f_obs = [POOL.submit(observe, t) for t in audit]
    none, allr = [f.result() for f in f_none], [f.result() for f in f_all]
    for f in f_obs: f.result()

    def confirm(mid):
        for tid in ev.stats(mid)["harmed"]:
            t, mems = ctx[tid]
            r = agent.answer(t.question, [m for m in mems if m.id != mid], now=t.now)
            return bool(t.grade(r.text))
        return False

    decisions = ev.review(confirm)
    aud = [f.result() for f in [POOL.submit(ask, t, store) for t in held]]
    return dict(conv=conv_id, store=store, ev=ev, none=none, all=allr, audited=aud, decisions=decisions, n_audit=len(audit),
                n_heldout=len(held), n_mem=len(store.all()), n_flips=len(ev.evidence) // 2, wall=time.time() - t0)


def pct(rows):
    return f"{sum(r['correct'] for r in rows)}/{len(rows)} ({100 * sum(r['correct'] for r in rows) / max(1, len(rows)):.0f}%)"


def cost_total():
    u = llm.usage()
    return u, sum(v["usd"] for v in u.values()), sum(v["usd_all"] for v in u.values())


def locomo_main(a):
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + "-locomo" + ("-fast" if a.fast else "")
    rd = os.path.join(HERE, "results", ts); os.makedirs(rd)
    events.set_log(os.path.join(rd, "events.jsonl"))
    if a.fast:
        a.convs, a.limit = 1, 30
        llm.configure("agent", concurrency=32, max_tokens=256); llm.configure("curator", concurrency=32); llm.configure("judge", concurrency=32)
    t0 = time.time()
    convs = locomo.conversations(a.convs)
    with ThreadPoolExecutor(len(convs)) as ex:
        res = [f.result() for f in [ex.submit(run_conv, cid, eps, a) for cid, eps in convs]]
    wall = time.time() - t0
    cond = {c: [r for x in res for r in x[c]] for c in ("none", "all", "audited")}
    decs = [d for x in res for d in x["decisions"]]
    n = lambda act: sum(d.action == act for d in decs)
    u, usd, usd_all = cost_total()
    cats = sorted(set(locomo.category(r["id"]) for r in cond["none"]))
    bycat = {c: {k: pct([r for r in rows if locomo.category(r["id"]) == c]) for k, rows in cond.items()} for c in cats}
    authors = collections.Counter()
    retired = []
    for x in res:
        rep = x["ev"].report()
        for au, v in rep["authors"].items(): authors.update({f"{au}.{k}": val for k, val in v.items()})
        retired += rep["retired"]
    summary = dict(mode="fast" if a.fast else "full", convs=[x["conv"] for x in res], agent_model=llm._roles()["agent"]["model"],
                   accuracy={k: pct(v) for k, v in cond.items()}, by_category=bycat,
                   n_heldout=sum(x["n_heldout"] for x in res), n_audit=sum(x["n_audit"] for x in res),
                   n_memories=sum(x["n_mem"] for x in res), n_flips=sum(x["n_flips"] for x in res),
                   retired=n("retire"), promoted=n("promote"), flagged=n("flag"), authors=dict(authors),
                   avg_ctx_tokens={k: round(sum(r["ctx"] for r in v) / max(1, len(v))) for k, v in cond.items()},
                   cost_usd_fresh=round(usd, 4), cost_usd_incl_cached=round(usd_all, 4),
                   cost_by_role={k: {kk: (round(vv, 4) if isinstance(vv, float) else vv) for kk, vv in v.items()} for k, v in u.items()},
                   wall_s=round(wall, 1), retired_memories=retired[:20])
    json.dump(summary, open(os.path.join(rd, "summary.json"), "w"), indent=1, ensure_ascii=False)
    L = [f"# BrainBob on LoCoMo ({ts})", "", f"Convs: {summary['convs']}; agent model {summary['agent_model']}; heldout n={summary['n_heldout']}, audit n={summary['n_audit']}, memories={summary['n_memories']}, flips={summary['n_flips']}.", "",
         "| group | accuracy | avg ctx tokens (est.) | " + " | ".join(cats) + " |", "|" + "---|" * (3 + len(cats))]
    for k in cond: L.append(f"| {k} | {summary['accuracy'][k]} | {summary['avg_ctx_tokens'][k]} | " + " | ".join(bycat[c][k] for c in cats) + " |")
    L += ["", f"Retired {summary['retired']}, promoted {summary['promoted']}, flagged {summary['flagged']}. Author ledger: {summary['authors']}", "",
          f"Cost fresh ${usd:.4f} (incl. cached ${usd_all:.4f}); wall {wall:.0f}s.", "", "| role | calls | cached | prompt tok | completion tok | USD fresh |", "|---|---|---|---|---|---|"]
    for k, v in u.items(): L.append(f"| {k} | {v['calls']} | {v['cached']} | {v['pt']} | {v['ct']} | {v['usd']:.4f} |")
    L += ["", "## Retired memories"] + [f"- {r['memory_id']} ({r['author']}): {r['text']} -- {r['reason']}" for r in retired]
    open(os.path.join(rd, "results.md"), "w", encoding="utf-8").write("\n".join(L))
    print(f"\n{'group':8} {'heldout acc':18}")
    for k in cond: print(f"{k:8} {summary['accuracy'][k]:18} ctx~{summary['avg_ctx_tokens'][k]}")
    print(f"retired={summary['retired']} promoted={summary['promoted']} flagged={summary['flagged']} flips={summary['n_flips']} | ${usd:.4f} fresh (${usd_all:.4f} incl cached) | {wall:.0f}s | {rd}")


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
    l = sp.add_parser("locomo"); l.add_argument("--convs", type=int, default=2); l.add_argument("--fast", action="store_true"); l.set_defaults(limit=None)
    m = sp.add_parser("longmemeval"); m.add_argument("--n", type=int, default=50); m.add_argument("--conditions", default="brainbob")
    a = ap.parse_args()
    (locomo_main if a.cmd == "locomo" else lme_main)(a)
    sys.stdout.flush(); os._exit(0)
