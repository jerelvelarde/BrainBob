# External benchmark readiness — 2026-10-17

We can validate GateMem data offline and export model predictions through an incremental adapter. We do **not** yet have BrainBob scores on GateMem, MUMBench, or CoMemBench. The existing Rusty Rod correctness results are internal results; they cannot fill these score cells. Model inference and official scoring were not run during this readiness pass.

Bonan's [access update](external-benchmark-status.md) confirms GateMem was not run
today (official GPT-4o judging budget and a full-app adapter remain), and no usable
public dataset/evaluator was located for MUMBench or CoMemBench. Those discovery
limits are not proof that a release does not exist. No external score is claimed;
these are follow-up work after the four submission P0s. The published Bob pilot
and [its review](bob-pilot-review-20261017.md) remain separate internal evidence.

| Target | Our measured score | Ready now | Remaining blocker |
| --- | --- | --- | --- |
| GateMem | Not measured | Full released data validated; incremental prediction export and append-only extraction baseline implemented | Test the deployed model; implement application-equivalent contextual ACL/deletion adapter; run official judging on complete domain predictions |
| MUMBench (AIM) | Not measured | Primary paper, schema, and metrics identified | Obtain/version the actual dataset and evaluator; implement chronological multi-user CRUD operation traces |
| CoMemBench | Not measured | Primary project release and evaluation requirements identified | Domain-native workflow executors, typed handoff integration, and evaluator/oracle access |
| “MUM” | Same target as MUMBench | Confirmed by Bonan through Jerel | Count once; no separate MUM score |
| Bob Benchmark | See Bob pilot artifacts separately | Internal benchmark work has separate ownership | Bob Benchmark and the existing Rusty Rod suite must retain their separate identities |

## Exact benchmark identities

