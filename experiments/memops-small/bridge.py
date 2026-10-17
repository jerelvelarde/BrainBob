"""Plug the small memory-operation checker into backend/brainbob/maintain.ingest(judge=...) for an isolated run.

    from bridge import make_judge
    judge = make_judge(fn)                                   # fn(messages) -> raw text (fake, local model, anything)
    judge = make_judge("http://host:8000/v1", model="user/memops-small-qwen3-0.6b-lora")  # OpenAI-compatible endpoint
    judge = make_judge(local_generator(adapter="user/memops-small-qwen3-0.6b-lora"))       # transformers on a GPU box
    maintain.ingest(episode, store, acl, judge=judge)

The model sees Jerel's Bob benchmark input format (bob_format.py), the same format it was trained and evaluated on,
not maintain.llm_judge's production prompt. The judge only returns the semantic relation (same / conflict / unrelated) or None. Every operation is still decided by
maintain's deterministic rules (_covers, _pair_action, locks, ACL); None takes the existing conservative path (tentative,
never overwrite). The production default judge is not touched.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from job_all import BASE, BASE_REVISION, parse_strict  # noqa: E402  (pure python, no torch at import)
import bob_format  # noqa: E402

CANONICAL_ADAPTER = "Guangze/memops-small-qwen3-0.6b-lora"
CANONICAL_ADAPTER_REVISION = "b904e6ec0baea37bf70209093b8c59332d3c450a"


def messages(cand, mem):
    """Bob-format messages for one (candidate, existing memory) pair. maintain's candidate dict has no source id, so the
    episode id is used when the caller adds one (cand['source_id']), else the literal 'candidate'."""
    return bob_format.messages(f"pair-{mem.id}", {"text": mem.text, "date": mem.date, "id": mem.id},
                               {"text": cand["text"], "date": cand["date"], "source_id": cand.get("source_id") or "candidate"})


def _endpoint(url, model, api_key=None, max_tokens=16):
    from openai import OpenAI
    client = OpenAI(base_url=url, api_key=api_key or os.environ.get("MEMOPS_API_KEY", "none"), timeout=60, max_retries=1)

    def gen(msgs):
        r = client.chat.completions.create(model=model, messages=msgs, temperature=0, max_tokens=max_tokens,
                                           extra_body={"chat_template_kwargs": {"enable_thinking": False}})
        return r.choices[0].message.content or ""
    return gen


def local_generator(adapter=None, base=BASE, revision=BASE_REVISION, max_new_tokens=16, *, adapter_revision=None):
    """GPU-only generator. The known released adapter defaults to its canonical
    frozen revision; an explicit adapter_revision overrides it. Local directories
    and unrelated repositories retain their existing behavior.
    """
    if adapter_revision is None and adapter == CANONICAL_ADAPTER and not os.path.isdir(adapter):
        adapter_revision = CANONICAL_ADAPTER_REVISION
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(base, revision=revision)
    m = AutoModelForCausalLM.from_pretrained(base, revision=revision, torch_dtype=torch.bfloat16).to("cuda")
    if adapter:
        from peft import PeftModel
        m = PeftModel.from_pretrained(m, adapter, revision=adapter_revision)
    m.eval()

    def gen(msgs):
        p = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
        enc = tok(p, return_tensors="pt", add_special_tokens=False).to(m.device)
        with torch.no_grad():
            out = m.generate(**enc, do_sample=False, max_new_tokens=max_new_tokens, pad_token_id=tok.pad_token_id)
        return tok.decode(out[0, enc["input_ids"].shape[1]:], skip_special_tokens=True)
    gen.model_id = f"{base}@{revision}" + (f"+{adapter}" + (f"@{adapter_revision}" if adapter_revision else "") if adapter else "")
    return gen


def make_judge(model_or_endpoint, *, model=None, api_key=None):
    """Return judge(cand, mem) -> 'same' | 'conflict' | 'unrelated' | None for maintain.ingest(judge=...).
    model_or_endpoint: a callable messages -> raw text, or an http(s) URL of an OpenAI-compatible server (needs model=).
    Any exception or non-strict-JSON output returns None (the conservative path)."""
    if callable(model_or_endpoint):
        gen = model_or_endpoint
    elif isinstance(model_or_endpoint, str) and model_or_endpoint.startswith(("http://", "https://")):
        if not model: raise ValueError("model= is required for an endpoint")
        gen = _endpoint(model_or_endpoint, model, api_key)
    else:
        raise TypeError("pass a callable(messages) -> str or an http(s) endpoint URL")

    def judge(cand, mem):
        try: return parse_strict(gen(messages(cand, mem)))
        except Exception: return None
    judge.model_id = model or getattr(gen, "model_id", None) or "custom:memops-unidentified"
    return judge
