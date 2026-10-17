"""DDXPlus (StreamBench version): diagnose from a patient profile, pick one of 49 pathologies.
Source: HF appier-ai-research/StreamBench, config ddxplus; prompt/parse from github.com/stream-bench/stream-bench
(stream_bench/benchmarks/ddxplus.py). Train pool = validate split, heldout pool = test split. No model calls."""
import os, random, re, urllib.request
from collections import defaultdict
try:
    from brainbob.types import Task
except Exception:  # pragma: no cover
    Task = None

NAME = "ddxplus"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "ddxplus")
BASE = "https://huggingface.co/datasets/appier-ai-research/StreamBench/resolve/main/ddxplus/%s-00000-of-00001.parquet"

LABELS = ['Acute COPD exacerbation / infection', 'Acute dystonic reactions', 'Acute laryngitis', 'Acute otitis media',
    'Acute pulmonary edema', 'Acute rhinosinusitis', 'Allergic sinusitis', 'Anaphylaxis', 'Anemia', 'Atrial fibrillation',
    'Boerhaave', 'Bronchiectasis', 'Bronchiolitis', 'Bronchitis', 'Bronchospasm / acute asthma exacerbation', 'Chagas',
    'Chronic rhinosinusitis', 'Cluster headache', 'Croup', 'Ebola', 'Epiglottitis', 'GERD', 'Guillain-Barré syndrome',
    'HIV (initial infection)', 'Influenza', 'Inguinal hernia', 'Larygospasm', 'Localized edema', 'Myasthenia gravis',
    'Myocarditis', 'PSVT', 'Pancreatic neoplasm', 'Panic attack', 'Pericarditis', 'Pneumonia', 'Possible NSTEMI / STEMI',
    'Pulmonary embolism', 'Pulmonary neoplasm', 'SLE', 'Sarcoidosis', 'Scombroid food poisoning', 'Spontaneous pneumothorax',
    'Spontaneous rib fracture', 'Stable angina', 'Tuberculosis', 'URTI', 'Unstable angina', 'Viral pharyngitis', 'Whooping cough']
OPTIONS = "\n".join(f"{i}. {v}" for i, v in enumerate(LABELS))


def _n(s):
    return re.sub(r"\s+", " ", s.lower().strip())


TEXT2LABEL = {_n(v): i for i, v in enumerate(LABELS)}


def prompt(profile):
    return ("Act as a medical doctor and diagnose the patient based on the following patient profile:\n\n"
            f"{profile.strip()}\n\n"
            "All possible diagnoses for you to choose from are as follows (one diagnosis per line, in the format of <number>. <diagnosis>):\n"
            f"{OPTIONS}\n\n"
            "Now, directly provide the diagnosis for the patient in the following format: <number>. <diagnosis>")


def parse(text):
    """-> label int or None. StreamBench rule: first '<number>.' in the lowercased answer (a JSON "answer" field is
    preferred when present); else a disease name found in the last line."""
    t = text or ""
    m = re.search(r'"answer"\s*:\s*"([^"]*)"', t)
    if m:
        t = m.group(1)
    nums = re.findall(r"(\d+)\.", t.lower().strip())
    if nums:
        k = int(nums[0])
        return k if k < len(LABELS) else None
    lines = [l for l in t.strip().splitlines() if l.strip()]
    last = _n(lines[-1]) if lines else ""
    last = re.sub(r"^(diagnosis|answer)\s*:\s*", "", last).strip(" .*")
    if last in TEXT2LABEL:
        return TEXT2LABEL[last]
    hits = [i for name, i in TEXT2LABEL.items() if name in last]
    return max(hits, key=lambda i: len(LABELS[i])) if hits else None


def _rows(split):
    import pyarrow.parquet as pq
    p = os.path.join(DATA, split + ".parquet")
    if not os.path.exists(p):
        os.makedirs(DATA, exist_ok=True)
        urllib.request.urlretrieve(BASE % split, p)
    return pq.read_table(p, columns=["PATIENT_PROFILE", "PATHOLOGY"]).to_pylist()


def _task(split, idx, row):
    label = TEXT2LABEL[_n(row["PATHOLOGY"])]
    ref = f"{label}. {LABELS[label]}"
    kw = dict(id=f"ddxplus-{split}-{idx}", question=prompt(row["PATIENT_PROFILE"]), grade=lambda a, _l=label: parse(a) == _l)
    try:
        return Task(**kw, reference=ref)
    except TypeError:
        t = Task(**kw); t.reference = ref; return t


def _stratified(rows, n, rng):
    by = defaultdict(list)
    for i, r in enumerate(rows):
        by[TEXT2LABEL[_n(r["PATHOLOGY"])]].append(i)
    for v in by.values():
        rng.shuffle(v)
    keys = sorted(by); picked = []
    while len(picked) < n and any(by.values()):
        rng.shuffle(keys)
        for k in keys:
            if by[k] and len(picked) < n:
                picked.append(by[k].pop())
    rng.shuffle(picked)
    return picked


def stream(seed=42, n_train=60, n_heldout=60):
    rng = random.Random(seed)
    tr, te = _rows("validate"), _rows("test")
    train = [_task("validate", i, tr[i]) for i in _stratified(tr, n_train, rng)]
    held = [_task("test", i, te[i]) for i in _stratified(te, n_heldout, rng)]
    return train, held
