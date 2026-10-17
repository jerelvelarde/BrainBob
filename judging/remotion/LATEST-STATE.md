# Latest project state used for this presentation

Evidence review: October 17, 2026 (America/Los_Angeles). Initial capture baseline: `10e098708dfbca606c427db6931e585aa82d52a0`. Additional commits inspected through `51058a1` while the shared repository continued changing. This is a bounded presentation snapshot, not a claim that all later teammate work has been reviewed.

## What is implemented

- **Product:** the 3D office, three memory tiers, 18-member selector, a seated session Bob, personalized CopilotKit chat, memory-grounded starter prompts, downloadable session files, evidence inspection, and event retrace. The account switcher/fresh-session work was present as local edits during captures and later committed as `2c7770d`.
- **Backend:** FastAPI HTTP/SSE, JSONL memory/episode/event persistence, BM25 retrieval, scope filtering, immutable correction records, locks/flags, write-time maintenance, leave-one-out usefulness checks, and recent-conversation audits. The actual store is JSONL, not the SQLite design described in older planning documents.
- **Connection:** the main frontend sends real HTTP requests and consumes SSE. Prior browser verification used a labeled contract fixture. The recent `46114e4` commit adds the same-origin Next proxy and unbuffered event streaming. This presentation did not run a new live frontend-to-Crusoe test.
- **Inference:** historical experiments called Crusoe directly. `0f92517` adds configurable model endpoints by role and cache namespaces for checkpoint isolation. Configuration support does not establish that a fine-tuned endpoint is available or better.
- **New evaluation plumbing:** `51058a1` adds GateMem prediction export and data preflight. It establishes no GateMem score. MUMBench and CoMemBench also have no measured BrainBob results in the inspected readiness report. Bob Benchmark is a separate internal effort; the Rusty Rod results are not renamed as Bob Benchmark scores.

## The demonstration has three distinct evidence types

| Segment | Evidence | What it establishes |
| --- | --- | --- |
| Rusty Rod UI | Fresh native browser captures of `/demo` | Actual interface and authored policy walkthrough, no inference |
| Backend loop | Archived October 17, 13:16 PDT run, metadata and exact responses | Real model calls at the time of the recorded run, using synthetic data and legacy mode |
| Result slides | Stored held-out experiment artifacts | Measured results under those specific protocols, not newly rerun experiments |

The backend trace uses Krusty Krab identities in legacy mode. The current UI uses Rusty Rod identities. They must not be presented as one already-verified live trajectory. The recorded run's metadata reports 17 dirty files at its capture, so its Git SHA is a baseline, not an exact clean build assertion. Two harmful-task checks were seeded with real calls before the third shown check. Review required three signals plus a fresh uncached confirmation.

## Results worth showing

- **Rusty Rod synthetic held-out suite:** 30 scenarios / 76 questions per condition. Correct memory updates 12/13 with maintenance vs 0/13 append-only. Valid memories wrongly retired 0/32. Answer accuracy 68/76 vs 67/76, paired difference +1.3 points, 95% interval [−5.3, +7.9]. No significant answer gain. Recent audit added zero net gain. Unresolved-conflict answers were a weakness: 0/3.
- **LongMemEval modified 50-question subset:** average answering context 2,681 vs 108,946 tokens (40.6× smaller). Answers 35/50 vs 39/50 for full history. This tests extraction/retrieval, not the audit. Judge differs from the official protocol. Seventy-six extraction episodes failed parsing or returned empty; no claim of accuracy equivalence.
- **Recorded selected backend example:** 15/15 recorded checks, bad m2 retired with confirmation, useful m3 promoted, new agent answered 10 PM citing m1. This illustrates the mechanism; it is not a population accuracy estimate.

## Current boundaries

Authentication is absent: the member marker is client supplied. Durable server sessions and full model-input tracing remain pending. NemoClaw and Switchyard are not integrated. The UI audit sample is authored, not an inference result. Usefulness is not truth. Historical benchmarks and a configured endpoint do not prove fine-tuned model readiness.

## Sources inspected

- [Frontend integration](../../docs/frontend-integration.md), [session files](../../docs/session-files.md), [Rusty Rod walkthrough](../../docs/rusty-rod-demo.md)
- [Memory store](../../backend/brainbob/memory.py), [server](../../backend/server.py), [inference client](../../backend/brainbob/llm.py)
- [Evaluation report](../../docs/evaluation-report.md), [LongMemEval original results](../../bench/results/20261017-110432/results.md)
- [Archived Rusty Rod result copied for portability](evidence/rusty-rod-results.md)
- [Recorded backend metadata](evidence/backend-run-meta.json), [selected responses](evidence/backend-selected-responses.json), [original runbook](../../backend/demo/DEMO.md)
- [Fine-tune handoff](../../docs/finetune-handoff.md), [external benchmark readiness](../../docs/external-benchmark-readiness.md)
- [Screen capture provenance](evidence/captures.json)

Some older README/evidence-sheet sections lag implementation. The presentation uses implementation files and actual result artifacts where they disagree. It does not rewrite those teammates' documents.
