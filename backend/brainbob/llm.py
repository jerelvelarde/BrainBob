"""All model calls: role -> model, Crusoe client, key file, retries, disk cache, cost."""
import collections, hashlib, json, os, sys, threading, time
import openai
from openai import OpenAI

CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache")
LIGHT = "nvidia/Nemotron-3.5-Lightning-30B-A3B"
NANO = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"
QWEN = "Qwen/Qwen3.8-27B"
NOTHINK = {"chat_template_kwargs": {"enable_thinking": False}}
PRICE = {LIGHT: (0.05, 0.20), "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B": (0.30, 2.40), "openai/gpt-oss-120b": (0.05, 0.25), NANO: (0.05, 0.20), QWEN: (0.10, 0.40)}
_OVR = {}  # role -> default overrides (configure)
DEFAULT_BASE_URL = "https://api.inference.crusoecloud.com/v1"


def _roles():
    r = {
        "curator": dict(model=LIGHT, max_tokens=4096, temperature=0, extra_body=NOTHINK),
        "curator_sloppy": dict(model=NANO, max_tokens=4096, temperature=float(os.environ.get("BRAINBOB_SLOPPY_TEMP", "1.2")), extra_body=NOTHINK),
        "curator_careful": dict(model=LIGHT, max_tokens=512, temperature=0, extra_body=NOTHINK),
        "curator_qwen": dict(model=QWEN, max_tokens=512, temperature=0, extra_body=NOTHINK),
        "agent": dict(model=os.environ.get("BRAINBOB_AGENT_MODEL", LIGHT), max_tokens=2048, temperature=0, extra_body=NOTHINK),
        "summarizer": dict(model=NANO, max_tokens=768, temperature=0, extra_body=NOTHINK),
        "judge": dict(model="openai/gpt-oss-120b", max_tokens=2048, temperature=0, extra_body=None),
    }
    for role, cfg in r.items():
        prefix = f"BRAINBOB_{role.upper()}"
        cfg["model"] = os.environ.get(f"{prefix}_MODEL", cfg["model"])
        if os.environ.get(f"{prefix}_EXTRA_BODY") is not None:
            cfg["extra_body"] = json.loads(os.environ[f"{prefix}_EXTRA_BODY"])
        cfg.update(_OVR.get(role, {}))
    return r


_SEM = {"curator": threading.Semaphore(24), "curator_sloppy": threading.Semaphore(24), "agent": threading.Semaphore(16), "judge": threading.Semaphore(16),
        "curator_careful": threading.Semaphore(24), "curator_qwen": threading.Semaphore(24), "summarizer": threading.Semaphore(4)}
_USAGE, _LOCK = [], threading.Lock()


def configure(role, concurrency=None, **defaults):
    """Change a role's default call params (e.g. max_tokens) and/or its concurrency."""
    _OVR.setdefault(role, {}).update(defaults)
    if concurrency:
        _SEM[role] = threading.Semaphore(concurrency)


def _key(role=None):
    for name in ([f"BRAINBOB_{role.upper()}_API_KEY"] if role else []) + ["BRAINBOB_API_KEY"]:
        if os.environ.get(name):
            return os.environ[name]
    return open(os.path.expanduser("~/.config/crusoe/api.key")).read().strip()


def _base_url(role=None):
    return os.environ.get(f"BRAINBOB_{role.upper()}_BASE_URL", os.environ.get("BRAINBOB_BASE_URL", DEFAULT_BASE_URL)).rstrip("/") if role else os.environ.get("BRAINBOB_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def configuration():
    """Serializable effective model configuration; deliberately excludes credentials."""
    return {role: {**cfg, "base_url": _base_url(role),
                   "cache_namespace": os.environ.get(f"BRAINBOB_{role.upper()}_CACHE_NAMESPACE", os.environ.get("BRAINBOB_CACHE_NAMESPACE", ""))}
            for role, cfg in _roles().items()}


_clients = {}


def _get_client(role=None):
    endpoint, key = _base_url(role), _key(role)
    identity = (endpoint, hashlib.sha256(key.encode()).hexdigest())
    with _LOCK:
        if identity not in _clients:
            _clients[identity] = OpenAI(api_key=key, base_url=endpoint, timeout=900, max_retries=0)
        return _clients[identity]


def complete(role, messages, fresh=False, **kw):
    """fresh=True skips reading the cache (the result is still written to it)."""
    cfg = {**_roles()[role], **kw}  # kw overrides; None drops the param
    model = cfg["model"]
    namespace = os.environ.get(f"BRAINBOB_{role.upper()}_CACHE_NAMESPACE", os.environ.get("BRAINBOB_CACHE_NAMESPACE", ""))
    payload = json.dumps([_base_url(role), namespace, model, messages, cfg.get("max_tokens"), cfg.get("temperature"), cfg.get("extra_body")], sort_keys=True)
    path = os.path.join(CACHE, hashlib.sha256(payload.encode()).hexdigest() + ".json")
    if not fresh and os.path.exists(path):
        try:
            d = json.load(open(path))
            with _LOCK: _USAGE.append((role, model, d["pt"], d["ct"], True))
            return d["content"]
        except Exception:
            pass
    req = dict(model=model, messages=messages)
    for k in ("max_tokens", "temperature", "extra_body"):
        if cfg.get(k) is not None: req[k] = cfg[k]
    # The optional memory overview must fail promptly enough for the UI to retry.
    if role == "summarizer": req["timeout"] = 30
    delay = 1 if role == "summarizer" else 3
    with _SEM[role]:
        for _ in range(2 if role == "summarizer" else 8):
            try:
                r = _get_client(role).chat.completions.create(**req); break
            except (openai.RateLimitError, openai.APIConnectionError, openai.APITimeoutError, openai.InternalServerError):
                time.sleep(delay); delay = min(delay * 2, 60)
            except openai.APIStatusError as e:
                if e.status_code >= 500 or e.status_code == 429:
                    time.sleep(delay); delay = min(delay * 2, 60)
                else:
                    print("HTTP", e.status_code, str(e)[:200].replace(_key(role), "***"), file=sys.stderr); return ""
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
