# Fresh frozen checker evaluation — round two

**Bonan: use `inputs.jsonl` unchanged after freezing the round-two checkpoint.**
This is a new 60-pair set (20 per label), with new scenario skeletons and 20
bootstrap clusters. It is separate from the organizational `bobbench/` pilot.
The original public 60 have now been inspected case by case and count as
development for round two. Preserve their historical round-one results.

## Handoff

1. Record the base revision, adapter revision/hash and completed training-data
   manifest **before opening these inputs**. Do not use them for training,
   prompt selection or threshold selection. If already exposed during tuning,
   disclose that exposure and treat this set as development too.
2. Pass each row's exact `messages` to base, round-one adapter and round-two
   adapter with the same prompt, decoding settings, output cap and hardware.
   Confirm token lengths with the actual tokenizer; never truncate silently.
3. Return every `id` and `input_sha256` with raw `response` (or `error`) and
   optional `latency_ms`, in the existing prediction format. Include failed
   requests. Freeze all comparison predictions before viewing the score report.
4. Jerel scores with the evaluator-local key. It is deliberately absent from
   Git, the Hub release and the public input file. Do not publish per-case gold
   until the frozen comparison is complete.

`manifest.json` commits to the exact input, gold, prompt and scorer SHA-256
hashes. Per-input hashes include IDs and fact metadata. IDs are shuffled
independently of labels; no gold, template IDs, or rationales are exported.

## Evaluator commands

Set `BOB_ROUND2_GOLD` privately to the saved `gold.jsonl` path. This wrapper
uses the existing `benchmark.py` scoring and bootstrap functions unchanged and
rejects a different gold file, input file or scorer. Reports must use new paths.

```sh
python3 benchmarks/bob/round2/evaluate.py score \
  --gold "$BOB_ROUND2_GOLD" --predictions /tmp/round2-predictions.jsonl \
  --model 'BASE_REVISION+ADAPTER_REVISION' --out /tmp/round2-score.json
python3 benchmarks/bob/round2/evaluate.py compare \
  --gold "$BOB_ROUND2_GOLD" --base /tmp/base-predictions.jsonl \
  --tuned /tmp/round2-predictions.jsonl --out /tmp/round2-comparison.json
```

Also compare round one versus round two on these **same new cases**. Do not
compare 42/60 on the old set against a new-set score as if only weights changed.
Report accuracy, macro-F1, invalid/missing outputs, conflict recall, false
conflicts and the paired interval. The classifier score does not establish safe
memory replacement; keep the policy gate in issue #6.

## Scope and limitations

The cases are agent-authored, not independently human-adjudicated. Exact fact
text was checked against the original pair dev/eval and committed round-one
train/dev files, with zero matches. Semantic categories necessarily overlap;
new wording and scenario skeletons do not prove distribution independence.
Round-two training data was unavailable for overlap checking. No model has been
run on this set during authoring. A second agent reviews label consistency;
that is an annotation check, not a model benchmark or human adjudication.

Public inputs and evaluator-local gold are process separation, not a security
boundary on the shared machine. This set is not part of the already published
Hub pilot v0.1. Publish it separately only after the comparison is frozen.
