# BrainBob — judge's guide

**Shared Brain · Jerel Velarde and Bonan Kou · October 17, 2026**

BrainBob gives agent teams shared memory that checks incoming facts, applies authorized corrections, and retrieves only the context the selected member may read. The 3D office makes the sources, changes, and subsequent answers inspectable.

## Start here: three minutes

1. **Watch:** [60-second narrated live demo](../docs/demo/live-one-minute-20261017/output/brainbob-live-60s-vo.mp4). Edited footage of the running app, real Crusoe inference, and fictional company data. [Recording provenance](../docs/demo/live-one-minute-20261017/README.md).
2. **Read the result:** [corrected scorecard](../bobbench/results/20261017-141014/scorecard.v0.3.md). Maintained memory scored **71.9% macro CATS vs 25.0% with no memory** on six synthetic worlds / 41 checkpoints / three replicates. The **+4.0-point** difference against append-only memory is inconclusive (95% interval −9.0 to 18.2); full authorized history scored 92.0%.
3. **Inspect the work:** [evidence sheet](evidence.md) for claims and artifacts; [proof-of-work timeline](proof-of-work/index.html) for implementation commits and visual history. Download/open the HTML locally to view the timeline.

[Run the app locally](../README.md#run-locally) · [Architecture](../docs/architecture.md) · [Three-minute presenter runbook](demo-runbook.md) · [Submission status](submission-status.md)

## What the team built

| Contribution | Inspect it |
| --- | --- |
| Shared memory service: ingestion, scope checks, maintenance, revisions, source correctness and usefulness evaluation | [Architecture](../docs/architecture.md), [API contract](../backend/CONTRACT.md) |
| Live chat and 3D office: retrieval, citations, source/history inspection, accessible cabinets, personal sessions | [Live workspace](live-workspace-20261017/README.md), [chat and cabinet checks](chat-memory-panel-20261017/README.md) |
| Read-only Nano summaries alongside original memory files | [Summary verification](memory-summary-20261017/README.md) |
| Organizational benchmark, independent scorer review, controls, and corrected results | [Evaluation report](../docs/evaluation-report.md), [benchmark dataset](https://huggingface.co/datasets/JerelVelarde/bob-benchmark) |
| Experimental 0.6B LoRA relation checker: 32/60 → 42/60 on the original public diagnostic | [Model handoff](../docs/finetune-handoff.md), [confirmation/observe modes](../experiments/memops-small/SAFE_MODE.md) |

Jerel led the app, interaction design, visualization, and independent evaluation presentation. Bonan led the agents, memory/maintenance/evaluation backend, and small-checker experiment. Reused libraries, datasets, and references are identified in the architecture and evaluation report.

## Evidence boundaries

- **Live development evidence:** real provider calls and saved backend operations on fictional inputs. The featured video shows a manual personal-preference correction and a fresh-session answer; the Atlas approval already existed before recording.
- **Measured results:** use corrected v0.3 scores, a post-hoc rescore of saved answers. The original scores and traces remain available. These synthetic/public diagnostics are not official leaderboard scores.
- **Historical controls and previews:** deterministic reference runs, scripted presentations, and earlier UI captures are labeled in the [artifact index](artifacts.md). They are not additional live-app evaluations.
- **Still pending:** public hosted-app verification and a recorded final submission receipt. NemoClaw's adapter is merged, but a real sandbox handoff is unverified. Switchyard and SQL are not integrated. The tuned checker remains opt-in; gpt-oss-120b remains the default judge. Member selection is development identity, not production authentication.

## Judging criteria

Weights are from the [participant guide](../docs/competition-details.md).

| Criterion | Round one / two | Evidence |
| --- | --- | --- |
| Technicality | 40% / 25% | Scoped memory lifecycle, authority checks, source lineage, independent evaluation |
| Live demo | 20% / 25% | Recorded correction, fresh-session use, citations, inspectable history |
| Creativity and originality | 25% / 25% | A brain office connected to actual memory operations |
| Future potential and AI impact | 15% / 25% | Measured context benefits, explicit limits, reproducible comparisons |

For detailed provenance, use the [artifact index](artifacts.md). Existing evidence paths and historical records are preserved so published links continue to work.
