"""Synthetic pairwise memory-operation data for the maintain.py judge (issue #7).

Stages (one command runs all; cached, so re-running is free):
  1. stories : freeze story/template ids and the train/dev split BEFORE any wording exists (stories.json).
               Dev uses templates that never appear in train, and its own entity/company/person pools.
  2. generate: teacher writes one existing memory + three candidates (same / conflict / unrelated) per story.
  3. check   : teacher labels every pair blind with the production judge prompt; disagreements go to review_queue.jsonl.
  4. finalize: apply label_overrides.json (manual review), validate, dedupe, balance, write train.jsonl / dev.jsonl
               and manifest.json.

Every pair's judge input is built with the exact system prompt and user string of maintain.llm_judge, so a
model trained on it can be passed to maintain.ingest(judge=...) unchanged.

Usage:  backend/.venv/Scripts/python experiments/memops-small/gen_data.py [--train 150 --dev 30]
"""
import argparse, collections, concurrent.futures as cf, hashlib, json, os, random, re, sys, time
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "backend"))
from brainbob.maintain import PROMPT as JUDGE_PROMPT  # production judge prompt: used only for the teacher's blind check
sys.path.insert(0, HERE)
import bob_format  # the model input format of Jerel's Bob benchmark: what train/dev rows contain

TEACHER = "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B"
PRICE_PER_M = (0.30, 2.40)  # Crusoe USD per 1M input / output tokens (same table as backend/brainbob/llm.py)
BASE_URL = "https://api.inference.crusoecloud.com/v1"
SEED = 42
LABELS = ("same", "conflict", "unrelated")
CACHE = os.path.join(HERE, ".cache")

# (template_id, domain, attribute) -- the split is by template, so no train/dev siblings share one.
TEMPLATES = [
    ("t01", "product launch", "launch date"), ("t02", "pricing", "monthly price of a plan"),
    ("t03", "hiring", "number of open headcount"), ("t04", "vendor contract", "contract renewal date"),
    ("t05", "office", "office move-in date"), ("t06", "infrastructure", "primary cloud region"),
    ("t07", "budget", "quarterly marketing budget"), ("t08", "customer account", "account owner"),
    ("t09", "security policy", "password rotation period"), ("t10", "company offsite", "offsite location"),
    ("t11", "release engineering", "code freeze date"), ("t12", "support", "first-response SLA"),
    ("t13", "sales", "quarterly sales quota"), ("t14", "partnership", "partner revenue share"),
    ("t15", "legal", "contract signatory"), ("t16", "data platform", "data retention period"),
    ("t17", "mobile app", "minimum supported OS version"), ("t18", "payroll", "payroll run day"),
    ("t19", "procurement", "approved laptop model"), ("t20", "events", "conference booth number"),
    ("t21", "engineering", "on-call rotation length"), ("t22", "finance", "fiscal year end"),
    ("t23", "customer pilot", "pilot deadline"), ("t24", "marketing", "campaign launch channel"),
    ("t25", "HR policy", "remote work days per week"), ("t26", "API", "rate limit per minute"),
    ("t27", "research", "experiment sample size"), ("t28", "operations", "warehouse shipping cutoff time"),
    ("t29", "travel policy", "hotel nightly cap"), ("t30", "fundraising", "target raise amount"),
    ("t31", "product roadmap", "feature owner"), ("t32", "compliance", "audit date"),
    ("t33", "infrastructure", "database version"), ("t34", "sales", "discount ceiling"),
    ("t35", "recruiting", "interview loop length"), ("t36", "customer success", "renewal price"),
    ("t37", "design", "brand primary color"), ("t38", "IT", "VPN provider"),
    ("t39", "board", "board meeting date"), ("t40", "logistics", "default courier"),
    ("t41", "training", "onboarding program length"), ("t42", "benefits", "annual learning stipend"),
]
N_DEV_TEMPLATES = 6

SAME = {"paraphrase": "restate the identical fact (same subject, attribute and value) with clearly different wording and sentence structure",
        "format_change": "the same value written in a different format or unit (e.g. 2026-11-03 vs 'Nov 3rd', '$1.2M' vs '1.2 million dollars', '2 weeks' vs '14 days')",
        "restated_negation": "make the EXISTING memory a negative fact (something will NOT happen / is NOT allowed / is NOT used); the candidate restates that same negative fact in other words",
        "attributed_restatement": "the same fact and value, attributed to who said or confirmed it, adding nothing materially new"}
