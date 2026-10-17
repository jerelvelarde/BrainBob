import argparse, json, os, re, sys, time, hashlib, random, threading, datetime, collections
from concurrent.futures import ThreadPoolExecutor, wait
import openai
from openai import OpenAI
from rank_bm25 import BM25Okapi

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "longmemeval_s_cleaned.json")
CACHE = os.path.join(HERE, "cache")
os.makedirs(CACHE, exist_ok=True)
ANS_M = "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B"
EXT_M = "nvidia/Nemotron-3.5-Lightning-30B-A3B"
JUDGE_M = "openai/gpt-oss-120b"
PRICE = {ANS_M: (0.30, 2.40), EXT_M: (0.05, 0.20), JUDGE_M: (0.05, 0.25)}
KEY = open(os.path.expanduser("~/.config/crusoe/api.key")).read().strip()
client = OpenAI(api_key=KEY, base_url="https://api.inference.crusoecloud.com/v1", timeout=900, max_retries=0)
SEM = {"extract": threading.Semaphore(24), "answer": threading.Semaphore(8), "judge": threading.Semaphore(16)}
USAGE = []; ULOCK = threading.Lock()
STATS = collections.Counter()


def llm(stage, model, messages, max_tokens=4096, temperature=None, extra_body=None):
    payload = json.dumps([model, messages, max_tokens, temperature, extra_body], sort_keys=True)
    h = hashlib.sha256(payload.encode()).hexdigest()
    path = os.path.join(CACHE, h + ".json")
    if os.path.exists(path):
        try:
            d = json.load(open(path))
            with ULOCK: USAGE.append(dict(stage=stage, model=model, pt=d["pt"], ct=d["ct"], cached=True))
            return d["content"], d["pt"]
        except Exception:
            pass
    kw = dict(model=model, messages=messages, max_tokens=max_tokens)
    if temperature is not None: kw["temperature"] = temperature
    if extra_body: kw["extra_body"] = extra_body
    delay = 3
    with SEM[stage]:
        for attempt in range(8):
            try:
                r = client.chat.completions.create(**kw)
                break
            except (openai.RateLimitError, openai.APIConnectionError, openai.APITimeoutError, openai.InternalServerError):
                STATS["retry_" + stage] += 1
                time.sleep(delay); delay = min(delay * 2, 60)
            except openai.APIStatusError as e:
                if e.status_code >= 500 or e.status_code == 429:
                    STATS["retry_" + stage] += 1; time.sleep(delay); delay = min(delay * 2, 60)
                else:
                    STATS["fail_" + stage] += 1; print("HTTP", e.status_code, str(e)[:200].replace(KEY, "***"), file=sys.stderr); return "", 0
        else:
            STATS["fail_" + stage] += 1; return "", 0
    c = r.choices[0].message.content or ""
    if "</think>" in c: c = c.split("</think>")[-1]
    c = c.strip()
    u = r.usage
    pt, ct = u.prompt_tokens, u.completion_tokens
    json.dump(dict(content=c, pt=pt, ct=ct), open(path, "w"))
    with ULOCK: USAGE.append(dict(stage=stage, model=model, pt=pt, ct=ct, cached=False))
    return c, pt


