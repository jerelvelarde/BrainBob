# BrainBob — Memory Benchmarks and Evaluation Plan

BrainBob targets the **Shared Brain** problem statement: agents read shared knowledge before working, update it afterward, and keep it current, lean, and conflict-free while improving output quality.

This document proposes benchmarks, measurements, and internal targets. No benchmark results have been collected yet.

## Recommended Public Benchmarks

| Benchmark | What it evaluates | Priority for BrainBob |
| --- | --- | --- |
| [HaluMem](https://github.com/MemTensor/HaluMem) | Memory extraction, updating, and downstream question answering, including hallucinations and omissions at each stage. | First: closest match to the memory curator and evaluator loop. |
| [LongMemEval](https://github.com/xiaowu0162/LongMemEval) | Information extraction, multi-session reasoning, temporal reasoning, knowledge updates, and abstention when evidence is insufficient. | Second: establishes whether maintained memory helps an agent answer correctly. |
| [MemoryAgentBench](https://github.com/HUST-AI-HYZ/MemoryAgentBench) | Incremental memory processing, accurate retrieval, test-time learning, long-range understanding, and conflict resolution. | Later: useful additional conflict-resolution and incremental-ingestion coverage. |

MemoryAgentBench's conflict-resolution split has a [published critique concerning ambiguous ground truth](https://arxiv.org/abs/2610.09193). Inspect case-level evidence before interpreting its aggregate score. If cases are excluded or scoring is changed, report that as a modified diagnostic evaluation rather than an official benchmark result.

Public benchmarks complement a custom Shared Brain suite. They do not replace tests of cross-agent handoff, role-based access, concurrent updates, or trace integrity.

## Shared Brain Experiment

1. Agent A learns project facts across multiple conversations through the normal ingestion path.
2. An authorized owner corrects some facts while other facts remain valid.
3. BrainBob consolidates and evaluates the shared memory.
4. A fresh Agent B completes held-out tasks using the resulting memory.
5. Compare outcomes against append-only memory and full conversation history.

Agent B starts with a fresh conversation and no hidden carryover from Agent A. In the BrainBob condition, it receives authorized retrieved memory rather than the original history. Keep individual, team, and organization scope boundaries active throughout ingestion, evaluation, retrieval, and inspection.

### Comparison Conditions

| Condition | Behavior | Purpose |
| --- | --- | --- |
| Append-only memory | Stores extracted records without consolidation or stale-fact maintenance. | Isolates the value of memory management. |
| BrainBob with audits disabled | Uses the same memory pipeline but disables periodic evaluator maintenance. | Measures the incremental benefit of audits; document whether targeted correction checks remain enabled. |
| BrainBob with maintenance | Uses consolidation, targeted corrections, and periodic random audits. | Measures the complete proposed memory loop. |
| Full history | Supplies the authorized conversation history within the answering model's context limit. | Compares output quality and repeated-context cost. |

Use identical task questions, answering model, prompts where applicable, output budgets, and task checks across conditions. Disclose any truncation in the full-history baseline. Reset storage between independent runs.

Evaluate Switchyard routing separately against a fixed-model policy. Do not attribute gains to memory if the comparison also changes the answering model. Record the actual model selected for every call.

## Proposed Internal Targets

These are initial engineering goals for the custom suite, **not published benchmark thresholds or achieved results**.

| Measure | Definition | Initial target |
| --- | --- | --- |
| Correct-update rate | Correctly applied updates divided by update cases where decisive, authorized evidence is available. | At least 90% |
| Unsupported-write rate | Unsupported newly stored factual claims divided by all newly stored factual claims. | At most 5% |
| Erroneous-forgetting count | Valid memories incorrectly removed from active retrieval. | Zero observed |
| Held-out task accuracy gain | Accuracy with BrainBob minus accuracy with append-only memory, on paired tasks. | At least 15 percentage points |
| Fresh-agent context reduction | Reduction in input context tokens supplied to Agent B relative to full history. | At least 40%, while preserving task accuracy |
| Unauthorized retrieval count | Retrieved memories or evidence outside the principal's permitted scopes. | Zero observed |
| Trace completeness | Committed memory changes with retraceable source evidence, revision history, and operation attribution. | 100% |

Report both precision and recall for extraction so avoiding writes cannot produce a misleading success. Evaluate forgetting against explicit expected outcomes, including cases where a valid memory should be retained despite not appearing recently.

“Zero observed” applies only to the evaluated cases and is not a guarantee about all future behavior.

## Random Audit: Coverage Versus Decision Quality

The proposed evaluator samples 10 conversations without replacement from the latest 50 eligible conversations. Measure two separate properties:

- **Evidence coverage:** How often does the sample include the information needed to detect a stale or incorrect memory?
- **Decision quality conditional on evidence:** When the necessary evidence is present, does the evaluator keep, update, quarantine, or retire the memory correctly?

With one correction-bearing conversation among 50, a random sample of 10 includes that conversation only **20% of the time**. A missed correction and a wrong judgment given the correction are different failures.

Also report end-to-end freshness across all eligible stale memories, including cases the sample missed. Do not present conditional update accuracy as overall freshness.

Record the audit cutoff, eligible conversation IDs, sampled IDs, seed, checked memory revisions, evidence citations, and any budget-based omissions. A missing mention is insufficient evidence, not proof that a memory should be forgotten.

Explicit user corrections trigger a separate targeted check. Label these checks separately and do not count them toward random-audit coverage. Use fresh seeds across evaluation runs and preserve every run; a saved demonstration seed is not a substitute for sampling evaluation.

## Hackathon Evaluation Scope

### Custom BrainBob Suite

Start with 30 held-out scenarios, five in each group:

1. **Extraction:** Store supported facts and reject irrelevant or unsupported claims.
2. **Updates:** Apply an authorized correction and prevent older evidence from reverting it.
3. **Retention:** Preserve valid memories when recent samples do not mention them.
4. **Forgetting:** Retire an explicitly obsolete record while retaining its retrace history.
5. **Shared handoff:** A fresh agent uses another agent's maintained team memory correctly.
6. **Insufficient evidence:** Abstain or flag unresolved conflicts rather than inventing an answer.

Maintain separate deterministic checks for scope isolation, stale concurrent writes, duplicate operations, atomic state/event commits, and read-only replay. These are system correctness checks rather than language-model benchmark scores.

Author the expected facts and permitted outcomes before running the system. Keep development examples separate from held-out scenarios. Where inference budget permits, repeat paired runs across multiple seeds and report variation.

### Public Benchmark Slice

Add a fixed, stratified 50-question LongMemEval subset spanning its question types, with abstention examples included. Publish selected IDs, dataset revision, sampling seed, and per-category counts.

Ingest the supplied conversations through BrainBob's normal write path. Do not insert gold memories or restrict inputs to gold evidence unless explicitly reporting an oracle experiment. Preserve the benchmark's original histories and evaluation protocol where possible.

Label the result **LongMemEval subset**, not a full benchmark or leaderboard score. If histories, prompts, judges, or scoring are modified, document the changes and the resulting comparison limits.

Use HaluMem's extraction and update evaluations to diagnose maintenance failures as integration time permits. Follow its official task definitions and scoring for any result labeled HaluMem; custom inspired cases remain part of the BrainBob suite.

## Measurement and Reporting

For each condition, record:

- Correct/total task counts, accuracy, category breakdowns, and sample sizes.
- Extraction precision and recall, correct updates, unsupported writes, erroneous forgetting, and unresolved conflicts.
- Random-audit coverage, conditional decision quality, and overall freshness.
- Context tokens supplied to the fresh agent.
- Total pipeline tokens and cost when available, including ingestion, consolidation, audits, routing judgments, retries, and answering.
- Task and maintenance latency, with separate measurements for each stage.
- Actual model IDs, inference parameters, prompt/policy versions, dataset revision, seeds, and raw outcome artifacts.

Use deterministic checks for facts and application state where possible. For semantic answers, use a fixed rubric and a separate judge that cannot inspect BrainBob's own success claims; manually review a sample of judgments. The maintenance evaluator's confidence is not a benchmark accuracy score.

Report failures and missing results explicitly. Do not substitute scripted scene activity or replay for live-model evaluation evidence. A smaller answering prompt is not proof of lower total system cost.

## Demo Evidence

The intended claim is:

> A fresh agent produces better answers with less repeated context, and every memory change can be retraced.

Support it with paired measured results, an actual agent handoff, a corrected fact used in a later answer, and a retrace from source conversation through evaluation, revision, retrieval, and answer. Present this claim as achieved only when the recorded results support it.
