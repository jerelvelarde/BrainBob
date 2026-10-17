# Bob: the smallest executable benchmark

For [#4](https://github.com/jerelvelarde/BrainBob/issues/4) and Bonan's [one-hour model experiment #7](https://github.com/jerelvelarde/BrainBob/issues/7). Python 3.10+, standard library only. Run from the repository root. No API keys, GPU, package installation or backend changes needed to run the scorer and reference pilot.

Two separate measurements:

| Measurement | Cases | What it measures |
| --- | --- | --- |
| Memory-pair classification | 60 evaluation pairs, balanced 20/class; 12 separate development pairs | `same`, `conflict`, `unrelated` predictions from the base or tuned model |
| Shared-memory public pilot | 6 structured worlds, 18 checkpoints | Scoped assembly, authority changes, cross-org publication, revocation, retention, correction propagation |

**These are public synthetic diagnostics, not the complete Bob Core benchmark or a hidden test.** The reference pilot is a deterministic rules implementation, not BrainBob or a trained model. Structured facts intentionally remove extraction/QA cost from this first slice. Existing 30-scenario and external benchmark results retain their original labels. See [the broader spec](../../docs/bob-benchmark-spec.md).

## Bonan: start here

Export model-visible evaluation inputs (gold and template IDs are omitted):

```sh
python3 benchmarks/bob/benchmark.py export --split eval --out /tmp/bob-eval-inputs
python3 benchmarks/bob/benchmark.py export --split dev --out /tmp/bob-dev-inputs
```

Directories must be new; do not overwrite a previous run. Each `inputs.jsonl` row has `id`, `input_sha256`, `existing`, `candidate`, and the exact `messages` to pass to both models. Use the messages unchanged, non-thinking mode, greedy decoding, and the same short output limit/hardware for base and tuned. Context is short enough for the proposed 512-token setup, but verify with the actual tokenizer before running.

Return one JSONL prediction per input:

```json
{"id":"eval-001","input_sha256":"COPY_FROM_INPUT_ROW","response":"{\"verdict\":\"unrelated\"}","latency_ms":12.5}
```

The ID/response shown above illustrates the format; it is **not a supplied answer**. `response` can also be a parsed `{"verdict":"..."}` object. Preserve raw output when possible so malformed JSON is counted. On inference failure, return the same ID/hash plus `"error":"timeout"`; never substitute a correct-looking verdict. Latency is optional, in milliseconds, measured by the caller. Export contains no expected labels.

A minimal prediction loop around your existing local model function:

```python
import json, time
with open('/tmp/bob-eval-inputs/inputs.jsonl') as src, open('/tmp/base.jsonl', 'w') as dst:
    for line in src:
        row = json.loads(line)
        result = {'id': row['id'], 'input_sha256': row['input_sha256']}
        started = time.perf_counter()
        try:
            result['response'] = generate(row['messages'])  # your base/adapter inference
        except Exception as exc:
            result['error'] = type(exc).__name__ + ': ' + str(exc)
        result['latency_ms'] = (time.perf_counter() - started) * 1000
        dst.write(json.dumps(result) + '\n')
```

Score and compare:

```sh
python3 benchmarks/bob/benchmark.py score --predictions /tmp/base.jsonl --model 'Qwen/Qwen3-0.6B@ACTUAL_REVISION' --out /tmp/base-score.json
python3 benchmarks/bob/benchmark.py score --predictions /tmp/tuned.jsonl --model 'BASE_REVISION+ACTUAL_ADAPTER_HASH' --out /tmp/tuned-score.json
python3 benchmarks/bob/benchmark.py compare --base /tmp/base.jsonl --tuned /tmp/tuned.jsonl --out /tmp/bob-comparison.json
```

Development scoring uses `score --split dev`. The default scored set is `eval`. Reports include accuracy with counts, macro-F1, a confusion matrix including invalid outputs, missing predictions, latency/sample counts, per-case outcomes, source/input hashes and commit provenance. Comparison reports improved/regressed cases, percentage-point delta, and a seeded bootstrap interval clustered by the 20 story templates. With this small public set, intervals are diagnostic, not proof of broad generalization.

Unknown or duplicate IDs and wrong input hashes invalidate a submission. Missing predictions and inference errors remain failures in the original denominator. Only a JSON object with exactly one `verdict` key is accepted. Markdown/code fences/explanatory prose are invalid outputs. This strict metric is intentionally separate from any permissive production parser.

## How to improve the score legitimately

Use `dev.jsonl` and its labels for prompt/training feedback. Generate training cases with different story/template skeletons, with all three semantic relations and hard negatives: different entities, different attributes, historical periods, negation and units. Treat equivalent wording as `same`; distinguish real conflicts from compatible facts. Keep JSON generation short and reliable. Approval/locks remain code decisions, not extra semantic labels.

Freeze the adapter before running `eval`. Do not train on `eval.jsonl`, inspect its errors and then call the next run held-out, or remove failures. Public evaluation gold is committed separately from model inputs so the scorer is reproducible; this is process separation, not a secret or adversarial isolation boundary. The cases are agent-authored with automated validation, **not independently human-annotated**. They need external review before a stronger release claim. If exposed to tuning, label them development and author a new disjoint evaluation set.

`make_cases.py` is the explicit authoring source. It creates 20 evaluation story templates × 3 relations and four separate development templates × 3 relations. IDs are shuffled independently of class. Lexical patterns remain a limitation of the authored set. Regeneration is deterministic; edits require a new dataset revision and rescoring, never silently changing gold to improve results.

## Shared-memory pilot: one command

```sh
python3 benchmarks/bob/benchmark.py pilot --out /tmp/bob-maintained
```

Additional controls:

```sh
python3 benchmarks/bob/benchmark.py pilot --adapter append-only --out /tmp/bob-append
python3 benchmarks/bob/benchmark.py pilot --adapter none --out /tmp/bob-none
python3 benchmarks/bob/benchmark.py pilot --adapter always-refuse --out /tmp/bob-refuse
python3 benchmarks/bob/benchmark.py pilot --adapter unfiltered --out /tmp/bob-unfiltered
```

`worlds.json` includes incrementally delivered facts and trusted policy, plus evaluator-only expected claims/allowed sources. Policies model separate Rusty Rod-like internal scopes and an Atlas-like client publication scope; they are synthetic, not actual server identities. The runner removes gold before calling adapters, creates a new component per world, and asks for fresh session context at each checkpoint. No model reasoning is hidden in the reference implementation.

The maintained reference accepts only approved facts from policy-authorized writers, supersedes matching scope/key records, invalidates transitive dependent summaries, applies read grants at delivery time and retains valid facts absent from an audit. Append-only uses the same ingestion approval/read policy but retains old versions and chooses the first matching record; this baseline is explicitly simple. None/always-refuse return no context. Unfiltered retains maintenance but bypasses read policy as a negative control.

A successful checkpoint requires exactly the expected structured claims, citations to delivered and matching source facts, and no prohibited source or known protected value in either context or output. Reusing a public source ID for a secret value still fails. Duplicate answer claims and extra schema fields fail. Exact-value checking does not detect arbitrary semantic paraphrase leakage. Raw malformed output remains a failure; exact protected values are still scanned. Fresh sessions are an adapter contract; this runner does not prove sandbox/process isolation for external adapters.

Each run writes the spec's eight artifacts: manifest, configuration, events, operations, contexts, outputs, metrics and limitations. Metrics show raw task success and per-world/per-stratum results, **not the complete Core CATS aggregate**. Successful reference controls are scorer/fixture sanity checks, never model-performance evidence. The adapter's internal mutations are not independently inspected. Model cost is zero for built-in deterministic controls; external adapter cost is unknown unless reported separately.

## Bring a real memory system

Use `--adapter your_module:factory` with an importable Python module. The factory takes a deep copy of `world['policy']` and returns an object with:

```python
def ingest(event):
    # Incremental fact / trusted revoke / audit event, no gold.
    ...

def session(task):
    # task: {type, id, principal, keys}; no hidden history in the answerer.
    return {
        'context': [{'key': 'launch', 'value': '2026-11-06', 'source_id': 's1'}],
        'claims': [{'key': 'launch', 'value': '2026-11-06', 'source_id': 's1'}],
    }
```

Return empty claims for unavailable/denied facts. Do not import the oracle or repair the system in the adapter. The candidate must implement cross-org, revocation and dependent invalidation itself to pass those worlds. Missing capability is a failure/unsupported result, not license to add gold-derived filters. Adapter code is trusted Python, not an isolation sandbox. Session errors count as failures; ingestion errors abort the run and must be reported as infrastructure/candidate failures. No wall-time limits are enforced for external Python adapters in v0.1.

## Verify

```sh
python3 -m unittest discover -s benchmarks/bob -p 'test_*.py' -v
```

The tests deliberately submit wrong/stale answers, invented citations, protected context, forged provenance, malformed output, constant-label predictions, omitted cases and duplicate IDs. They also verify gold is not passed to adapters and that the always-refuse/unfiltered controls fail their intended dimensions. No cloud/model claims arise from these tests.
