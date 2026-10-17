# BrainBob — Judging Guide

**Track: Shared Brain.** BrainBob is a shared memory layer for an agent team, visualized as a 3D isometric brain office with BrainBob workers.

Every agent should read the team's living project memory before working and update it afterward. The goal is current, lean, conflict-free knowledge with measurable gains in output quality. Self-improvement through better memory is the supporting outcome.

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

The intended stack is CopilotKit/AG-UI → BrainBob bridge → NemoClaw-managed agents → NVIDIA Switchyard → Crusoe inference, with SQL-backed Markdown memory. Distinguish working integrations, planned integrations, scripted preview events, and recorded replay throughout the presentation.
