# BrainBob — judge's guide

**Shared Brain · Jerel Velarde and Bonan Kou · October 17, 2026**

**We built an app, a benchmark, and a fine-tuned model.** BrainBob maintains shared knowledge for agent teams; Bob Benchmark measures its behavior; our Qwen3-0.6B LoRA adapter explores a smaller memory-relation checker.

## Start here

1. **Watch [V2 — 2:50](https://github.com/user-attachments/assets/e75a7bcc-b46e-4c95-9e15-6edac63a0b38):** the app's chat-driven memory update and fresh-session handoff, followed by our benchmark and fine-tuned model. [Chapters, transcript, repository MP4 and provenance](../docs/demo/v2-agent-chat-20261017/README.md).
2. **Compare the three deliverables below:** what we created, what was measured, and where the evidence lives.
3. **Inspect the work:** [evidence sheet](evidence.md), [full evaluation report](../docs/evaluation-report.md), and [commit-linked timeline](proof-of-work/index.html). Download/open the HTML locally to view the timeline.

For a strict one-minute video slot, use [V1 — 60 seconds](../docs/demo/live-one-minute-20261017/README.md). V2 is the extended judging demo.

[Run the app locally](../README.md#run-locally) · [Architecture](../docs/architecture.md) · [Three-minute presenter runbook](demo-runbook.md) · [Submission status](submission-status.md)

## Three things we built

| Deliverable | What we created | Results and evidence |
| --- | --- | --- |
| **1. BrainBob app** | Shared-memory service plus live chat and a 3D workspace: scoped retrieval, authorized maintenance, source/history inspection, and Nano summaries. | V2 records a chat preference update and a fresh session citing its replacement. Separately, Rusty Rod measured **12/13 correct updates vs 0/13 append-only**, with **0/32 valid memories wrongly retired**. [V2 evidence](../docs/demo/v2-agent-chat-20261017/README.md) · [Architecture](../docs/architecture.md) · [Evaluation report](../docs/evaluation-report.md) |
| **2. Bob Benchmark** | Our public synthetic organizational dataset, runner, deterministic scorer and controls: **six worlds / 41 checkpoints**, plus separate memory-pair and structured diagnostics. | Three-replicate pilot: **71.9% maintained vs 25.0% no memory**, corrected v0.3 macro CATS. Append-only 67.9%; full authorized history 92.0%. The maintained/append-only difference is inconclusive. [Public dataset](https://huggingface.co/datasets/JerelVelarde/bob-benchmark) · [Scorecard and traces](../bobbench/results/20261017-141014/) |
| **3. Fine-tuned memory checker** | Our published **Qwen3-0.6B LoRA adapter**, trained on 144 synthetic pairs to classify **same / conflict / unrelated**; deterministic rules still decide permitted writes. | **32/60 base → 42/60 tuned**, +16.7 points [5.0, 28.3] on the original diagnostic. Five false conflicts remain; experimental and opt-in, with gpt-oss-120b still the default. [Published adapter](https://huggingface.co/Guangze/memops-small-qwen3-0.6b-lora/tree/b904e6ec0baea37bf70209093b8c59332d3c450a) · [Model handoff](../docs/finetune-handoff.md) |

The app recording, organizational pilot and model diagnostic are separate evidence. The small-model result does not establish end-to-end improvement; the public cases are not an independently secret test set.

Jerel led the app, interaction design, visualization, and independent evaluation presentation. Bonan led the agents, memory/maintenance/evaluation backend, and small-checker experiment. Reused libraries, datasets, and references are identified in the architecture and evaluation report.

## Evidence boundaries

- **Live development evidence:** real provider calls and saved backend operations on fictional inputs. V2 shows an explicit `Remember:` chat command followed by backend maintenance and a fresh-session answer. It is not autonomous tool selection or a live audit. V1 separately shows a manual inspector correction; its Atlas approval already existed before recording.
- **Measured results:** use corrected v0.3 scores, a post-hoc rescore of saved answers. The original scores and traces remain available. These synthetic/public diagnostics are not official leaderboard scores.
- **Historical controls and previews:** deterministic reference runs, scripted presentations, and earlier UI captures are labeled in the [artifact index](artifacts.md). They are not additional live-app evaluations.
- **Still pending:** public hosted-app verification and a recorded final submission receipt. NemoClaw's adapter is merged, but a real sandbox handoff is unverified. Switchyard and SQL are not integrated. The tuned checker remains opt-in; gpt-oss-120b remains the default judge. Member selection is development identity, not production authentication.

## Judging criteria

Weights are from the [participant guide](../docs/competition-details.md).

| Criterion | Round one / two | Evidence |
| --- | --- | --- |
| Technicality | 40% / 25% | Scoped memory lifecycle, authority checks, source lineage, independent evaluation |
| Live demo | 20% / 25% | Recorded correction, fresh-session use, citations, inspectable history |
| Creativity and originality | 25% / 25% | An inspectable memory office, an original organizational benchmark, and a specialized learned checker |
| Future potential and AI impact | 15% / 25% | Measured context benefits, explicit limits, reproducible comparisons |

For detailed provenance, use the [artifact index](artifacts.md). Existing evidence paths and historical records are preserved so published links continue to work.
