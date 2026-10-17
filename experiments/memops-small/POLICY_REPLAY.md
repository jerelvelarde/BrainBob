# Saved-response maintenance policy replay

This is an offline integration diagnostic. It replays the saved 60-pair base and tuned responses from run `20261017-210457` through the actual `brainbob.maintain.ingest` code. It makes no model calls and activates no production configuration.

The tuned response set improves pair classification from 32/60 to 42/60, but it is not ready for unrestricted automatic replacement of approved, unlocked memories:

| Controlled policy context | Base records retired | Tuned records retired | Tuned false-conflict retirements |
| --- | ---: | ---: | ---: |
| Approved, authorized, newer, unlocked | 0 | 15 | **5** |
| Same context, existing record locked | 0 | 0 | 0 |
| Candidate marked tentative | 0 | 0 | 0 |
| Candidate author lacks approval rights | 0 | 0 | 0 |

The five false-conflict cases are `eval-007`, `eval-011`, `eval-015`, `eval-035`, and `eval-048`. They retire an existing record under the first controlled context even though its annotated semantic relation is not conflict. The base model predicts no conflicts; its zero retirements do not imply better update quality. For the tuned model, the 15 conflict predictions become tentative in each conservative context. Classification accuracy stays 42/60 across those policy interventions.

`policy-replay-evidence.json` records input/output hashes, model identities, observed actions and failure IDs. Full local traces are saved alongside the original responses under ignored `out/runs/20261017-210457/`. The evidence file is a replay result, not a claim of new model inference, production behavior rates, or a Bob CATS score.

## Reproduce

From the repository root:

```sh
backend/.venv/bin/python experiments/memops-small/replay_policy.py \
  --inputs experiments/memops-small/bob_inputs/eval_inputs.jsonl \
  --predictions experiments/memops-small/out/runs/20261017-210457/tuned_eval.jsonl \
  --gold benchmarks/bob/eval.jsonl \
  --model 'Qwen/Qwen3-0.6B@c1899de289a04d12100db370d81485cdf75e47ca+Guangze/memops-small-qwen3-0.6b-lora@b904e6ec0baea37bf70209093b8c59332d3c450a' \
  --out /tmp/tuned-policy-replay.json
backend/.venv/bin/python -m pytest backend/tests/test_maintain.py backend/tests/test_memops_bridge.py backend/tests/test_memops_policy_replay.py -q
```

Choose a new output filename for every replay. Inputs and predictions must have identical ID sets and matching input hashes; model messages must match the frozen export. Invalid responses take the existing conservative path. Gold labels are loaded only after all actions finish, and their input hashes are validated before diagnosis.

## Limits and integration change

Each pair starts with one supplied existing fact. Extraction is replaced with the supplied candidate fact, so this checks neither extraction quality nor multi-neighbor retrieval. Authority, approval rights, and lock state are explicit test interventions; the pair dataset does not supply those production circumstances. Responses were generated for the original exported IDs; a replay reuses those responses without asserting that the bridge's live IDs would produce identical inference.

A custom judge now exposes `model_id`, or the caller can pass `judge_model` to `maintain.ingest`. The bridge propagates its endpoint/model identity; unidentified callbacks are recorded as `custom:unidentified` rather than the production judge. Events and decisions retain that identity. The default production judge route and policy decisions are unchanged. For a frozen callback, pass the actual pinned identity explicitly:

```python
judge = make_judge(generator, model="base@revision+adapter@commit")
maintain.ingest(episode, store, acl, judge=judge)
```
