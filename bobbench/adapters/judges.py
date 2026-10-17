"""Maintenance pair judges for the judge-comparison conditions. Only the judge that BrainBob's maintain.ingest(judge=...)
calls changes; curator, audit judge, retrieval, rules, answerer and budget stay fixed.

    maintained             production judge (backend role "judge", gpt-oss-120b, production prompt) - built in brainbob.py
    maintained_teacher     Bob-format messages -> Crusoe nvidia/NVIDIA-Nemotron-3-Super-120B-A12B (bridge._endpoint)
    maintained_tuned       Bob-format messages -> Qwen3-0.6B@pinned + LoRA Guangze/memops-small-qwen3-0.6b-lora@pinned,
                           adapter_model.safetensors sha256 checked after loading (bridge.local_generator, GPU)
    maintained_small_base  same base, no adapter

Every call is recorded by TracedJudge: input hash, raw output, parsed verdict, latency, model, revision, error, timeout,
usage and cost. A reply that does not parse returns None (maintain's conservative path) and is counted. torch,
transformers, peft and huggingface_hub are imported only when a local judge is built, so the other conditions run
without them. This module does not import BrainBob.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MEMOPS = ROOT / "experiments" / "memops-small"
VERDICTS = ("same", "conflict", "unrelated")

TEACHER_BASE_URL = "https://api.inference.crusoecloud.com/v1"
TEACHER_MODEL = "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B"
TEACHER_MAX_TOKENS = 64          # as experiments/memops-small/compare_large_judges.py for this model
TEACHER_PRICE_PER_MTOK = (0.30, 2.40)  # (input, output) USD, same as backend/brainbob/llm.py PRICE
KEY_FILE = "~/.config/crusoe/api.key"

BASE = "Qwen/Qwen3-0.6B"
BASE_REVISION = "c1899de289a04d12100db370d81485cdf75e47ca"
ADAPTER = "Guangze/memops-small-qwen3-0.6b-lora"
ADAPTER_REVISION = "b904e6ec0baea37bf70209093b8c59332d3c450a"
ADAPTER_FILE = "adapter_model.safetensors"
ADAPTER_SHA256 = "21588c9e975fe23d6c8e73db35bea23cd8834e8e1259ce6184d29472c7a19a0b"
GPU_USD_PER_HOUR = {"l4x1": 0.80, "a100-large": 2.50}  # experiments/memops-small/job_all.py PRICE_PER_HOUR

JUDGE_CONDITIONS = {"maintained_teacher": "teacher", "maintained_tuned": "tuned", "maintained_small_base": "small_base"}


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _is_timeout(e: BaseException) -> bool:
    return "timeout" in type(e).__name__.lower() or isinstance(e, TimeoutError)


def bridge():
    """experiments/memops-small/bridge.py (pure python at import; no torch)."""
    if str(MEMOPS) not in sys.path:
        sys.path.insert(0, str(MEMOPS))
    import bridge as _b
    return _b


class TracedJudge:
    """judge(cand, mem) -> 'same' | 'conflict' | 'unrelated' | None, recording every call in ``calls``.

    build(cand, mem) -> messages; run(cand, mem, messages) -> {"raw": str, "usage": dict | None, ["verdict"]};
    parse(raw) -> verdict | None (used when run returns no verdict). Exceptions become None with the error recorded.
    usd: usage["usd"] if given, else tokens x price_per_mtok, else latency x gpu_usd_per_hour."""

    def __init__(self, run, *, build, parse=None, model_id: str, info: dict, billed_via: str = "direct",
                 price_per_mtok=None, gpu_usd_per_hour=None):
        self.run, self.build, self.parse = run, build, parse
        self.model_id = model_id
        self.info = dict(info)
        self.billed_via = billed_via  # "brainbob.llm": already in backend usage; "direct": billed only here
        self.price_per_mtok, self.gpu_usd_per_hour = price_per_mtok, gpu_usd_per_hour
        self.calls: list[dict] = []

    def reset(self):
        self.calls = []

    def __call__(self, cand, mem):
        rec = {"call": len(self.calls), "judge": self.info.get("kind"), "model": self.info.get("model"),
               "revision": self.info.get("revision"), "adapter": self.info.get("adapter"),
               "adapter_revision": self.info.get("adapter_revision"), "memory_id": getattr(mem, "id", None),
               "billed_via": self.billed_via}
        raw, usage, verdict, err, timeout = None, None, None, None, False
        t0 = time.perf_counter()
        try:
            msgs = self.build(cand, mem)
            rec["input_sha256"] = _sha(json.dumps(msgs, sort_keys=True, ensure_ascii=False))
            out = self.run(cand, mem, msgs) or {}
            raw, usage = out.get("raw"), out.get("usage")
            verdict = out["verdict"] if "verdict" in out else (self.parse(raw) if self.parse else None)
        except Exception as e:  # noqa: BLE001 - any failure is the conservative None path, recorded
            err, timeout = f"{type(e).__name__}: {str(e)[:200]}", _is_timeout(e)
        latency_s = time.perf_counter() - t0
        verdict = verdict if verdict in VERDICTS else None
        usd = None
        if isinstance(usage, dict) and usage.get("usd") is not None:
            usd = float(usage["usd"])
        elif isinstance(usage, dict) and self.price_per_mtok:
            pi, po = self.price_per_mtok
            usd = ((usage.get("prompt_tokens") or 0) * pi + (usage.get("completion_tokens") or 0) * po) / 1e6
        elif self.gpu_usd_per_hour:
            usd = latency_s * self.gpu_usd_per_hour / 3600
        rec.setdefault("input_sha256", None)
        rec.update(raw_output=raw, parsed=verdict, parse_failed=err is None and verdict is None, error=err,
                   timeout=timeout, latency_ms=round(1000 * latency_s, 3), usage=usage, usd=usd)
        self.calls.append(rec)
        return verdict

    def describe(self) -> dict:
        return {"implementation": "traced_callable", "model": self.model_id, **self.info, "billed_via": self.billed_via,
                "usage": summarize_calls(self.calls)}


def _pct(xs, q):
    xs = sorted(xs)
    if not xs:
        return None
    k = (len(xs) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def summarize_calls(calls) -> dict:
    calls = list(calls or [])
    lat = [c["latency_ms"] for c in calls if c.get("latency_ms") is not None and not c.get("error")]
    verdicts = {}
    for c in calls:
        k = c.get("parsed") or "None"
        verdicts[k] = verdicts.get(k, 0) + 1
    return {"calls": len(calls), "parse_failed": sum(1 for c in calls if c.get("parse_failed")),
            "errors": sum(1 for c in calls if c.get("error")), "timeouts": sum(1 for c in calls if c.get("timeout")),
            "none": sum(1 for c in calls if c.get("parsed") is None), "verdicts": verdicts,
            "latency_ms_p50": _pct(lat, 0.5), "latency_ms_p95": _pct(lat, 0.95),
            "usd": sum(c.get("usd") or 0 for c in calls),
            "usd_direct": sum(c.get("usd") or 0 for c in calls if c.get("billed_via") == "direct")}


# ---------------------------------------------------------------- condition judges

def _bob_judge(gen, *, model_id, info, **kw) -> TracedJudge:
    b = bridge()
    return TracedJudge(lambda cand, mem, msgs: {"raw": gen(msgs), "usage": getattr(gen, "last_usage", None)},
                       build=b.messages, parse=b.parse_strict, model_id=model_id, info=info, **kw)


def teacher_judge() -> TracedJudge:
    b = bridge()
    with open(os.path.expanduser(KEY_FILE), encoding="utf-8") as f:
        key = f.read().strip()
    gen = b._endpoint(TEACHER_BASE_URL, TEACHER_MODEL, api_key=key, max_tokens=TEACHER_MAX_TOKENS)
    info = {"kind": "teacher", "model": TEACHER_MODEL, "revision": "crusoe-hosted (provider does not expose one)",
            "base_url": TEACHER_BASE_URL, "max_tokens": TEACHER_MAX_TOKENS, "temperature": 0, "thinking": False,
            "prompt": "bob_format.PROMPT (memops-small bridge)"}
    return _bob_judge(gen, model_id=TEACHER_MODEL, info=info, price_per_mtok=TEACHER_PRICE_PER_MTOK)


_LOCAL: dict = {}
_LOCAL_LOCK = threading.Lock()


def _file_sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_adapter(repo=ADAPTER, revision=ADAPTER_REVISION, expected=ADAPTER_SHA256) -> dict:
    """sha256 of the adapter weights at the pinned revision (from the local HF cache that peft just filled)."""
    from huggingface_hub import hf_hub_download
    path = hf_hub_download(repo, ADAPTER_FILE, revision=revision)
    got = _file_sha256(path)
    if got != expected:
        raise RuntimeError(f"{repo}@{revision} {ADAPTER_FILE} sha256 {got} != expected {expected}")
    return {"adapter_file": ADAPTER_FILE, "adapter_sha256": got, "adapter_sha256_expected": expected, "verified": True}


def _local_gen(kind: str):
    """Load once per process (cached; a load failure is cached too and re-raised for every run)."""
    with _LOCAL_LOCK:
        if kind not in _LOCAL:
            t0 = time.time()
            try:
                b = bridge()
                if kind == "tuned":
                    gen = b.local_generator(adapter=ADAPTER, base=BASE, revision=BASE_REVISION, adapter_revision=ADAPTER_REVISION)
                    check = verify_adapter()
                else:
                    gen = b.local_generator(adapter=None, base=BASE, revision=BASE_REVISION)
                    check = {}
                _LOCAL[kind] = (gen, {**check, "load_s": round(time.time() - t0, 2)}, None)
            except Exception as e:  # noqa: BLE001
                _LOCAL[kind] = (None, {"load_s": round(time.time() - t0, 2)}, e)
        gen, meta, err = _LOCAL[kind]
    if err is not None:
        raise RuntimeError(f"local {kind} judge failed to load: {type(err).__name__}: {str(err)[:300]}") from err
    return gen, meta


def local_judge(kind: str) -> TracedJudge:
    gen, meta = _local_gen(kind)
    flavor = os.environ.get("BOB_FLAVOR", "l4x1")
    info = {"kind": kind, "model": BASE, "revision": BASE_REVISION, "max_new_tokens": 16, "decoding": "greedy",
            "thinking": False, "prompt": "bob_format.PROMPT (memops-small bridge)", "flavor": flavor,
            "cost_basis": f"GPU wall time x {GPU_USD_PER_HOUR.get(flavor)} USD/h", **meta}
    if kind == "tuned":
        info.update(adapter=ADAPTER, adapter_revision=ADAPTER_REVISION)
    model_id = getattr(gen, "model_id", None) or (f"{BASE}@{BASE_REVISION}" + (f"+{ADAPTER}@{ADAPTER_REVISION}" if kind == "tuned" else ""))
    return _bob_judge(gen, model_id=model_id, info=info, gpu_usd_per_hour=GPU_USD_PER_HOUR.get(flavor))


def condition_judge(condition: str) -> TracedJudge:
    kind = JUDGE_CONDITIONS[condition]
    return teacher_judge() if kind == "teacher" else local_judge(kind)
