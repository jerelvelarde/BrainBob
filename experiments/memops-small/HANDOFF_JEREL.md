# Handoff to Jerel: held-out evaluation of the memops-small checker (#7 ↔ #4)

We follow the contract in `benchmarks/bob/README.md` on `codex/bob-benchmark` (commit ab084a6; `benchmarks/bob/` is identical to b672fd7 except for the README). Nothing new is needed from you, apart from the points below.

## Inputs (yours → us)

- We use your `benchmark.py export` output **unchanged**: `export --split eval` gives 60 pairs, `--split dev` gives 12. Each row has `id`, `input_sha256`, `existing`, `candidate` and `messages`, and no gold. Copies are in `bob_inputs/` here, together with the export manifests.
- `eval_inputs_template.jsonl` shows the row shape with placeholder text, in case you author more pairs. The format is identical to your export. Gold stays with you.
- Both models receive exactly your `messages`. Our training data was converted to that format: same system prompt, same user JSON field order (`id`, `existing{text,date,id}`, `candidate{text,date,source_id}`). `bob_format.py` mirrors your renderer. A test re-renders all 72 exported rows and checks each one byte for byte, and also checks your `input_sha256`.

## What the model never saw

- `benchmarks/bob/eval.jsonl`, `make_cases.py`, `worlds.json` and anything under `bobbench/` were not read while the training stories were written. The training stories come from our own 42 templates (`gen_data.py`). I read your `dev.jsonl` labels after training data was generated, only to check format and whether dev contains hedged statements (it does not). Dev was not used for training.
- The adapter is frozen (saved, hashed, pushed) before any tuned prediction runs. Base and tuned run in the same job, on the same GPU, with the same settings: greedy, non-thinking, `max_new_tokens=16`.

## Outputs (us → you)

One HF Jobs run (`job_all.py`) writes the following to `runs/<run_id>/` of the private Hub repo. Copies of the same files are printed in the job log.

| File | Content |
| --- | --- |
| `base_eval.jsonl`, `tuned_eval.jsonl` | One row per eval input: `{"id","input_sha256","response","latency_ms"}`. `response` is the raw decoded text. If inference fails, the row has `"error"` instead of `response`. A verdict is never filled in. |
| `base_dev.jsonl`, `tuned_dev.jsonl` | The same format, for your 12 dev inputs. |
| `run_meta.json` | Base model + resolved revision, adapter repo/commit/sha256, training config and loss log, GPU name, elapsed time, package versions, embedded-data hash. |
| `label_probs.json` | Per-row label probabilities (forced `{"verdict":"` prefix). Diagnostic only; not part of the scored predictions. |

Scoring is yours, or we run your scorer locally (stdlib only, no model):

```sh
python3 benchmarks/bob/benchmark.py score --predictions base_eval.jsonl --model 'Qwen/Qwen3-0.6B@c1899de289a04d12100db370d81485cdf75e47ca' --out base-score.json
python3 benchmarks/bob/benchmark.py score --predictions tuned_eval.jsonl --model 'Qwen/Qwen3-0.6B@c1899de2+<adapter repo>@<commit>' --out tuned-score.json
python3 benchmarks/bob/benchmark.py compare --base base_eval.jsonl --tuned tuned_eval.jsonl --out comparison.json
```

A smoke check with fake predictions (constant labels, one malformed row, one error row) passed your hash and ID validation. It counted the malformed and error rows as invalid.

## Things to flag

- **Hedge policy**: our training data labels "X said it *might* move to Y" as `unrelated` (both statements can coexist), not `conflict`. Your cases may decide this differently.
- Our training rows use ids `train-NNN`, but the eval ids are `eval-NNN`. The id string is inside the user JSON, so the model sees it.
- If we tune anything after seeing eval outcomes, we will relabel your eval set as development and say so.