[GateMem](https://github.com/rzhub/GateMem) tests legitimate utility, access violations, and recovery of explicitly forgotten information across four domains. Its headline MGS combines utility with both violation rates: `U × (1 − A) × (1 − F)`. Released files retain legacy categories `utility`, `privacy`, and `safety`. Prediction generation must not see checkpoint grading annotations. Our adapter strips them, along with turn-level annotated memory operations and record references.

[MUMBench is introduced by AIM](https://arxiv.org/html/2609.12320v1), covering 672 sequential multi-user interactions across coding, support, education, and travel. Report strict operation accuracy, state-aware operation accuracy, and visibility classification separately; payload/retrieval judgments are additional measures. The paper's 96.0% visibility, 58.8% strict, and 70.5% state-aware figures describe AIM, **not BrainBob**. This pass did not locate a downloadable official dataset/evaluator from the paper or targeted repository searches. This is a discovery blocker, not a claim that no release exists. Generated lookalike examples would be an internal diagnostic, not MUMBench.

[CoMemBench](https://comembench.world/) publishes 800 workflow families and matched pollution experiments. Its SR, VNCR, VHS, and ICS metrics depend on domain-native verification and successful handoffs. The project says evaluation oracles and pollution plans remain held out. ICS is blank when its denominator is below ten; infrastructure failures need separate reporting. A QA-only adapter or synthetic privacy fixture cannot reproduce these results. Obtain the official evaluation path and provision the tool, repository, retrieval, and formal-math execution environments before claiming coverage.

## Evidence collected here

GateMem upstream checkout inspected at commit `a983828b3bb7565e16e25ac8cdc2fc1982633b0b`. Offline validation found:

| Domain | Episodes | Checkpoints | Utility | Access (`privacy`) | Forgetting (`safety`) |
| --- | ---: | ---: | ---: | ---: | ---: |
| medical | 21 | 579 | 210 | 192 | 177 |
| office | 17 | 547 | 154 | 171 | 222 |
| education | 30 | 540 | 180 | 180 | 180 |
| household | 23 | 552 | 184 | 184 | 184 |
| total | 91 | 2,218 | 728 | 727 | 763 |

The machine-readable evidence is `bench/evidence/gatemem-data-preflight.json`. These counts validate data availability and checkpoint joins; they measure no model capability. `bench/gatemem.py preflight` additionally emits SHA-256 hashes of both input files. Tests in `bench/tests/test_gatemem.py` use synthetic plumbing fixtures solely to verify no future turns/labels reach the adapter, episode isolation, fail-closed joins, valid prediction shapes, trace fidelity, and incomplete-run preservation.

## Runbook

From the repository root, clone the official toolkit into an untracked data location and pin the inspected revision:

```sh
git clone https://github.com/rzhub/GateMem.git backend/data/GateMem
git -C backend/data/GateMem checkout a983828b3bb7565e16e25ac8cdc2fc1982633b0b
backend/.venv/bin/python bench/gatemem.py preflight --data-dir backend/data/GateMem/bench/data/medical
backend/.venv/bin/python -m pytest bench/tests/test_gatemem.py -q
```

Preflight requires only the standard library and makes no API calls. The `predict` command **does make model calls**, using the configured BrainBob `curator` and `agent` routes. Keep the judge and prompts fixed across Bonan's base/fine-tuned comparisons. Set role-specific configuration as documented in the model handoff instructions; never include keys in result artifacts.

```sh
export GATEMEM_TOOLKIT="$PWD/backend/data/GateMem"
backend/.venv/bin/python bench/gatemem.py predict \
  --data-dir "$GATEMEM_TOOLKIT/bench/data/medical" \
  --adapter adapters.gatemem_brainbob:ExtractedMemoryBaseline \
  --limit-episodes 1 \
  --output backend/results/gatemem-medical-base-pilot
```

The included `ExtractedMemoryBaseline` uses the real BrainBob extractor and BM25 store with the upstream answer prompt/policy. It is **append-only extraction with prompt-level governance**, not the complete maintained app. It does not map contextual access permissions into the application ACL or execute deletion requests. Its eventual score must carry this variant label. Removing `--limit-episodes` runs a complete domain; repeat for all four domains. Invalid model JSON stops the run rather than converting an infrastructure/parsing error into a scored refusal.

To evaluate the full app, provide `--adapter your_module:YourFactory` implementing:

- `reset({episode_id, domain})`: a fresh isolated memory store.
- `ingest({turn_id, timestamp, speaker: {principal_id, role}, text})`: exactly the observed turn, with no gold memory operations.
- `query({checkpoint_id, episode_id, as_of_turn_id, query_text, asker, relationships})`: only requester-relevant scaffold relationships and current query; return `action`, `answer`, optional `answer_structured` and `used_record_ids`.

Query outputs are never ingested as conversation evidence. Do not map our internal `m1` IDs to GateMem record IDs by guessing; they are different namespaces. Preserve prompt-visible memory traces so context exposure can also be audited.

Each prediction run writes an immutable new directory with `predictions.jsonl` and `manifest.json`: dataset hashes, selected IDs, completeness, model routes, Git revision/dirty flag, and an explicitly null score. Partial runs remain `failed_incomplete`; reruns must use a new directory. Cost for an unknown model/endpoint is not verified from the current fallback tariff.

For complete predictions, use the [official external scorer](https://github.com/rzhub/GateMem/blob/main/docs/prediction_format.md) in the pinned upstream environment. Install its dependencies separately, then run (credentials must already be configured):

```sh
python "$GATEMEM_TOOLKIT/bench/scripts/score_predictions.py" \
  --data_dir "$GATEMEM_TOOLKIT/bench/data/medical" \
  --predictions "$PWD/backend/results/gatemem-medical-base/predictions.jsonl" \
  --out_dir "$PWD/backend/results/gatemem-medical-base-scored" \
  --use_llm_judge --judge_provider openai --judge_model gpt-4o \
  --judge_temperature 0 --judge_concurrency 4
```

That scorer command also makes paid calls. A one-episode pilot remains a subset; it must not be submitted as a complete domain or a leaderboard score. Rule-only scoring is auxiliary. No leaderboard publication or external message was performed here.

## Existing measured comparator

`bench/results/20261017-110432/summary.json` records a 50-question LongMemEval slice: BrainBob **35/50 (70%)**, full history **39/50 (78%)**. Average answering context is 2,681 versus 108,946 tokens, approximately 97.5% smaller, with lower observed answer accuracy. It reports 76 extraction parse failures/empty extractions and no unfinished tasks. The companion report discloses a different judge from the official setup. Treat this as an existing modified subset experiment, not an official full benchmark result or evidence the new model is ready. The reported total cost includes replayed cache usage, not just new billing.

The fetched backend now has dynamic multi-organization policy primitives. The remaining GateMem gap is mapping its observed domain relationships, consent, and deletion requests into that engine without importing gold labels; it is not a claim that the backend lacks all dynamic ACL support.

## Work queue before a scorecard can be called complete

1. **Model owner / Bonan:** the local LoRA maintenance checker and frozen-pair predictions have been supplied; use confirmed canonical revision `b904e6ec0baea37bf70209093b8c59332d3c450a` and arrange private Hub/GPU access for repeat inference. A permanent endpoint is not required. Use the opt-in callable bridge and fixed judge/prompt settings, then evaluate downstream maintenance effects. See [fine-tuning handoff](finetune-handoff.md).
2. **Backend evaluation owner:** implement a production-equivalent GateMem adapter for contextual principals, scope changes, and explicit forgetting; retain the current extraction baseline as a named control. Run one pilot then complete four-domain inference and official judging.
3. **MUMBench owner:** resolve release access/revision, preserve domain chronology and shared user state, capture predicted CRUD/payload/visibility independently of expected actions, and reproduce the paper's distinct metric definitions.
4. **CoMemBench owner:** establish evaluator access, native tool environments, typed/versioned receipts and pollution pairing; report unregistered/unsupported cells blank until real runs exist.
5. **Bob owner:** finish the independently versioned internal pilot and scoring gates; do not count inspired fixtures toward any external benchmark coverage.
