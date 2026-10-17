# BrainBob — Judging Guide

**Track: Shared Brain. Core problem: memory correctness.** BrainBob aims to ensure that shared memories are supported by evidence, reflect the latest valid information, and remain reliable when reused by other agents.

One wrong or stale memory can spread the same mistake across an agent team. Every agent should read the team's living project memory before working and update it afterward, with evaluation checking corrections, preserving valid knowledge, and surfacing unresolved conflicts. The 3D brain office makes this process inspectable; measurable gains in output quality are the intended proof that more correct memory helps.

**Repository:** [jerelvelarde/BrainBob](https://github.com/jerelvelarde/BrainBob)

## Start Here

- [Three-minute demo runbook](demo-runbook.md)
- [Evidence, results, and original contributions](evidence.md)
- [Project overview and current implementation status](../README.md)
- [Architecture and stack](../docs/architecture.md)
- [Benchmark and evaluation plan](../docs/benchmarks.md)
- [Competition requirements](../docs/competition-details.md)

This folder is a judging aid, not evidence that a feature has been implemented. Record actual results and links in the evidence sheet before presenting claims.

## What to Look For

| Shared Brain requirement | Demonstration or evidence |
| --- | --- |
| Memory correctness — central claim | Evidence-backed facts, correct updates, fewer stale or unsupported facts, and no unjustified removal of valid memories; report evidence coverage and uncertainty. |
| Read before work | A fresh agent receives the correct scoped memory revisions. |
| Update after work | A useful fact or explicit correction creates an evidence-linked revision. |
| Keep knowledge current | A later answer uses the corrected fact rather than the superseded value. |
| Keep knowledge lean | Less repeated context, with task quality preserved and total maintenance cost reported. |
| Keep knowledge conflict-free | Stale writes cannot overwrite a newer revision; unresolved conflicts remain visible. |
| Show measurable quality gains | Paired held-out results against append-only memory and full-history baselines. |
| Make behavior inspectable | Retrace source conversation → evaluation → revision → retrieval → answer. |

## Judging Criteria

Weights below come from the supplied participant guide; see the [competition details](../docs/competition-details.md) for the full rules.

| Criterion | Round one | Round two | Relevant BrainBob evidence |
| --- | --- | --- | --- |
| Technicality | 40% | 25% | Shared memory lifecycle, scope enforcement, revision conflicts, independent evaluation, and harness/routing/inference integration. |
| Live demo | 20% | 25% | A working handoff, correction, subsequent answer, and persistent retrace. |
| Creativity and originality | 25% | 25% | A playful brain office that visualizes actual memory operations and their evidence. |
| Future potential and AI impact | 15% | 25% | Better cross-agent continuity and quality with less repeated context, supported by measured results. |

The intended system uses NemoClaw-managed agents, NVIDIA Switchyard routing, Crusoe inference, and SQL-backed Markdown memory. The frontend visualizes memory operations and their evidence. Distinguish working integrations, planned integrations, scripted preview events, and recorded replay throughout the presentation.