CONFLICT = {"value_change": "same subject and attribute, plainly states a different current value",
            "negation_reversal": "same subject and attribute, negates or reverses the existing claim (e.g. 'will not', 'no longer', 'cancelled')",
            "hedged_new_value": "ambiguous evidence: a hedged or unconfirmed suggestion of a DIFFERENT value for the same attribute ('might move to', 'I heard it is probably')",
            "explicit_update": "explicitly says the value changed ('as of this week', 'moved to', 'now', 'updated to') to a different current value"}
UNRELATED = {"similar_wording_different_entity": "nearly the same wording and attribute but about a DIFFERENT entity (a sibling project, another office, another quarter, another customer); any value",
             "different_attribute_same_entity": "the same entity but a different attribute (not the one in the existing memory)",
             "historical_original_value": "explicitly about a past or original value ('was originally', 'previously', 'last year it was') that differs from the existing value, without claiming the current value changed",
             "vague_no_value": "ambiguous evidence: same topic but states no specific value and does not contradict the existing memory (e.g. 'the team is still reviewing the timeline')",
             "compatible_extra_detail": "a compatible new fact about the same entity that neither restates nor changes the existing value"}
PHEN = {"same": SAME, "conflict": CONFLICT, "unrelated": UNRELATED}

POOLS = {
    "train": dict(companies=["Rusty Rod", "Lumen Labs", "Northwind Foods", "Quarry Systems", "Bluefin Health", "Copperleaf", "Halcyon Bank", "Tidewater Logistics"],
                  entities=["Atlas", "Borealis", "Cedar", "Driftwood", "Ember", "Falcon", "Granite", "Harbor", "Iris", "Juniper", "Kestrel", "Lantern", "Meridian", "Nimbus", "Orchid", "Pioneer"],
                  people=["Maya Chen", "Diego Alvarez", "Priya Nair", "Tom Becker", "Aisha Bello", "Kenji Sato", "Laura Rossi", "Omar Haddad", "Sofia Lind", "Ravi Kumar", "Grace Okafor", "Ben Walsh"]),
    "dev": dict(companies=["Starling Robotics", "Mosaic Media", "Glacier Insurance"],
                entities=["Quasar", "Redwood", "Saffron", "Topaz", "Umber", "Vesper"],
                people=["Elena Petrova", "Marcus Hill", "Yuki Tanaka", "Fatima Zahra", "Noah Klein", "Ines Duarte"]),
}

GEN = """You write synthetic data for a classifier that maintains a company's shared memory notes.
Company: {company}. Topic: {domain}. Attribute: {attribute}. Main entity: {entity}. People you may mention: {people}.
The EXISTING memory was written on {d0}; the NEW candidates were written on {d1}.

Write ONE existing memory: a single atomic fact (one sentence, 8-30 words) with a concrete subject, the attribute above and a specific value, like a note extracted from a chat or meeting.
Then write THREE new candidate memories. Each candidate is compared ALONE against the existing memory:
1. "same" - {ps}: {psd}
2. "conflict" - {pc}: {pcd}
3. "unrelated" - {pu}: {pud}

Label definitions (follow exactly):
- same: the candidate states the same fact with the same value; it adds nothing materially new.
- conflict: same subject and attribute, but a different current value (different date, number, owner, choice, or a reversal/negation). Hedged suggestions of a different value still count as conflict.
- unrelated: different subject or attribute, or compatible information that can both be true. A statement explicitly about a past or original value is not a conflict.

Rules: each candidate is one self-contained sentence (8-35 words) written like an extracted fact; never refer to "the existing memory" or the labels; use realistic specifics; fictional names only.
Reply with JSON only: {{"existing": "...", "candidates": [{{"label": "same", "text": "..."}}, {{"label": "conflict", "text": "..."}}, {{"label": "unrelated", "text": "..."}}]}}"""


