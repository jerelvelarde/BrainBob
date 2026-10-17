"""LoCoMo adapter: one memory space per conversation; audit/heldout split (locomo_split.json).
Categories: 1 multi-hop, 2 temporal, 3 open-domain, 4 single-hop, 5 adversarial (excluded from the split)."""
import json, os, random, re, urllib.request
from brainbob import llm
from brainbob.types import Episode, Task

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "https://raw.githubusercontent.com/snap-research/locomo/main/data/locomo10.json"
DATA = os.path.join(ROOT, "data", "locomo10.json")
SPLIT = os.path.join(ROOT, "locomo_split.json")
CATS = {1: "multi-hop", 2: "temporal", 3: "open-domain", 4: "single-hop", 5: "adversarial"}
_data = None

JUDGE = """Your task is to label an answer to a question as CORRECT or WRONG. You will be given a question, a gold (ground truth) answer, and a generated answer.
The generated answer may be longer, but count it as CORRECT if it touches on the same topic or contains the gold answer's information, even if worded differently. For time questions, a different date format referring to the same date or period is CORRECT. If it contradicts the gold answer, misses it, or says it doesn't know, it is WRONG.

Question: {q}
Gold answer: {g}
Generated answer: {a}

Output only one word: CORRECT or WRONG."""


def load():
    global _data
    if _data is None:
        if not os.path.exists(DATA):
            os.makedirs(os.path.dirname(DATA), exist_ok=True); urllib.request.urlretrieve(URL, DATA)
        _data = json.load(open(DATA, encoding="utf8"))
    return _data


def judge(question, gold, answer):
    c = llm.complete("judge", [{"role": "user", "content": JUDGE.format(q=question, g=gold, a=answer)}], max_tokens=1024)
    m = re.findall(r"\b(CORRECT|WRONG)\b", c.upper())
    return bool(m) and m[-1] == "CORRECT"


def conversations(n=None):
    """-> [(conv_id, [Episode per session])]"""
    out = []
    for conv in load()[:n]:
        c, sid0 = conv["conversation"], conv["sample_id"]
        nums = sorted(int(m.group(1)) for k in c if (m := re.fullmatch(r"session_(\d+)", k)))
        eps = [Episode(f"{sid0}:session_{k}", "\n".join(f"{t['speaker']} ({t['dia_id']}): {t['text']}" for t in c[f"session_{k}"]),
                       c.get(f"session_{k}_date_time") or "", f"{sid0}:session_{k}") for k in nums]
        out.append((sid0, eps))
    return out


def category(task_id):
    conv_id, i = task_id.rsplit(":q", 1)
    return CATS[next(c for c in load() if c["sample_id"] == conv_id)["qa"][int(i)]["category"]]


def tasks(conv_id, split, judge_fn=judge, limit=None, seed=7):
    """Tasks of one conversation for 'audit' or 'heldout'; limit samples that many (fixed seed)."""
    want = {i for i in json.load(open(SPLIT))[split] if i.startswith(conv_id + ":")}
    conv = next(c for c in load() if c["sample_id"] == conv_id)
    out = []
    for i, q in enumerate(conv["qa"]):
        tid = f"{conv_id}:q{i}"
        if tid in want:
            gold = str(q.get("answer", q.get("adversarial_answer", "")))
            out.append(Task(tid, q["question"], lambda a, qq=q["question"], g=gold: judge_fn(qq, g, a)))
    if limit and limit < len(out):
        out = random.Random(seed).sample(out, limit)
    return out