# ---- judge prompts (verbatim from LongMemEval evaluate_qa.py) ----
def get_anscheck_prompt(task, question, answer, response, abstention=False):
    if not abstention:
        if task in ['single-session-user', 'single-session-assistant', 'multi-session']:
            template = "I will give you a question, a correct answer, and a response from a model. Please answer yes if the response contains the correct answer. Otherwise, answer no. If the response is equivalent to the correct answer or contains all the intermediate steps to get the correct answer, you should also answer yes. If the response only contains a subset of the information required by the answer, answer no. \n\nQuestion: {}\n\nCorrect Answer: {}\n\nModel Response: {}\n\nIs the model response correct? Answer yes or no only."
        elif task == 'temporal-reasoning':
            template = "I will give you a question, a correct answer, and a response from a model. Please answer yes if the response contains the correct answer. Otherwise, answer no. If the response is equivalent to the correct answer or contains all the intermediate steps to get the correct answer, you should also answer yes. If the response only contains a subset of the information required by the answer, answer no. In addition, do not penalize off-by-one errors for the number of days. If the question asks for the number of days/weeks/months, etc., and the model makes off-by-one errors (e.g., predicting 19 days when the answer is 18), the model's response is still correct. \n\nQuestion: {}\n\nCorrect Answer: {}\n\nModel Response: {}\n\nIs the model response correct? Answer yes or no only."
        elif task == 'knowledge-update':
            template = "I will give you a question, a correct answer, and a response from a model. Please answer yes if the response contains the correct answer. Otherwise, answer no. If the response contains some previous information along with an updated answer, the response should be considered as correct as long as the updated answer is the required answer.\n\nQuestion: {}\n\nCorrect Answer: {}\n\nModel Response: {}\n\nIs the model response correct? Answer yes or no only."
        elif task == 'single-session-preference':
            template = "I will give you a question, a rubric for desired personalized response, and a response from a model. Please answer yes if the response satisfies the desired response. Otherwise, answer no. The model does not need to reflect all the points in the rubric. The response is correct as long as it recalls and utilizes the user's personal information correctly.\n\nQuestion: {}\n\nRubric: {}\n\nModel Response: {}\n\nIs the model response correct? Answer yes or no only."
        else:
            raise NotImplementedError
    else:
        template = "I will give you an unanswerable question, an explanation, and a response from a model. Please answer yes if the model correctly identifies the question as unanswerable. The model could say that the information is incomplete, or some other information is given but the asked information is not.\n\nQuestion: {}\n\nExplanation: {}\n\nModel Response: {}\n\nDoes the model correctly identify the question as unanswerable? Answer yes or no only."
    return template.format(question, answer, response)


# ---- data ----
def load_subset(n):
    data = json.load(open(DATA, encoding="utf-8"))
    p = os.path.join(HERE, "subset_ids.json")
    if os.path.exists(p):
        ids = json.load(open(p))["ids"]
    else:
        rng = random.Random(42)
        by = collections.defaultdict(list)
        for d in data: by[d["question_type"]].append(d)
        N = len(data); tot = 50
        alloc = {t: max(1, round(tot * len(v) / N)) for t, v in by.items()}
        while sum(alloc.values()) > tot: alloc[max(alloc, key=alloc.get)] -= 1
        while sum(alloc.values()) < tot: alloc[max(alloc, key=alloc.get)] += 1
        pick = []
        for t, v in sorted(by.items()):
            v = sorted(v, key=lambda d: d["question_id"]); rng.shuffle(v)
            pick += v[:alloc[t]]
        absn = [d for d in pick if d["question_id"].endswith("_abs")]
        allabs = [d for d in data if d["question_id"].endswith("_abs")]
        while len(absn) < 4:
            cand = [d for d in allabs if d not in pick]; rng.shuffle(cand)
            c = cand[0]
            victim = next(d for d in pick if d["question_type"] == c["question_type"] and not d["question_id"].endswith("_abs"))
            pick[pick.index(victim)] = c; absn.append(c)
        ids = [d["question_id"] for d in pick]
        cnt = collections.Counter(d["question_type"] for d in pick)
        json.dump(dict(ids=ids, counts=dict(cnt), abstention=len(absn), data_file="longmemeval_s_cleaned.json (xiaowu0162/longmemeval-cleaned)", seed=42), open(p, "w"), indent=1)
    byid = {d["question_id"]: d for d in data}
    qs = [byid[i] for i in ids]
    if n < len(qs):
        rng = random.Random(1); qs = qs[:]; rng.shuffle(qs); qs = qs[:n]
    return qs


def ordered_sessions(q):
    return sorted(zip(q["haystack_dates"], q["haystack_session_ids"], q["haystack_sessions"]), key=lambda x: x[0])


def fmt_session(s):
    return "\n".join(f"{m['role']}: {m['content']}" for m in s)


ANS_TMPL = """You are answering a question about a user based on their past chat history with an assistant.

{ctx_note}

{ctx}

Current date: {date}
Question: {q}
Answer concisely. If the information needed is not present, say you don't know / the information was not provided."""


def answer(q, ctx_note, ctx):
    p = ANS_TMPL.format(ctx_note=ctx_note, ctx=ctx, date=q["question_date"], q=q["question"])
    return llm("answer", ANS_M, [{"role": "user", "content": p}], max_tokens=4096)


