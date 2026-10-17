"""Game of 24 (Tree-of-Thoughts 24.csv, 1362 puzzles). Dynamic Cheatsheet's data dir has no 24 file, so ToT is used.
Source: github.com/princeton-nlp/tree-of-thought-llm src/tot/data/24/24.csv. Deterministic grade, no eval(), no models."""
import csv, itertools, os, random, re, urllib.request
from fractions import Fraction
try:
    from brainbob.types import Task
except Exception:  # pragma: no cover
    Task = None

NAME = "game24"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "data", "game24", "24.csv")
URL = "https://raw.githubusercontent.com/princeton-nlp/tree-of-thought-llm/master/src/tot/data/24/24.csv"
EPS = 1e-6


def _tokens(s):
    s = s.replace("×", "*").replace("÷", "/").replace("−", "-")
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c.isspace():
            i += 1
        elif c.isdigit() or (c == "." and i + 1 < len(s) and s[i + 1].isdigit()):
            j = i
            while j < len(s) and (s[j].isdigit() or s[j] == "."):
                j += 1
            out.append(("n", s[i:j])); i = j
        elif c in "+-*/()":
            out.append((c, c)); i += 1
        else:
            raise ValueError("bad char " + c)
    return out


def evaluate(expr):
    """-> (value Fraction, [numbers used]). Only numbers, + - * / and parens; exact arithmetic (no float error)."""
    toks, pos, used = _tokens(expr), [0], []

    def peek():
        return toks[pos[0]][0] if pos[0] < len(toks) else None

    def eat():
        pos[0] += 1
        return toks[pos[0] - 1]

    def atom():
        k = peek()
        if k == "n":
            v = eat()[1]; used.append(v); return Fraction(v)
        if k == "(":
            eat(); v = add()
            if peek() != ")":
                raise ValueError("missing )")
            eat(); return v
        if k == "-":
            eat(); return -atom()
        raise ValueError("unexpected token")

    def mul():
        v = atom()
        while peek() in ("*", "/"):
            op = eat()[0]; r = atom()
            if op == "*":
                v *= r
            else:
                if r == 0:
                    raise ZeroDivisionError("division by zero")
                v /= r
        return v

    def add():
        v = mul()
        while peek() in ("+", "-"):
            op = eat()[0]; r = mul(); v = v + r if op == "+" else v - r
        return v

    v = add()
    if pos[0] != len(toks):
        raise ValueError("trailing tokens")
    return v, used


def check(expr, nums):
    try:
        v, used = evaluate(expr)
    except (ValueError, ZeroDivisionError):
        return False
    if sorted(Fraction(u) for u in used) != sorted(Fraction(n) for n in nums):
        return False
    return abs(float(v) - 24) < EPS


def extract(text):
    """Candidate expressions from the last line that has one (strips markdown/LaTeX, drops '= 24' tail)."""
    t = (text or "").replace("\\times", "*").replace("\\div", "/").replace("\\cdot", "*")
    t = re.sub(r"\\[()\[\]]|\\boxed\{|\\left|\\right", " ", t).replace("$", " ").replace("`", " ").replace("**", " ")
    cands = []
    for line in reversed([l for l in t.splitlines() if l.strip()]):
        line = re.sub(r"(?i)^.*?(answer|expression|solution|final)[^:=]*:", "", line)
        for seg in re.findall(r"[0-9().+\-*/×÷−\s=]*[0-9)][0-9().+\-*/×÷−\s=]*", line):
            seg = seg.strip()
            if "=" in seg:  # keep the side(s) that contain operators
                for part in seg.split("="):
                    part = part.strip()
                    if re.search(r"\d\s*[-+*/×÷−]|[-+*/]\s*[\d(]", part):
                        cands.append(part)
            elif re.search(r"\d\s*[-+*/×÷−]|\)\s*[-+*/]|[-+*/]\s*[\d(]", seg):
                cands.append(seg)
        if cands:
            break
    return cands


def solve(nums):
    for perm in sorted(set(itertools.permutations(nums))):
        for o1, o2, o3 in itertools.product("+-*/", repeat=3):
            a, b, c, d = perm
            for e in (f"(({a}{o1}{b}){o2}{c}){o3}{d}", f"({a}{o1}({b}{o2}{c})){o3}{d}", f"({a}{o1}{b}){o2}({c}{o3}{d})",
                      f"{a}{o1}(({b}{o2}{c}){o3}{d})", f"{a}{o1}({b}{o2}({c}{o3}{d}))"):
                try:
                    if abs(float(evaluate(e)[0]) - 24) < EPS:
                        return e
                except ZeroDivisionError:
                    pass
    return None


def _puzzles():
    if not os.path.exists(PATH):
        os.makedirs(os.path.dirname(PATH), exist_ok=True); urllib.request.urlretrieve(URL, PATH)
    with open(PATH, encoding="utf8") as f:
        return [r["Puzzles"].split() for r in csv.DictReader(f)]


def _task(i, nums):
    q = (f"Use the four numbers {', '.join(nums)} and basic arithmetic operations (+, -, *, /) and parentheses to obtain 24. "
         "Use each number exactly once. Give the final expression.")
    ref = solve(nums) or "any valid expression"
    kw = dict(id=f"game24-{i}", question=q, grade=lambda a, _n=tuple(nums): any(check(c, _n) for c in extract(a)))
    try:
        return Task(**kw, reference=ref)
    except TypeError:
        t = Task(**kw); t.reference = ref; return t


def stream(seed=42, n_train=60, n_heldout=60):
    ps = _puzzles()
    idx = list(range(len(ps))); random.Random(seed).shuffle(idx)
    tr, he = idx[:n_train], idx[n_train:n_train + n_heldout]
    return [_task(i, ps[i]) for i in tr], [_task(i, ps[i]) for i in he]
