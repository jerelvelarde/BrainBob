# BrainBob judging evidence

Current reading path: [solution and setup](../README.md) → [implemented architecture](../docs/architecture.md) → [evaluation report](../docs/evaluation-report.md). This sheet links recorded evidence; the documentation refresh did not run inference, retrain a model, or repeat the benchmarks.

## Submission

| Item | Recorded status |
| --- | --- |
| Public repository | [jerelvelarde/BrainBob](https://github.com/jerelvelarde/BrainBob) |
| Team | Jerel Velarde and Bonan Kou |
| Track | Shared Brain |
| Submitted commit / receipt | Not yet recorded; [remaining submission checks](submission-status.md). Individual evidence builds are listed below |
| Public live demo URL | Not yet recorded; the documented app runs locally |
| One-minute video | [Finished narrated 60-second recording](../docs/demo/live-one-minute-20261017/output/brainbob-live-60s-vo.mp4); [provenance and media checks](../docs/demo/live-one-minute-20261017/README.md) |
| Evaluation provenance | October 17, 2026; original inference builds and v0.3 rescore are recorded in the [report](../docs/evaluation-report.md#provenance) |

## Featured recording

The [one-minute narrated video](../docs/demo/live-one-minute-20261017/README.md) records the running localhost application with real Crusoe inference and fictional data. It shows Maya retrieving an existing approved Atlas deadline, inspecting its source, manually correcting a personal preference, and using the correction in a fresh session. The Atlas correction predates this recording. It is edited live footage, not a continuous take, an automatic audit demonstration, or a verified hosted release. Original captures came from a shared development checkout; [verification metadata](../docs/demo/live-one-minute-20261017/verification.json) discloses the build boundary.

## Working application evidence

The [live-workspace verification](live-workspace-20261017/README.md) records a real-provider development demonstration against implementation commits `348db5b`, `e77bb9a`, and `489919b`. The fictional company input is not a held-out benchmark.

| Capability | Recorded observation | Evidence |
| --- | --- | --- |
| Source ingestion and maintenance | All 29 fictional source conversations imported; 71 records, including one tentative and one retired record, across 22 scopes | [Import and correction results](live-workspace-20261017/live-results.json) |
| Authorized correction | November 6 record retired in favor of the approved November 13 record; Engineering estimate remained tentative | [Verification narrative](live-workspace-20261017/README.md#observed-memory-outcome) |
| Fresh-member handoff | Sales answer used November 13 and cited the approved date and acceptance records | [Saved answer](live-workspace-20261017/fresh-sales-answer.json) |
| Scope checks | 18 member views and event replays contained accessible references; selected unauthorized reads and writes returned 404/403 | [Access checks](live-workspace-20261017/access-checks.json) |
| Resumable import | Re-import skipped all 29 sources and preserved episode/memory hashes | [Repeat-import record](live-workspace-20261017/import-rerun.json) |
| Persistent retrace | Browser inspection of actual correction event #103, followed by return to live, without repeating inference | [Capture provenance](live-workspace-20261017/captures.json) |
| UI/provider integration | Real answer, follow-up draft, citations, source/model inspection, session files, and mobile layout exercised | [Verification and limitations](live-workspace-20261017/README.md#verification) |
| Offline integration | Next proxy → Python routes, store, ACL, and SSE exercised with deterministic model substitutes | [Earlier commands and results](readiness-20261017/verification.md) |
| NemoClaw / OpenClaw | Scoped adapter and MCP server implemented; sandbox integration and end-to-end validation pending | [Adapter runbook](../integrations/nemoclaw/README.md), [deterministic checks](nemoclaw-alignment-20261017/README.md) |
| Switchyard / SQL | Not integrated | [Current architecture](../docs/architecture.md) |

The member header is development identity selection, not authentication. These observations do not establish public deployment security, all live-stream cases, or complete session-cache revocation behavior. Desk conversations are browser-local; server memory and events persist.

## Corrected organizational pilot

Six synthetic worlds, 41 checkpoints, three replicates, common answering model/prompt. Inference build `5fcd554`; v0.3 scorer/oracle correction at `c241b6e`, applied to saved answers after results were inspected.

| Condition | Macro CATS v0.3 | Original v0.2 |
| --- | ---: | ---: |
| No memory | 25.0% | 25.0% |
| Full authorized history | 92.0% | 88.6% |
| Append-only | 67.9% | 67.3% |
| Maintained BrainBob | 71.9% | 74.4% |
| Always refuse | 25.0% | 25.0% |
| Unfiltered | 6.5% | 7.9% |

Maintained minus no memory: **+46.9 points [22.7, 71.1]**. Maintained minus append-only: **+4.0 points [−9.0, 18.2]**, inconclusive. Intervals are paired bootstraps clustered by world. CATS averages checkpoint replicates, worlds, and task sections; it is not a pooled count of correct answers.

Maintained memory had **0/111 protected-string disclosures in applicable answer/context records**; the unfiltered control had **111/111**. The original traces exercised search, record, and event surfaces. Source/history probes were empty, and export/session-cache probes were unsupported. A rescore does not add missing coverage.

[Corrected scorecard](../bobbench/results/20261017-141014/scorecard.v0.3.md) · [Machine-readable corrected results](../bobbench/results/20261017-141014/scorecard.v0.3.json) · [Original scorecard and traces](../bobbench/results/20261017-141014/) · [Methods and review caveats](../docs/evaluation-report.md#experiment-6-bob-organizational-pilot-proposed-benchmark-synthetic).

## Other measured results

| Experiment | Recorded result | Boundary of the claim |
| --- | --- | --- |
| Rusty Rod synthetic correctness | Maintained 12/13 correct updates vs append-only 0/13; 0/32 valid memories wrongly retired; accuracy 68/76 vs 67/76 | State maintenance improved; answer difference +1.3 points [−5.3, 7.9] is inconclusive |
| LoCoMo, 760 held-out questions | No memory 85/760; memory and audited memory both 404/760 | Context helps on this custom split; no audit gain |
| LongMemEval, modified 50-question subset | Memory 35/50 with 2,681 answer-context tokens; full history 39/50 with 108,946 | Context reduction with lower observed accuracy; no total pipeline savings claim |
| BANKING77, frozen policy, 300 tasks | Memory and audited memory both 202/300; audit delta 0.0 points [−1.3, 1.3] | Null result for this audit policy |
| Qwen3-0.6B relation diagnostic | Base 32/60 → tuned 42/60; +16.7 points [5.0, 28.3]; five false conflicts | Public synthetic pairs, now development data; not safe-default activation evidence |
| Maintenance-judge swap, one replicate/world | Tuned 72.2 vs default 68.5; v0.3 delta +3.7 points [−11.1, 18.5] | No resolved advantage or non-inferiority; the Super condition also suffered rate limits |

Sources, costs, model settings, and limitations: [evaluation report](../docs/evaluation-report.md). GateMem, MUMBench, and CoMemBench have no reported BrainBob scores. The small checker remains opt-in; the production judge remains gpt-oss-120b.

## Contribution and history

| Contribution | Evidence |
| --- | --- |
| Shared memory, maintenance, auditing, evaluation | Backend commits and per-experiment builds in the [evaluation report](../docs/evaluation-report.md#provenance) |
| Live app launch, resumable company import, desk conversations, answer instructions | `348db5b`, `e77bb9a`, `489919b`, with [recorded verification](live-workspace-20261017/README.md) |
| Visual interface, inspectors, session files, and subsequent UI work | [Commit-linked proof of work](proof-of-work/index.html); each entry identifies its execution/capture mode |
| Small checker | Public adapter `b904e6ec0baea37bf70209093b8c59332d3c450a` and saved predictions in the [model handoff](../docs/finetune-handoff.md) |
| Reused libraries, datasets, and reference material | [Runtime stack](../docs/architecture.md), per-experiment datasets in the [report](../docs/evaluation-report.md), and [character references](../docs/character-design.md) |

Original results, scorer reviews, historical designs, and earlier fixture screenshots remain evidence of their own builds. They should not be presented as a single verified final submission build. The narrated video is now committed and linked above. Record the final submitted commit, hosted demo verification, and submission receipt only when confirmed; track the remaining work in [submission status](submission-status.md).