EXT_PROMPT = """Below is a chat session between a user and an AI assistant (session date: {date}). Extract atomic, self-contained facts worth remembering long-term: facts about the user, their preferences, events (with dates if mentioned), plans, and specific information the assistant gave (names, numbers, recommendations, lists). One fact per item, include concrete details. Output ONLY a JSON array of strings, no commentary.

SESSION:
{s}"""


def parse_facts(txt):
    m = re.search(r"\[.*\]", txt, re.S)
    if m:
        try:
            arr = json.loads(m.group(0))
            out = []
            for a in arr:
                if isinstance(a, str): out.append(a)
                elif isinstance(a, dict): out.append(" ".join(str(v) for v in a.values()))
            if out: return out
        except Exception:
            pass
    lines = [re.sub(r"^\s*(?:[-*]|\d+[.)])\s+", "", l).strip() for l in txt.splitlines() if re.match(r"^\s*(?:[-*]|\d+[.)])\s+", l)]
    if lines: return lines
    m = re.search(r"\{.*\}", txt, re.S)
    if m:
        try:
            d = json.loads(m.group(0)); out = []
            for v in d.values():
                if isinstance(v, list): out += [str(x) for x in v]
                else: out.append(str(v))
            return out
        except Exception:
            pass
    return None


def extract_session(date, sid, sess):
    txt = fmt_session(sess)
    if len(txt) > 60000: txt = txt[:60000]
    msgs = [{"role": "user", "content": EXT_PROMPT.format(date=date, s=txt)}]
    c, _ = llm("extract", EXT_M, msgs, max_tokens=4096, temperature=0, extra_body={"chat_template_kwargs": {"enable_thinking": False}})
    f = parse_facts(c)
    if f is None:
        STATS["extract_parse_fail"] += 1; f = []
    if not f: STATS["extract_empty"] += 1
    return [dict(fact=x, date=date, sid=sid) for x in f]


def tok(s): return re.findall(r"\w+", s.lower())


EXT_POOL = ThreadPoolExecutor(64)


def run_full(q):
    parts = [f"[Session date: {d}]\n{fmt_session(s)}" for d, _, s in ordered_sessions(q)]
    return answer(q, "Below is the complete chat history, ordered by time.", "\n\n".join(parts))


def run_brainbob(q):
    futs = [EXT_POOL.submit(extract_session, d, sid, s) for d, sid, s in ordered_sessions(q)]
    facts = [f for fu in futs for f in fu.result()]
    STATS["facts_total"] += len(facts)
    if not facts:
        return answer(q, "Memory is empty.", "(no memories)")
    bm = BM25Okapi([tok(f["fact"]) or ["_"] for f in facts])
    sc = bm.get_scores(tok(q["question"]))
    top = sorted(range(len(facts)), key=lambda i: -sc[i])[:40]
    sel = sorted((facts[i] for i in top), key=lambda f: f["date"])
    ctx = "\n".join(f"- [{f['date']}] (session {f['sid']}) {f['fact']}" for f in sel)
    note = "Below are retrieved memory facts extracted from the chat history, sorted by date. Newer facts override older ones when they conflict. If the memory doesn't contain the answer, say you don't know."
    return answer(q, note, ctx)


def judge(q, hyp):
    p = get_anscheck_prompt(q["question_type"], q["question"], q["answer"], hyp, abstention=q["question_id"].endswith("_abs"))
    c, _ = llm("judge", JUDGE_M, [{"role": "user", "content": p}], max_tokens=1024, temperature=0)
    cl = c.strip().lower()
    if re.search(r"\byes\b", cl) and not re.search(r"\bno\b", cl): return True, False
    if cl.startswith("yes"): return True, False
    if re.search(r"\bno\b", cl): return False, False
    STATS["judge_parse_fail"] += 1
    return False, True