def judge_user(mem_date, mem_text, cand_date, cand_text):
    """Exactly the user message maintain.llm_judge sends."""
    return f"EXISTING memory ({mem_date}): {mem_text}\n\nNEW candidate ({cand_date}): {cand_text}"


def target(label): return json.dumps({"verdict": label}, separators=(",", ":"))


# ---------------- teacher client (OpenAI-compatible, Crusoe), disk cache, usage ----------------
_client, USAGE = None, collections.Counter()


def call(messages, temperature, max_tokens=700):
    global _client
    payload = json.dumps([TEACHER, messages, temperature, max_tokens, SEED], sort_keys=True)
    path = os.path.join(CACHE, hashlib.sha256(payload.encode()).hexdigest() + ".json")
    if os.path.exists(path):
        d = json.load(open(path, encoding="utf8")); USAGE["cached_calls"] += 1
        USAGE["pt"] += d["pt"]; USAGE["ct"] += d["ct"]; USAGE["calls"] += 1
        return d["content"]
    if _client is None:
        from openai import OpenAI
        key = open(os.path.expanduser("~/.config/crusoe/api.key")).read().strip()
        _client = OpenAI(api_key=key, base_url=BASE_URL, timeout=300, max_retries=0)
    import openai
    delay = 2
    for attempt in range(10):
        try:
            r = _client.chat.completions.create(model=TEACHER, messages=messages, temperature=temperature, max_tokens=max_tokens,
                                                seed=SEED, extra_body={"chat_template_kwargs": {"enable_thinking": False}})
            break
        except (openai.RateLimitError, openai.APIConnectionError, openai.APITimeoutError, openai.InternalServerError):
            USAGE["retries"] += 1; time.sleep(delay); delay = min(delay * 2, 30)
    else:
        return ""
    c = (r.choices[0].message.content or "")
    if "</think>" in c: c = c.split("</think>")[-1]
    c = c.strip()
    os.makedirs(CACHE, exist_ok=True)
    json.dump(dict(content=c, pt=r.usage.prompt_tokens, ct=r.usage.completion_tokens), open(path, "w", encoding="utf8"))
    USAGE["pt"] += r.usage.prompt_tokens; USAGE["ct"] += r.usage.completion_tokens; USAGE["calls"] += 1; USAGE["fresh_calls"] += 1
    return c


def first_json(t):
    t = re.sub(r"```[a-zA-Z]*", " ", t or "")
    i = t.find("{")
    if i < 0: return None
    try: return json.JSONDecoder().raw_decode(t[i:])[0]
    except ValueError: return None


# ---------------- 1. stories ----------------
def make_stories(n_train, n_dev):
    rng = random.Random(SEED)
    tids = [t[0] for t in TEMPLATES]; rng.shuffle(tids)
    dev_t, train_t = sorted(tids[:N_DEV_TEMPLATES]), sorted(tids[N_DEV_TEMPLATES:])
    tmap = {t[0]: t for t in TEMPLATES}
    out = []
    for split, pool_t, n in (("train", train_t, n_train), ("dev", dev_t, n_dev)):
        P = POOLS[split]
        for i in range(n):
            tid = pool_t[i % len(pool_t)]
            d0 = date(2026, 1, 5) + timedelta(days=rng.randrange(0, 240))
            gap = rng.randrange(1, 60)
            d1 = d0 + timedelta(days=gap) if rng.random() > 0.15 else d0 - timedelta(days=gap)  # some candidates are older
            out.append(dict(story_id=f"{split[:2]}{i:03d}", split=split, template_id=tid, domain=tmap[tid][1], attribute=tmap[tid][2],
                            company=rng.choice(P["companies"]), entity=rng.choice(P["entities"]), people=rng.sample(P["people"], 2),
                            d0=d0.isoformat(), d1=d1.isoformat(),
                            phen={lab: rng.choice(sorted(PHEN[lab])) for lab in LABELS},
                            authority=rng.choice(["approved", "approved", "tentative", "discussion"]),
                            existing_origin=f"ep-{split[:2]}{i:03d}-a", candidate_source=f"ep-{split[:2]}{i:03d}-b"))
    return out, train_t, dev_t


