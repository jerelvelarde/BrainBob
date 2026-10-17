# BrainBob readiness and scorecard

Assessment: October 17, 2026 (America/Los_Angeles). This combines the frontend checkout with concurrent backend/Bob work from remote `main` through `d85064d`, and the frozen diagnostics scorer from `codex/bob-benchmark@ab084a6`. Milestone histories were merged, not rewritten. No new GPU job, paid inference, deployment, or score submission was performed during this assessment.

**Decision: ready for offline integration checks and a controlled fine-tuned-checker experiment; not ready to claim a complete cross-benchmark scorecard or enable the tuned checker as the default memory writer.** Missing measurements remain unmeasured, not zero and not passing.

Completed verification: **473 Python tests**, **52 frontend tests**, and TypeScript checking passed. The latest main integration retains Bonan's recent-conversation audits and in-process HTTP probes alongside the local judge callback and canonical adapter pin. The integration subagent also passed a production build and the actual Next-to-Python HTTP/SSE smoke with deterministic model substitutes. [Commands, commit references, and limitations](../judging/readiness-20261017/verification.md).

## Verified scores

| Evaluation | Base / comparator | BrainBob / tuned | Meaning and limitation |
| --- | --- | --- | --- |
| Bob memory-pair diagnostic, 60 public synthetic cases | Qwen3-0.6B: 32/60 (53.3%), macro-F1 0.437 | LoRA: 42/60 (70.0%), macro-F1 0.694 | Independently rescored saved predictions; no new inference. Not the organizational Bob pilot. |
| Bob organizational pilot (`bobbench/`) | Always-refuse diagnostic: 0% legitimate, 25% macro CATS | No scored BrainBob/model run | Six worlds / 41 checkpoints; the refusal control made zero model calls and is not a BrainBob score. |
| Bob structured scorer smoke (`benchmarks/bob/`) | Append-only rules 15/18 | Maintained rules 18/18 | Existing deterministic reference evidence; neither system is the app or a trained model. |
| GateMem | Not measured | Not measured | Public data/code available; validated 91 episodes and 2,218 checkpoints. Full-app policy mapping and official scored inference remain. |
| MUMBench / MUM (AIM) | Not measured | Not measured | Bonan confirmed these are the same target. Official runnable data/evaluator not located. |
| CoMemBench | Not measured | Not measured | Workflow integration and evaluation access remain; project withholds evaluation oracles. |
| LongMemEval, modified 50-question subset | Full history 39/50 (78%) | BrainBob 35/50 (70%) | Historical run, different judge from official protocol; lower context use with lower observed accuracy. |
| LoCoMo, custom held-out split | No memory 85/760 (11.2%) | Memory and audited memory both 404/760 (53.2%) | Historical custom evaluation; audit produced no accuracy gain. |
| Rusty Rod synthetic correctness, 76 questions | Append-only 67/76 | Maintained 68/76 | Historical accuracy gain not significant; current-fact updates improved 0/13 to 12/13. |
| BANKING77, 300 held-out tasks | Ordinary memory 202/300 | Audited memory 202/300 | Historical audit delta 0.0 points, paired 95% interval [-1.3, +1.3]. |

Sources: [independent MemOps rescore](../judging/readiness-20261017/memops-comparison.json), [original prediction artifacts](../experiments/memops-small/out/runs/20261017-210457/), [structured control evidence](../judging/bob-pilot-b672fd7/README.md), [historical evaluation report](evaluation-report.md), and [external benchmark protocol/runbook](external-benchmark-readiness.md). These tests measure different capabilities; averaging them into one score would conceal missing coverage.

## Fine-tuned checker decision

The saved base/tuned predictions have matching frozen input hashes and complete 60-case coverage. Rescoring reproduces **17 improved / 7 regressed**, a **+16.7 percentage-point** accuracy delta, and template-cluster bootstrap 95% **[+5.0, +28.3]** (20 templates, 2,000 resamples, seed 42). Both have zero invalid JSON outputs. The interval characterizes this small authored dataset, not independent real-world generalization.

