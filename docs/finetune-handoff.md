# Fine-tuned model test handoff

The harness can route each role to a separate OpenAI-compatible endpoint. A checkpoint path alone is insufficient: serve it behind a chat-completions endpoint first. No fine-tuned checkpoint or endpoint has been supplied yet, and the local preflight found no configured inference credential. Offline tests do not establish model availability or quality.

Ask Bonan for:

- Immutable checkpoint ID/hash, base model, and the intended role (answering agent, memory extractor, or maintenance judge).
- Endpoint URL, credential setup, context limit, supported chat template and request parameters.
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

This is the existing synthetic Rusty Rod suite, **not Bob Benchmark, GateMem, MUMBench, or CoMemBench**. Each external suite needs its native data, adapter and scoring protocol. The six-world Bob public pilot is separately documented and cannot establish held-out model performance.

Legacy cost accounting uses a fallback tariff for unknown model IDs and is not valid for a custom endpoint. The preflight flags these routes; report cost as unknown until a provider price schedule or measured local resource cost is attached. No performance benefit, cost reduction, or official benchmark score is established by this handoff configuration.