# ---------------- 2. generate ----------------
def gen_prompt(s):
    p = s["phen"]
    return GEN.format(company=s["company"], domain=s["domain"], attribute=s["attribute"], entity=s["entity"],
                      people=", ".join(s["people"]), d0=s["d0"], d1=s["d1"],
                      ps=p["same"], psd=SAME[p["same"]], pc=p["conflict"], pcd=CONFLICT[p["conflict"]],
                      pu=p["unrelated"], pud=UNRELATED[p["unrelated"]])


def generate(s):
    d = first_json(call([{"role": "user", "content": gen_prompt(s)}], temperature=0.8))
    if not isinstance(d, dict) or not isinstance(d.get("existing"), str) or not isinstance(d.get("candidates"), list): return []
    rows = []
    for c in d["candidates"]:
        if not isinstance(c, dict) or c.get("label") not in LABELS or not isinstance(c.get("text"), str): continue
        lab = c["label"]
        rows.append(dict(id=f"{s['story_id']}-{lab}", story_id=s["story_id"], template_id=s["template_id"], split=s["split"],
                         phenomenon=s["phen"][lab], teacher_label=lab,
                         existing=dict(text=d["existing"].strip(), date=s["d0"], origin=s["existing_origin"], status="trial", authority="approved"),
                         candidate=dict(text=c["text"].strip(), date=s["d1"], source=s["candidate_source"], authority=s["authority"])))
    return rows


# ---------------- 3. blind check with the production judge prompt ----------------
def messages_for(r):
    return [{"role": "system", "content": JUDGE_PROMPT},
            {"role": "user", "content": judge_user(r["existing"]["date"], r["existing"]["text"], r["candidate"]["date"], r["candidate"]["text"])}]


def blind(r):
    out = call(messages_for(r), temperature=0.0, max_tokens=200)
    d = first_json(out)
    v = str(d.get("verdict", "")).strip().lower() if isinstance(d, dict) else ""
    return v if v in LABELS else None, (d.get("reason", "") if isinstance(d, dict) else out[:200])


def _norm(t): return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", t.lower())).strip()