The tuned model identifies **10/20 conflicts**, compared with zero for the base. It misses ten conflicts (nine as unrelated, one as same), and calls **5/40 non-conflicts** conflicts (four same, one unrelated). Aggregate accuracy alone therefore does not justify authorizing destructive maintenance. Keep the bridge opt-in and evaluate false retirements alongside detection and preserved valid facts.

Saved-response replay through the real `maintain.ingest` policy confirms the risk: when the harness supplies an approved, authorized, newer candidate against an unlocked old memory, those five false conflicts retire the existing record. The same outputs against locked memories, tentative candidates, or a writer without approval yield zero retirements. This is a controlled policy intervention with provided input facts, not fresh inference or measured end-to-end extraction quality. Production activation remains blocked on the overwrite gate; an observe-only comparison is appropriate. [Replay evidence and reproduction](../experiments/memops-small/POLICY_REPLAY.md).

Recorded inference latency p50/p95 is 307.78/339.75 ms base versus 349.46/360.99 ms tuned, on the same unoptimized L4 setup. These are read from saved predictions, not measured on this machine. Run metadata records 8.6 seconds training, 103.8 seconds in the job process and estimated process GPU cost $0.0231; Bonan reports 137 seconds total running time and approximately $0.03 GPU plus $0.09 teacher. Process and whole-job timing have different scopes, and neither is a newly verified bill.

The adapter identity is resolved: Bonan confirmed canonical revision `b904e6ec0baea37bf70209093b8c59332d3c450a`, matching the committed metadata and reload checks. He confirmed unchanged weights across the other mentioned repository revisions; metadata records SHA-256 `21588c9e975fe23d6c8e73db35bea23cd8834e8e1259ce6184d29472c7a19a0b`. This identity confirmation is from the model owner, not an independent download of the private weights. The supplied [Hub page](https://huggingface.co/Guangze/memops-small-qwen3-0.6b-lora) was inaccessible to the browser tool. A local GPU callable through `bridge.make_judge` is supported; no standing inference endpoint is required. See [handoff instructions](finetune-handoff.md).

## Work assigned and acceptance gates

| Workstream | Owner in this assessment | Gate |
| --- | --- | --- |
| UI → backend | `live_integration` subagent | Same-origin HTTP and SSE reach the actual Python service; ingest, ask, feedback, correction, inspection, member isolation and reconnect checks pass. Model responses in offline smoke remain explicitly fake. |
| External benchmarks | `benchmark_readiness` subagent | GateMem adapter sees no labels/future turns; hashes and completeness are recorded; unavailable official MUMBench/CoMemBench evaluation stays marked blocked. |
| Bob pilot | `bob_pilot` subagent | Existing six worlds and scorer validated; inaccessible citations and failed operations cannot pass; real backend adapter resolves and is tested. |
| Fine-tuning integration | Root + `benchmark_readiness` | Saved predictions independently scored; maintenance bridge tested with provenance and deterministic policy guards; canonical checkpoint pinned; GPU/private Hub access still needed for fresh inference. |
| Real model and official scores | Bonan + project owners | Private checkpoint access/compute, configured inference and judging credentials, full-app external adapter, and official evaluator access. These cannot be inferred from passing unit tests. |

Priority order: complete a real-provider UI demo; run the LoRA checker as an opt-in maintenance candidate on fresh cases; run the organizational Bob pilot with comparable conditions; finish GateMem full-app mapping and official judging; obtain MUMBench and CoMemBench evaluation access. Maintain separate score cells and disclose unsupported surfaces and data exposure.

The app still uses client-selected demo identity, not authenticated multi-user login. The permission regression tests check behavior within that demo contract; they do not establish an authentication boundary. SQLite, NemoClaw and Switchyard remain separate roadmap items and are not prerequisites for the saved-prediction rescore.

The organizational refusal control is saved with [scorecard and traces](../judging/readiness-20261017/organizational-refusal-control/scorecard.md). It exercises scorer 0.2, demonstrates that universal refusal fails legitimate utility, and lists unsupported inspection surfaces. Its configured default answer-model name appears in run metadata, but the control's actual call count and token count are zero. Do not attribute its CATS to that model.
