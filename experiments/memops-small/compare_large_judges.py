"""Run large Crusoe-hosted judges on the frozen Bob eval inputs for comparison with the 0.6B checker.

Same exported messages (system + user), temperature 0, Nemotron thinking off. gpt-oss cannot turn
reasoning off, so it gets a larger token cap. The response is normalized the way the production
judge path normalizes it (strip whitespace and markdown code fences) before it is written for scoring.

Usage (repo root): backend/.venv/Scripts/python -I experiments/memops-small/compare_large_judges.py OUT_DIR
"""
import concurrent.futures as cf
import json
import os
import re
import sys
import time

from openai import OpenAI

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = {
    "gpt-oss-120b": ("openai/gpt-oss-120b", {"max_tokens": 1024}),
    "nemotron-super": ("nvidia/NVIDIA-Nemotron-3-Super-120B-A12B",
                       {"max_tokens": 64, "extra_body": {"chat_template_kwargs": {"enable_thinking": False}}}),
    "nemotron-lightning": ("nvidia/Nemotron-3.5-Lightning-30B-A3B",
                           {"max_tokens": 64, "extra_body": {"chat_template_kwargs": {"enable_thinking": False}}}),
}


def normalize(text):
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S).strip()
    m = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, flags=re.S)
    return (m.group(1) if m else text).strip()


def main(out_dir):
    key = open(os.path.expanduser("~/.config/crusoe/api.key")).read().strip()
    client = OpenAI(api_key=key, base_url="https://api.inference.crusoecloud.com/v1", timeout=120, max_retries=4)
    rows = [json.loads(l) for l in open(os.path.join(HERE, "bob_inputs", "eval_inputs.jsonl"), encoding="utf8")]
    os.makedirs(out_dir, exist_ok=True)
    usage = {}

    def one(name, model, kw, row):
        t = time.time()
        try:
            r = client.chat.completions.create(model=model, messages=row["messages"][:2], temperature=0, **kw)
            u = r.usage
            return dict(id=row["id"], input_sha256=row["input_sha256"], response=normalize(r.choices[0].message.content),
                        latency_ms=round((time.time() - t) * 1000, 1)), (u.prompt_tokens, u.completion_tokens)
        except Exception as e:  # noqa: BLE001
            return dict(id=row["id"], input_sha256=row["input_sha256"], error=type(e).__name__), (0, 0)

    for name, (model, kw) in MODELS.items():
        with cf.ThreadPoolExecutor(16) as ex:
            res = list(ex.map(lambda r: one(name, model, kw, r), rows))
        with open(os.path.join(out_dir, f"{name}_eval.jsonl"), "w", encoding="utf8", newline="\n") as f:
            for pred, _ in res:
                f.write(json.dumps(pred) + "\n")
        usage[name] = dict(model=model, prompt_tokens=sum(u[0] for _, u in res), completion_tokens=sum(u[1] for _, u in res),
                           errors=sum(1 for p, _ in res if "error" in p), settings=kw)
        print(name, usage[name])
    json.dump(usage, open(os.path.join(out_dir, "large_judges_meta.json"), "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1])
