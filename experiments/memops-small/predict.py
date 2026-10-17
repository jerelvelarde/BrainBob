# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = [
#   "torch==2.8.0",
#   "transformers==4.56.2",
#   "peft==0.17.1",
#   "accelerate==1.10.1",
#   "huggingface_hub==0.35.3",
# ]
# ///
"""Standalone re-prediction (GPU only; never on the laptop): frozen base, or base + LoRA adapter from a local dir or Hub.

Input: a Bob export `inputs.jsonl` (id, input_sha256, messages) -- or any JSONL with those fields; messages are used
unchanged. Output: Jerel's prediction JSONL ({"id","input_sha256","response","latency_ms"} or "error"), plus a separate
`<out>.probs.json` with label probabilities and, if rows carry a `label`, metrics. Greedy, non-thinking, short output cap.

  python predict.py --inputs bob_inputs/eval_inputs.jsonl --out base_eval.jsonl
  python predict.py --inputs bob_inputs/eval_inputs.jsonl --adapter user/memops-small-qwen3-0.6b-lora --out tuned_eval.jsonl

Shared helpers come from job_all.py: --lib, this folder, /data (newer `hf jobs uv run` ships local file args there), or the
adapter repo's code/job_all.py.
"""
import argparse, importlib.util, json, os, time


def _load_lib(path, adapter, token):
    for p in ([path] if path else []) + [os.path.join(os.path.dirname(os.path.abspath(__file__)), "job_all.py"), "/data/job_all.py"]:
        if p and os.path.isfile(p): break
    else:
        if not adapter or os.path.isdir(adapter): raise SystemExit("job_all.py not found: pass --lib path/to/job_all.py")
        from huggingface_hub import hf_hub_download
        p = hf_hub_download(adapter, "code/job_all.py", token=token)
    spec = importlib.util.spec_from_file_location("job_all", p); mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod); return mod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--adapter", default=None); ap.add_argument("--adapter-revision", default=None)
    ap.add_argument("--base", default="Qwen/Qwen3-0.6B"); ap.add_argument("--revision", default=None)
    ap.add_argument("--lib", default=None); ap.add_argument("--threshold", type=float, default=0.8)
    ap.add_argument("--max-new-tokens", type=int, default=16)
    a = ap.parse_args()
    token = os.environ.get("HF_TOKEN")
    J = _load_lib(a.lib, a.adapter, token)
    revision = a.revision or J.BASE_REVISION
    rows = [json.loads(l) for l in open(a.inputs, encoding="utf8") if l.strip()]
    items = [dict(id=r["id"], input_sha256=r.get("input_sha256"), label=r.get("label"), messages=r["messages"][:2],
                  authority=(r.get("candidate") or {}).get("authority"), cand_date=(r.get("candidate") or {}).get("date"),
                  old_date=(r.get("existing") or {}).get("date")) for r in rows]

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(a.base, revision=revision, token=token)
    dtype = torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else torch.float32
    model = AutoModelForCausalLM.from_pretrained(a.base, revision=revision, torch_dtype=dtype, token=token)
    model = model.to("cuda" if torch.cuda.is_available() else "cpu")
    ident = dict(base=a.base, base_revision=revision, adapter=None)
    if a.adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, a.adapter, revision=a.adapter_revision, token=token)
        sha = None
        if not os.path.isdir(a.adapter):
            from huggingface_hub import HfApi
            sha = HfApi(token=token).model_info(a.adapter, revision=a.adapter_revision).sha
        ident["adapter"] = dict(source=a.adapter, revision=sha or a.adapter_revision)
    cold = round(time.time() - t0, 2)
    preds = J.predict(model, tok, items, a.max_new_tokens, "predict")
    with open(a.out, "w", encoding="utf8") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in J.submission(preds))
    side = dict(model=ident, inputs=a.inputs, n=len(items), cold_setup_s=cold, versions=J.versions(),
                hardware=torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu", threshold=a.threshold,
                rows=[dict(id=r["id"], probs=r.get("probs"), label_logprobs=r.get("label_logprobs")) for r in preds])
    if items and all(it["label"] for it in items):
        side["metrics"] = J.metrics(preds, a.threshold)
    json.dump(side, open(a.out + ".probs.json", "w", encoding="utf8"), indent=1)
    print("wrote", a.out, "and", a.out + ".probs.json", "| cold_setup_s", cold)


if __name__ == "__main__":
    main()
