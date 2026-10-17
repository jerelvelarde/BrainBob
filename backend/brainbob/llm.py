"""All model calls: role -> model, Crusoe client, key file, retries, disk cache, cost."""
import collections, hashlib, json, os, sys, threading, time
import openai
from openai import OpenAI

CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache")
LIGHT = "nvidia/Nemotron-3.5-Lightning-30B-A3B"
NOTHINK = {"chat_template_kwargs": {"enable_thinking": False}}
PRICE = {LIGHT: (0.05, 0.20), "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B": (0.30, 2.40), "openai/gpt-oss-120b": (0.05, 0.25)}
_OVR = {}  # role -> default overrides (configure)


def _roles():
    r = {
        "curator": dict(model=LIGHT, max_tokens=4096, temperature=0, extra_body=NOTHINK),
        "agent": dict(model=os.environ.get("BRAINBOB_AGENT_MODEL", LIGHT), max_tokens=2048, temperature=0, extra_body=NOTHINK),
        "judge": dict(model="openai/gpt-oss-120b", max_tokens=2048, temperature=0, extra_body=None),
    }
    return {k: {**v, **_OVR.get(k, {})} for k, v in r.items()}


_SEM = {"curator": threading.Semaphore(24), "agent": threading.Semaphore(16), "judge": threading.Semaphore(16)}
_USAGE, _LOCK, _client = [], threading.Lock(), None


def configure(role, concurrency=None, **defaults):
    """Change a role's default call params (e.g. max_tokens) and/or its concurrency."""
    _OVR.setdefault(role, {}).update(defaults)
    if concurrency:
        _SEM[role] = threading.Semaphore(concurrency)


def _key():
    return open(os.path.expanduser("~/.config/crusoe/api.key")).read().strip()


def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=_key(), base_url="https://api.inference.crusoecloud.com/v1", timeout=900, max_retries=0)
    return _client


def complete(role, messages, **kw):
    cfg = {**_roles()[role], **kw}  # kw overrides; None drops the param
    model = cfg["model"]
    payload = json.dumps([model, messages, cfg.get("max_tokens"), cfg.get("temperature"), cfg.get("extra_body")], sort_keys=True)
    path = os.path.join(CACHE, hashlib.sha256(payload.encode()).hexdigest() + ".json")
    if os.path.exists(path):
        try:
            d = json.load(open(path))
            with _LOCK: _USAGE.append((role, model, d["pt"], d["ct"], True))
            return d["content"]
        except Exception:
            pass
    req = dict(model=model, messages=messages)
    for k in ("max_tokens", "temperature", "extra_body"):
        if cfg.get(k) is not None: req[k] = cfg[k]
    delay = 3
    with _SEM[role]:
        for _ in range(8):
            try:
                r = _get_client().chat.completions.create(**req); break
            except (openai.RateLimitError, openai.APIConnectionError, openai.APITimeoutError, openai.InternalServerError):
                time.sleep(delay); delay = min(delay * 2, 60)
            except openai.APIStatusError as e:
                if e.status_code >= 500 or e.status_code == 429:
                    time.sleep(delay); delay = min(delay * 2, 60)
                else:
                    print("HTTP", e.status_code, str(e)[:200].replace(_key(), "***"), file=sys.stderr); return ""
        else:
            return ""
    c = r.choices[0].message.content or ""
    if "</think>" in c: c = c.split("</think>")[-1]
    c = c.strip()
    if c.startswith("```"):
        lines = c.split("\n")
        c = "\n".join(lines[1:-1] if lines[-1].strip().startswith("```") else lines[1:]).strip()
    pt, ct = r.usage.prompt_tokens, r.usage.completion_tokens
    json.dump(dict(content=c, pt=pt, ct=ct), open(path, "w"))
    with _LOCK: _USAGE.append((role, model, pt, ct, False))
    return c


def usage():
    """{role: {calls, cached, pt, ct, usd}}; usd counts only fresh (non-cached) calls, usd_all counts all."""
    out = collections.defaultdict(lambda: dict(calls=0, cached=0, pt=0, ct=0, usd=0.0, usd_all=0.0))
    with _LOCK: rows = list(_USAGE)
    for role, model, pt, ct, cached in rows:
        o = out[role]; pi, po = PRICE.get(model, (0.3, 2.4)); c = (pt * pi + ct * po) / 1e6
        o["calls"] += 1; o["cached"] += cached; o["pt"] += pt; o["ct"] += ct; o["usd_all"] += c
        if not cached: o["usd"] += c
    return dict(out)


os.makedirs(CACHE, exist_ok=True)