def one(cond, q, t0, out):
    try:
        hyp, ctoks = (run_full if cond == "full" else run_brainbob)(q)
        ok, bad = judge(q, hyp)
        out.append(dict(cond=cond, qid=q["question_id"], qtype=q["question_type"], abs=q["question_id"].endswith("_abs"),
                        hyp=hyp, ctx_tokens=ctoks, correct=ok, judge_parse_fail=bad, t=time.time() - t0))
    except Exception as e:
        STATS["exception"] += 1
        print("ERR", cond, q["question_id"], type(e).__name__, str(e)[:200].replace(KEY, "***"), file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--conditions", default="full,brainbob")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--deadline-min", type=float, default=600)
    a = ap.parse_args()
    n = 3 if a.smoke else a.n
    conds = a.conditions.split(",")
    qs = load_subset(n)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + ("-smoke" if a.smoke else "")
    rd = os.path.join(HERE, "results", ts); os.makedirs(rd)
    t0 = time.time()
    out = []
    pool = ThreadPoolExecutor(len(qs) * len(conds) + 1)
    futs = [pool.submit(one, c, q, t0, out) for c in conds for q in qs]
    done, notdone = wait(futs, timeout=a.deadline_min * 60)
    wall = time.time() - t0
    rows = {}
    for c in conds:
        r = [x for x in out if x["cond"] == c]

        def acc(f):
            s = [x for x in r if f(x)]
            return (sum(x["correct"] for x in s), len(s))
        types = sorted({x["qtype"] for x in r})
        rows[c] = dict(n=len(r), overall=acc(lambda x: True), abstention=acc(lambda x: x["abs"]),
                       by_type={t: acc(lambda x, t=t: x["qtype"] == t) for t in types},
                       avg_ctx_tokens=round(sum(x["ctx_tokens"] for x in r) / max(1, len(r))),
                       wall_s=round(max([x["t"] for x in r] or [0])),
                       judge_parse_fail=sum(x["judge_parse_fail"] for x in r))
    cost = collections.defaultdict(lambda: dict(pt=0, ct=0, usd=0.0))
    for u in list(USAGE):
        k = u["stage"]; pi, po = PRICE[u["model"]]
        cost[k]["pt"] += u["pt"]; cost[k]["ct"] += u["ct"]; cost[k]["usd"] += (u["pt"] * pi + u["ct"] * po) / 1e6
    total = sum(v["usd"] for v in cost.values())
    summ = dict(n_requested=len(qs), conditions=rows, cost=cost, total_usd=round(total, 4), stats=dict(STATS), wall_s=round(wall), unfinished=len(notdone),
                note="cost counts cached calls too (usage replayed)")
    json.dump(summ, open(os.path.join(rd, "summary.json"), "w"), indent=1)
    with open(os.path.join(rd, "predictions.jsonl"), "w", encoding="utf-8") as f:
        for x in out: f.write(json.dumps(dict(cond=x["cond"], question_id=x["qid"], hypothesis=x["hyp"], ctx_tokens=x["ctx_tokens"]), ensure_ascii=False) + "\n")
    with open(os.path.join(rd, "judgments.jsonl"), "w") as f:
        for x in out: f.write(json.dumps(dict(cond=x["cond"], question_id=x["qid"], qtype=x["qtype"], abstention=x["abs"], correct=x["correct"], judge_parse_fail=x["judge_parse_fail"])) + "\n")
    P = lambda t: f"{t[0]}/{t[1]} ({100*t[0]/max(1,t[1]):.0f}%)"
    types = sorted({x["qtype"] for x in out})
    L = [f"# LongMemEval_S results ({ts})", "",
         "Judge: official LongMemEval prompts, but official uses GPT-4o; here judge is openai/gpt-oss-120b (temp 0). Answer model Nemotron-3-Super-120B; extraction Nemotron-3.5-Lightning-30B (thinking off); retrieval BM25 top-40.",
         f"Requested n={len(qs)} per condition; unfinished tasks at report time: {len(notdone)}. Wall total {wall:.0f}s.", "",
         "| condition | n | overall | abstention | " + " | ".join(types) + " | avg ctx tokens | wall s |",
         "|" + "---|" * (6 + len(types))]
    for c, r in rows.items():
        L.append(f"| {c} | {r['n']} | {P(r['overall'])} | {P(r['abstention'])} | " + " | ".join(P(r['by_type'].get(t, (0, 0))) for t in types) + f" | {r['avg_ctx_tokens']} | {r['wall_s']} |")
    L += ["", "| stage | prompt tok | completion tok | USD |", "|---|---|---|---|"]
    for k, v in cost.items(): L.append(f"| {k} | {v['pt']} | {v['ct']} | {v['usd']:.3f} |")
    L.append(f"| total | | | {total:.3f} |")
    L += ["", f"Stats: {dict(STATS)}"]
    open(os.path.join(rd, "results.md"), "w", encoding="utf-8").write("\n".join(L))
    print("\n".join(L)); print("DIR", rd)
    sys.stdout.flush(); os._exit(0)


main()