def sha(path): return hashlib.sha256(open(path, "rb").read()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", type=int, default=150); ap.add_argument("--dev", type=int, default=30)
    ap.add_argument("--surplus", type=float, default=1.25, help="generate this many times the needed stories")
    a = ap.parse_args()
    t0 = time.time()
    n_tr, n_dv = int(a.train / 3 * a.surplus) + 1, int(a.dev / 3 * a.surplus) + 1
    sp = os.path.join(HERE, "stories.json")
    stories, train_t, dev_t = make_stories(n_tr, n_dv)
    json.dump(dict(seed=SEED, train_templates=train_t, dev_templates=dev_t, stories=stories), open(sp, "w", encoding="utf8"), indent=1)
    assert not set(train_t) & set(dev_t)

    with cf.ThreadPoolExecutor(6) as ex: rows = [r for rs in ex.map(generate, stories) for r in rs]
    with cf.ThreadPoolExecutor(6) as ex: checks = list(ex.map(blind, rows))
    for r, (v, why) in zip(rows, checks): r["teacher_blind"], r["teacher_blind_reason"] = v, why

    # review queue: blind label disagrees with the label the teacher was asked to write
    with open(os.path.join(HERE, "review_queue.jsonl"), "w", encoding="utf8") as f:
        for r in rows:
            if r["teacher_blind"] != r["teacher_label"]: f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # finalize: manual overrides, validation, dedupe, balance
    ovp = os.path.join(HERE, "label_overrides.json")
    overrides = json.load(open(ovp, encoding="utf8")) if os.path.exists(ovp) else {}
    seen, final, dropped = set(), collections.defaultdict(list), collections.Counter()
    for r in rows:
        o = overrides.get(r["id"], {})
        if o.get("drop"): dropped["review_drop"] += 1; continue
        r["label"] = o.get("label", r["teacher_label"])
        r["label_source"] = "manual_review" if "label" in o else ("teacher" if r["teacher_blind"] == r["teacher_label"] else "teacher_unreviewed_disagreement")
        if o: r["review_note"] = o.get("why", "")
        e, c = r["existing"]["text"], r["candidate"]["text"]
        key = (_norm(e), _norm(c))
        if not e or not c or _norm(e) == _norm(c): dropped["empty_or_identical"] += 1; continue
        if key in seen: dropped["duplicate"] += 1; continue
        if len(e) + len(c) > 900: dropped["too_long"] += 1; continue
        seen.add(key)
        r["target"] = target(r["label"])
        final[(r["split"], r["label"])].append(r)
    need = {"train": a.train // 3, "dev": a.dev // 3}
    rng = random.Random(SEED)
    for split in ("train", "dev"):
        out = []
        for lab in LABELS:
            pool = sorted(final[(split, lab)], key=lambda r: r["id"])
            # prefer reviewed / agreed rows, then deterministic shuffle
            pool.sort(key=lambda r: r["label_source"] == "teacher_unreviewed_disagreement")
            head = [r for r in pool if r["label_source"] != "teacher_unreviewed_disagreement"]
            rest = [r for r in pool if r["label_source"] == "teacher_unreviewed_disagreement"]
            rng.shuffle(head); rng.shuffle(rest)
            out += (head + rest)[:need[split]]
        rng.shuffle(out)
        prefix = {"train": "train", "dev": "syn"}[split]
        for n, r in enumerate(out, 1):  # Bob benchmark input format, exactly (ids, field order, system prompt)
            r["source_row"] = r["id"]; r["id"] = f"{prefix}-{n:03d}"
            r["existing"]["id"] = f"m-{n:03d}"; r["candidate"]["source_id"] = f"s-{n:03d}"
            r["messages"] = bob_format.messages(r["id"], r["existing"], r["candidate"])
            r["input_sha256"] = bob_format.input_hash(r["id"], r["existing"], r["candidate"])
        with open(os.path.join(HERE, f"{split}.jsonl"), "w", encoding="utf8") as f:
            for r in out: f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(split, len(out), collections.Counter(r["label"] for r in out), collections.Counter(r["label_source"] for r in out))
    pt, ct = USAGE["pt"], USAGE["ct"]
    man = dict(model_input_format=f"Bob benchmark messages (bob_format.py, codex/bob-benchmark@{bob_format.BOB_COMMIT})",
               bob_isolation="generated from this file's own templates before the Bob export was seen; no bobbench/ or benchmarks/bob/ eval content used",
               teacher_model=TEACHER, endpoint=BASE_URL, seed=SEED, thinking=False,
               generation_prompt=GEN, generation_temperature=0.8, check_prompt="backend/brainbob/maintain.py PROMPT (verbatim) + llm_judge user string",
               check_system_prompt=JUDGE_PROMPT, check_temperature=0.0, phenomena=PHEN,
               train_templates=train_t, dev_templates=dev_t, split_rule="split by template id before any wording; dev uses disjoint templates and entity/company/person pools",
               target_format='{"verdict":"same|conflict|unrelated"} (compact, no reason)',
               note_source_refs="model input carries existing.id and candidate.source_id (Bob format); origin/source episode ids kept as metadata",
               usage=dict(calls=USAGE["calls"], fresh_calls=USAGE["fresh_calls"], cached_calls=USAGE["cached_calls"], prompt_tokens=pt, completion_tokens=ct),
               price_basis_usd_per_1M=dict(input=PRICE_PER_M[0], output=PRICE_PER_M[1], source="Crusoe list price as in backend/brainbob/llm.py PRICE"),
               cost_usd_all_calls=round((pt * PRICE_PER_M[0] + ct * PRICE_PER_M[1]) / 1e6, 4),
               generated_rows=len(rows), dropped=dict(dropped), overrides=len(overrides),
               sha256={f: sha(os.path.join(HERE, f)) for f in ("train.jsonl", "dev.jsonl", "stories.json")},
               elapsed_s=round(time.time() - t0, 1))
    json.dump(man, open(os.path.join(HERE, "manifest.json"), "w", encoding="utf8"), indent=1)
    print("usage", dict(USAGE), "cost_usd", man["cost_usd_all_calls"], "review_queue", sum(1 for r in rows if r["teacher_blind"] != r["teacher_label"]))


if __name__ == "__main__":
    main()
