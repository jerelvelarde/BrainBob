# BrainBob — Judging Evidence Sheet

Fill this sheet with verified links and outcomes before submission. **Blank fields and “not recorded” entries are not passing results.** Internal goals in the [benchmark plan](../docs/benchmarks.md) are not achieved scores.

## Submission

| Item | Value |
| --- | --- |
| Public repository | [jerelvelarde/BrainBob](https://github.com/jerelvelarde/BrainBob) |
| Submitted commit | Not yet (HEAD when the report was written: `21260c4`; Rusty Rod and benchmark files were still uncommitted) |
| Live demo URL | Not yet |
| One-minute video URL | Not yet |
| Team members | Not yet |
| Evaluation date and build | 2026-10-17, build `21260c4`; per-experiment code commits in the [evaluation report](../docs/evaluation-report.md#provenance) |

## Working Features and Integration Evidence

| Capability | Evidence to attach | Verified result |
| --- | --- | --- |
| Fresh-agent shared-memory handoff | Agent A write, Agent B retrieval manifest, and task outcome. | Not recorded |
| Create/update/forget | Source evidence, committed revisions, and active retrieval behavior. | Not recorded |
| Memory evaluation | Audit mode, eligible/sample IDs, verdicts, and independently expected outcomes. | Change-and-observe evaluator run on LoCoMo and BANKING77: no accuracy gain (BANKING77 frozen rule +0.0 pts, CI [-1.3, +1.3]; LoCoMo identical at 404/760). Seeded recent-conversation audit implemented in `b82fde7`; no scored result yet. See [report](../docs/evaluation-report.md). |
| Scope isolation | Authorized and unauthorized retrieval checks. | Not yet (permissions implemented in `467c9b3`; correctness suite pending, no results) |
| Conflict handling | Stale expected-revision rejection and duplicate-operation checks. | Not yet (`5b2d2ea` adds locks and corrections; no recorded check results) |
| Persistent retrace | Reloaded history and source → revision → answer links. | Not recorded |
| 3D visualization | Recording of event-driven actions; label any ambient walking or scripted preview. | Screenshots in [proof-of-work](proof-of-work/index.html), recorded against a labeled local fixture; no live-backend recording yet |
| NemoClaw harness | Runtime/version and an observed agent execution. | Not yet (not integrated) |
| NVIDIA Switchyard routing | Route configuration/version and actual selected-target evidence. | Not yet (not integrated) |
| Crusoe inference and NVIDIA models | Successful call records with provider, actual model IDs, and outcomes. | Crusoe called directly; model ids per role listed in the [report](../docs/evaluation-report.md#integration-status) (Nemotron-3.5-Lightning-30B-A3B, Nemotron-3-Super-120B-A12B, Nemotron-3-Nano-30B-A3B; also Qwen3.8-27B and gpt-oss-120b, which are not NVIDIA). Outcomes in the result folders below. |
| Optional You.com research | Saved search results and plan citations, if included. | Not recorded |

## Paired Evaluation Results

Record actual numerators and denominators, not percentages alone. Use identical held-out tasks and answering-model settings across conditions. See the [benchmark plan](../docs/benchmarks.md) for condition definitions.

| Condition | Correct / total tasks | Fresh-agent context tokens | Total pipeline tokens | Task latency | Results artifact |
| --- | --- | --- | --- | --- | --- |
| No memory (BANKING77, n=300 held-out, seed 42) | 189/300 | 0 | Not recorded | Not recorded | [results](../backend/results/20261017-122228-stream-banking77/results.md) |
| Ordinary memory, audit disabled (same run) | 202/300 | ~547 (est.) | Not recorded; whole pipeline $0.2215 fresh, wall 479 s | Not recorded | same |
| Audited memory, frozen rule `min_changes=3` (same run) | 202/300 (paired diff vs ordinary +0.0 pts, 95% CI [-1.3, +1.3]) | ~544 (est.) | same | Not recorded | same |
| Full authorized history (LongMemEval 50-question subset, different task set) | 39/50 vs BrainBob extracted memory 35/50 | 108,946 vs 2,681 | $2.299 total for both | Not recorded | [results](../bench/results/20261017-110432/results.md) |
| Append-only vs maintenance-enabled (write-time maintenance) | Not yet | Not yet | Not yet | Not yet | Not yet |

Other held-out runs: LoCoMo 10 conversations, none 85/760, all 404/760, audited 404/760 ([results](../backend/results/20261017-112134-locomo/results.md)); LoCoMo noisy-writer stress test, n=115 ([results](../backend/results/20261017-113727-locomo/results.md)). The `backend/results/` folders are gitignored. Exploratory threshold variants (min 2, min 1, author) are labeled exploratory in the report. Full write-up: [evaluation report](../docs/evaluation-report.md).

| Maintenance measure | Observed count / denominator or result |
| --- | --- |
| Extraction precision and recall | Not yet (Rusty Rod correctness suite pending) |
| Correct updates given decisive evidence | Not yet |
| Unsupported new claims | Not yet |
| Valid memories incorrectly forgotten | Not yet |
| Random-audit evidence coverage | Not yet |
| Audit decision quality given evidence | Not yet |
| End-to-end freshness, including audit misses | Not yet |
| Unauthorized retrievals | Not yet |
| Changes with complete retrace evidence | Not yet |

Attach dataset/scenario IDs, revision, seeds, actual model and policy versions, scoring rubric, and raw outcomes. Count ingestion, audits, routing judgments, retries, and answering in total pipeline usage. Label public benchmark subsets and modified protocols explicitly.

## Original Hackathon Contributions

The participant guide requires clearly identifying what was built during the event. Complete this table from actual commits and work records; do not assume every repository file is an original contribution.

| Feature or asset | Built during event / reused | Team contribution | Commit, source, or license reference |
| --- | --- | --- | --- |
| Shared memory service | Built during event | Not yet | Backend commits `d45d1fe`..`21260c4` (`git log -- backend`) |
| Memory evaluation | Built during event | Not yet | `7b40bfd`, `e2b4cf5`, `f308bab`, `5e2b4bb`, `833911b`, `b82fde7`; benchmark datasets (LongMemEval, LoCoMo, BANKING77) are third-party |
| Agent harness and routing integration | Not recorded | Not recorded | Not recorded |
| 3D scene and character implementation | Not recorded | Not recorded | Not recorded |
| Memory inspector and retracing | Not recorded | Not recorded | Not recorded |
| Third-party libraries and reference imagery | Not recorded | Not recorded | Not recorded |

## Known Limits

- NemoClaw and NVIDIA Switchyard are not integrated.
- The audit/evaluator showed no measurable accuracy gain (see the report); usefulness is not truth, and factual correctness has no scored result yet (Rusty Rod correctness suite pending).
- Demo scenes are selected or fixture-driven; only held-out numbers are evaluation results.
- LongMemEval is a 50-question subset with a gpt-oss-120b judge; no run reports multi-seed variation.
- Full list: [evaluation report](../docs/evaluation-report.md).

Link to the current [implementation status](../README.md) and avoid describing planned capabilities as completed work.
