# memops-small: a 0.6B memory-operation checker (issue #7)

This is a LoRA fine-tune of `Qwen/Qwen3-0.6B` (revision `c1899de289a04d12100db370d81485cdf75e47ca`) for the pairwise memory judge. Given one existing memory and one new candidate, it answers `{"verdict":"same"|"conflict"|"unrelated"}`. Base and tuned models are compared on Jerel's Bob memory-pair benchmark (`codex/bob-benchmark` @ ab084a6). The classifier only names the semantic relation. Every write decision stays with `backend/brainbob/maintain.py`'s deterministic rules (`_covers`, `_pair_action`, locks, ACL). The production default judge is unchanged.

**Status: data and code are ready, and the GPU run has not happened yet.** Until a run's `run_meta.json` exists, no model results exist.

## Files

| File | Purpose |
| --- | --- |
| `gen_data.py` | Synthetic data: freezes stories and the template split, then teacher generation, blind teacher check, manual overrides, dedupe, balance. Writes `train.jsonl`, `dev.jsonl`, `stories.json`, `review_queue.jsonl` and `manifest.json`. |
| `label_overrides.json`, `data_review.md` | Manual label decisions and spot-check notes. |
| `bob_format.py` | Jerel's model input format, copied verbatim, plus his strict verdict rule. |
| `bob_inputs/` | `benchmark.py export` output for eval (60) and dev (12): inputs only, no gold. |
| `job_all.py` | One HF Jobs script. It does what a separate `train.py` would (base eval → LoRA SFT → tuned eval → push → reload), so there is no separate `train.py`. Data is embedded via `--pack`. |
| `predict.py` | Standalone re-prediction for base or base+adapter on any exported `inputs.jsonl`. |
| `bridge.py` | `make_judge(callable_or_endpoint)`, for `maintain.ingest(judge=...)` in isolated runs. |
| `threshold_report.py` | Thresholded label-probability coverage/precision on a labeled set. |
| `HANDOFF_JEREL.md`, `eval_inputs_template.jsonl` | Evaluation handoff. |
| `../../backend/tests/test_memops_bridge.py` | 28 no-model tests: format equality with every Bob export row, the parser, conservative failure, approved/stale/tentative/locked rules, no deletion. |

## Commands

Run everything from the repository root. The laptop never loads a model: GPU work runs only on HF Jobs.

```sh
# 1. data (Crusoe teacher, cached in .cache/; needs ~/.config/crusoe/api.key)
backend/.venv/Scripts/python experiments/memops-small/gen_data.py --train 150 --dev 30

# 2. Bob inputs (from Jerel's branch without touching this worktree's branch)
git fetch origin codex/bob-benchmark
git worktree add ../bob-wt origin/codex/bob-benchmark          # or: git archive origin/codex/bob-benchmark benchmarks/bob | tar -x -C <dir>
python3 ../bob-wt/benchmarks/bob/benchmark.py export --split eval --out /tmp/bob-eval-inputs
python3 ../bob-wt/benchmarks/bob/benchmark.py export --split dev  --out /tmp/bob-dev-inputs
cp /tmp/bob-eval-inputs/inputs.jsonl experiments/memops-small/bob_inputs/eval_inputs.jsonl
cp /tmp/bob-dev-inputs/inputs.jsonl  experiments/memops-small/bob_inputs/dev_inputs.jsonl

# 3. embed data + inputs into job_all.py, then run the no-model tests
python experiments/memops-small/job_all.py --pack
cd backend && .venv/Scripts/python -m pytest tests/test_memops_bridge.py -q && cd ..

# 4. base eval + train + tuned eval + push + reload: one job (after `hf auth login`)
hf jobs uv run --flavor l4x1 --timeout 30m --secrets HF_TOKEN -e MEMOPS_HUB_REPO=<hf-user>/memops-small-qwen3-0.6b-lora experiments/memops-small/job_all.py
hf jobs logs <job-id>          # files are also printed between =====FILE <name> BEGIN/END=====

# 5. fetch outputs
hf download <hf-user>/memops-small-qwen3-0.6b-lora --include "runs/*" --local-dir experiments/memops-small/out

# 6. score locally with Jerel's scorer (stdlib, no model)
B=../bob-wt/benchmarks/bob/benchmark.py; R=experiments/memops-small/out/runs/<run_id>
python3 $B score --predictions $R/base_eval.jsonl  --model 'Qwen/Qwen3-0.6B@c1899de289a04d12100db370d81485cdf75e47ca' --out $R/base-score.json
python3 $B score --predictions $R/tuned_eval.jsonl --model 'Qwen/Qwen3-0.6B@c1899de2+<hf-user>/memops-small-qwen3-0.6b-lora@<commit>' --out $R/tuned-score.json
python3 $B compare --base $R/base_eval.jsonl --tuned $R/tuned_eval.jsonl --out $R/comparison.json
python3 $B score --split dev --predictions $R/tuned_dev.jsonl --model ... --out $R/tuned-dev-score.json

# 7. thresholded probabilities, calibrated on labeled dev only
python experiments/memops-small/threshold_report.py --probs $R/label_probs.json --key tuned_dev --gold ../bob-wt/benchmarks/bob/dev.jsonl --sweep

# 8. reload the adapter elsewhere (GPU)
hf jobs uv run --flavor l4x1 --timeout 15m --secrets HF_TOKEN experiments/memops-small/predict.py \
    --inputs experiments/memops-small/bob_inputs/dev_inputs.jsonl --adapter <hf-user>/memops-small-qwen3-0.6b-lora --out tuned_dev_rerun.jsonl
```

