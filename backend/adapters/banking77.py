"""BANKING77: 77-way intent classification. Train and heldout tasks are stratified by label, fixed seed."""
import collections, csv, os, random, re
from brainbob.types import Task

NAME = "banking77"
DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
MARK = "\n\nLabels:"  # everything from here on is the label list (not part of the search query)


def _rows(fn):
    return [(r["text"], r["category"]) for r in csv.DictReader(open(os.path.join(DATA, fn), encoding="utf-8"))]


def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip().strip("`*\"'. ").replace("-", "_")).lower()


def _sample(rows, n, rng):
    by = collections.defaultdict(list)
    for r in rows: by[r[1]].append(r)
    for v in by.values(): rng.shuffle(v)
    labs = sorted(by); rng.shuffle(labs)
    out, i = [], 0
    while len(out) < n and any(by.values()):
        v = by[labs[i % len(labs)]]
        if v: out.append(v.pop())
        i += 1
    rng.shuffle(out)
    return out


def stream(seed=42, n_train=60, n_heldout=60):
    rng = random.Random(seed)
    train, test = _rows("banking77_train.csv"), _rows("banking77_test.csv")
    labels = sorted({c for _, c in train})
    lab = ", ".join(labels)

    def mk(kind, rows, ref):
        out = []
        for i, (t, c) in enumerate(rows):
            q = (f"Classify this customer banking message into exactly one intent label.\n\nMessage: {t}{MARK} {lab}\n\n"
                 "Reply with only the label, exactly as written in the list.")
            out.append(Task(f"b77-{kind}-{i}", q, (lambda a, c=c: norm(a) == norm(c)), reference=c if ref else None))
        return out
    return mk("train", _sample(train, n_train, rng), True), mk("held", _sample(test, n_heldout, rng), False)
