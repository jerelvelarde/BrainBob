# Fine-tuned model test handoff

Bonan has supplied an opt-in **local LoRA maintenance checker**, not a hosted answering endpoint. The committed handoff is [experiments/memops-small/HANDOFF_JEREL.md](../experiments/memops-small/HANDOFF_JEREL.md), and [bridge.py](../experiments/memops-small/bridge.py) exposes `make_judge(callable)` for `maintain.ingest(judge=...)`. No persistent endpoint is required for that path. Run `local_generator` on the GPU host with access to the published Hub adapter, not the development laptop. The production judge is unchanged. Bonan subsequently published [confirmation and observe modes](https://github.com/jerelvelarde/BrainBob/blob/373eee2e11891e43232ae509c1d7de9ae3567e3a/experiments/memops-small/SAFE_MODE.md) at `fa7e93d`; use that implementation revision when following those instructions. Controlled saved-response tests do not establish live-provider safety.

Saved predictions from `d85064d` were independently rescored with the frozen 60-pair scorer: base **32/60**, tuned **42/60**, +16.7 points with template-cluster bootstrap 95% [+5.0, +28.3]. These are public synthetic memory-pair diagnostics, not an organizational Bob score. See [readiness and verified scorecard](readiness.md). The tuned checker misclassifies five non-conflict pairs as conflicts; keep it opt-in until the maintenance overwrite gate passes.

Base: `Qwen/Qwen3-0.6B@c1899de289a04d12100db370d81485cdf75e47ca`. Adapter: [Guangze/memops-small-qwen3-0.6b-lora](https://huggingface.co/Guangze/memops-small-qwen3-0.6b-lora). Pin canonical adapter commit `b904e6ec0baea37bf70209093b8c59332d3c450a`, matching the run metadata and Bonan's correction relayed by Jerel. Bonan confirmed that the later repository revisions, including `509ea772fc9a` and the model-card update, retain the same weights SHA-256 `21588c9e975fe23d6c8e73db35bea23cd8834e8e1259ce6184d29472c7a19a0b`. We did not independently download or execute those weights in this assessment.

The separate HTTP configuration below is available for future hosted models or a temporarily served checkpoint. An earlier offline preflight found no configured inference credential; that historical check does not describe the later [live-workspace verification](../judging/live-workspace-20261017/README.md).

For a new model run, freeze:

- Immutable checkpoint ID/hash, base model, and the intended role (answering agent, memory extractor, or maintenance judge).
- Execution path (local GPU callable or endpoint), credential setup, context limit, supported chat template and request parameters.
- Training-data manifest and any exposure to our synthetic fixtures, Bob pilot, or external benchmark examples. Public pilot cases are development material; do not call them held out after training on them.

From the repository root, inspect the effective configuration without inference or printing keys:

```bash
backend/.venv/bin/python backend/model_preflight.py
```

Each role supports `BRAINBOB_<ROLE>_MODEL`, `_BASE_URL`, `_API_KEY`, `_EXTRA_BODY`, and `_CACHE_NAMESPACE`. Roles are `AGENT`, `CURATOR`, `CURATOR_CAREFUL`, `CURATOR_SLOPPY`, `CURATOR_QWEN`, and `JUDGE`. Global `BRAINBOB_BASE_URL` and `BRAINBOB_API_KEY` are fallbacks; absent an environment key, the existing `~/.config/crusoe/api.key` file is used. Prefer role-specific settings for a candidate so the judge remains fixed. Set `EXTRA_BODY` to JSON `null` when the serving stack does not accept Nemotron's `chat_template_kwargs`.

Example after replacing the placeholders with Bonan's actual values:

```bash
export BRAINBOB_AGENT_MODEL='actual-served-model-id'
export BRAINBOB_AGENT_BASE_URL='http://127.0.0.1:9000/v1'
export BRAINBOB_AGENT_EXTRA_BODY='null'
export BRAINBOB_AGENT_CACHE_NAMESPACE='actual-checkpoint-sha'
# Set BRAINBOB_AGENT_API_KEY securely in your environment.
backend/.venv/bin/python backend/model_preflight.py
```

Use `CURATOR` instead of `AGENT` when testing extraction. `CURATOR_CAREFUL` is a separate writer used by some multi-writer experiments: configure only the role under test. The cache includes endpoint and checkpoint namespace as well as model and request parameters. Always change the namespace when replacing weights behind the same model name. Existing cache entries from the earlier endpoint-agnostic scheme will not be reused.

Before scoring, run a small **development** smoke test with the actual service. The following command makes inference calls and is not part of the offline preflight:

```bash
cd backend
.venv/bin/python bench.py correctness --split dev
```

Freeze the dataset/split hashes, prompt hashes, judge, baseline model, budgets, role configuration, and checkpoint first. Run the baseline and candidate with identical tasks and settings, changing only the declared role. Save each preflight JSON alongside its results; model/endpoint configuration alone is not a complete reproducibility manifest. Compare the paired outcomes, state correctness, stale-fact use, leakage, legitimate utility, and costs separately. Then run held-out evaluation once without adapting prompts to its feedback:

```bash
.venv/bin/python bench.py correctness --split heldout
```

This is the existing synthetic Rusty Rod suite, **not Bob Benchmark, GateMem, MUMBench, or CoMemBench**. Each external suite needs its native data, adapter and scoring protocol. The organizational Bob public pilot is in `bobbench/`; the separate memory-pair scorer used by Bonan is in `benchmarks/bob/`. Configure a custom `judge` through Bonan's bridge to exercise the LoRA; setting `BRAINBOB_JUDGE_MODEL` alone does not load local adapter weights or select its distinct prompt.

Legacy cost accounting uses a fallback tariff for unknown model IDs and is not valid for a custom endpoint. The preflight flags these routes; report cost as unknown until a provider price schedule or measured local resource cost is attached. No performance benefit, cost reduction, or official benchmark score is established by this handoff configuration.