`hf jobs uv run` CLIs from 2026 ship local files named on the command line through a bucket mounted at `/data`. That bucket is also where `job_all.py` copies its outputs when the mount is writable. Older CLIs ship only the script, which is why `job_all.py` embeds its data. If no local copy exists, `predict.py` downloads `code/job_all.py` from the adapter repo.

## Configuration (as issue #7's starting settings; not tuned)

Transformers 4.56.2, PEFT 0.17.1, TRL 0.23.0, torch 2.8.0, accelerate 1.10.1, datasets 4.1.1, huggingface_hub 0.35.3, pinned in the PEP 723 header. The prompt is non-thinking (`enable_thinking=False`). Loss covers the completion only (`{"verdict":"…"}<|im_end|>`). `max_length` is 512: with the real tokenizer the longest example is 254 tokens, and an over-length example would be dropped rather than truncated. LoRA r=16, alpha=32, dropout=0.05 on q/k/v/o. BF16 is used when supported. Microbatch 4 × accumulation 4, learning rate 2e-4 with a linear schedule and no warmup, 1 epoch (9 optimizer steps on 144 rows), seed 42. A wall-clock stop at 5 minutes saves state before stopping, with checkpoints every 3 steps and a 30-minute job timeout. Evaluation decodes greedily with `max_new_tokens=16`.

Label probabilities: force the prefix `{"verdict":"`, take the next-token log-probabilities of each label's first token (`same` / `conf` / `un` in the Qwen3 tokenizer), and normalize with softmax. A call below the threshold (0.8 by default) becomes `None`, which `maintain` treats conservatively. The 0.8 is a preset. Calibrate it on labeled dev data before relying on it, and never on eval outcomes.

## Budget (envelope $25; this issue buys no compute by itself)

| Item | Basis | Cost |
| --- | --- | --- |
| Data generation + blind check | 304 calls, 90,329 in / 25,304 out tokens × $0.30 / $2.40 per 1M (Crusoe list) | **$0.088** |
| Training + both evals (planned) | l4x1 $0.80/h × ≤30 min timeout; expect ~10 min including install | ≤ $0.40 (expected ~$0.15) |
| Retries reserve | | remaining |
| **Total so far** | | **$0.088** |

Fill in the actual GPU minutes from `run_meta.json` (`elapsed_job_s`, which covers this process only) and from the HF billing page, which includes image pull and dependency install.

## Limitations

- The data is small and synthetic: 144 train rows, written and blind-checked by one teacher model. The spot check was done by an agent, not an independent human. See `data_review.md`.
- Conflict has 44 training rows against 50 for the other labels. Hedged "might move to" statements are labeled `unrelated` by our policy.
- The Bob eval is 60 public, agent-authored pairs. Its intervals are diagnostic and do not prove generalization. A strict parse makes any extra key, such as `reason`, invalid, which penalizes a base model that explains itself.
- The bridge feeds the tuned model Bob-format messages (`pair-<mem id>`, `source_id` defaults to `candidate`), not `maintain.llm_judge`'s production prompt. Operation counts in `syn_dev.json` assume an approver, matching scopes and unlocked approved old memories. The real outcome comes from `maintain` rules in an integration run with real model outputs, which is not done yet.
- Cost and latency come from a single L4 run. Warm latency excludes the first 2 calls. Cold setup counts tokenizer and weight load only.

## Related work

- Jiang, Li & Li, "Jev-Mem: System-One-Controlled Agentic Memory for Efficient AI Agents", arXiv:2609.23986 (2026). A lightweight System-One controller makes the fast memory decisions, and slower reasoning is used only where needed. We borrow the division of labor: the small checker gives a typed decision with a calibrated confidence, and the policy is executed by code (`maintain` rules), with low-confidence calls falling back to the conservative path.
- Memory-R1 (arXiv:2508.19828): learned ADD/UPDATE/DELETE/NOOP memory managers at 3B–14B. Their results do not validate a 0.6B model, and this experiment has no DELETE.
