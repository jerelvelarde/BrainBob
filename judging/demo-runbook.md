# BrainBob — three-deliverable demo script

**Jerel Velarde and Bonan Kou · Shared Brain · App + benchmark + fine-tuned model**

**[Watch V2 — 2:50](https://github.com/user-attachments/assets/e75a7bcc-b46e-4c95-9e15-6edac63a0b38)** · [Repository MP4](../docs/demo/v2-agent-chat-20261017/output/brainbob-v2.mp4) · [Recorded narration transcript](../docs/demo/v2-agent-chat-20261017/SCRIPT.md) · [Video provenance and chapters](../docs/demo/v2-agent-chat-20261017/README.md)

Opening line: **“We built three things: BrainBob, a shared-memory app; Bob Benchmark, a public evaluation suite; and a fine-tuned model that checks memory relations.”**

## Three-minute presentation with V2

| Stage time | Action |
| --- | --- |
| 0:00–0:10 | “We built an app, a benchmark, and a fine-tuned model. Here’s V2, with recorded live footage.” |
| 0:10–3:00 | Play V2 uninterrupted. Its 170-second runtime fills the remaining slot; the film includes the problem, all three deliverables, results, and creators. |

Do not add another live walkthrough inside this three-minute slot. Use the questions afterward to open the [scorecard](../bobbench/results/20261017-141014/scorecard.v0.3.md), [dataset](https://huggingface.co/datasets/JerelVelarde/bob-benchmark) or [adapter](https://huggingface.co/Guangze/memops-small-qwen3-0.6b-lora/tree/b904e6ec0baea37bf70209093b8c59332d3c450a).

## V2 chapter cues

| Video time | Deliverable / point | What the audience sees |
| --- | --- | --- |
| 0:00–0:24 | Problem and solution | Shared memory must stay current, authorized and traceable. |
| 0:24–1:24 | **1. The app** | Maya asks about her three-bullet preference, sends `Remember: I now prefer client updates as two short paragraphs instead of three short bullets.`, and starts a fresh session that cites the updated memory. Source/history remains inspectable. |
| 1:24–1:57 | App mechanisms | Create, retrieve, update and retire; source correctness and task usefulness are distinct. These graphics explain mechanisms, not a new live audit. |
| 1:57–2:17 | **2. Our benchmark** | Synthetic organizational benchmark and corrected results. The spoken 72% is rounded from **71.9%**, versus **25.0%** without memory; the append-only comparison is inconclusive. |
| 2:17–2:35 | **3. Our fine-tuned model** | Qwen3-0.6B LoRA classifies same/conflict/unrelated; **32/60 → 42/60**. It remains experimental and opt-in. |
| 2:35–2:50 | Creators and artifacts | Repository, benchmark, adapter and proof of work. |

## Alternative: three-minute spoken demo

Use this instead of playing the full film; it is a presenter script, not a rewrite of V2's recorded narration.

| Time | Say | Show |
| --- | --- | --- |
| 0:00–0:20 | “One stale fact can spread across an agent team. We built three things to tackle that: a shared-memory app, a benchmark to measure it, and a fine-tuned memory checker.” | [Three-deliverable guide](README.md#three-things-we-built) |
| 0:20–1:20 | “First, BrainBob. Maya changes her preference through chat. The backend checks the new fact against existing memory and supersedes the old record. A fresh session uses the correction and cites its source. The old record stays in history.” | V2 app excerpt, 0:24–1:24, with film narration muted while presenting; label it recorded footage |
| 1:20–2:05 | “Second, we created Bob Benchmark: six synthetic organizational worlds, 41 checkpoints, a runner, a scorer, and controls. Across three replicates, BrainBob scored 71.9% versus 25% without memory. Append-only scored 67.9%, so that maintenance advantage is inconclusive. Full authorized history scored 92%. We publish the traces and corrected scoring.” | [Public dataset](https://huggingface.co/datasets/JerelVelarde/bob-benchmark) and [v0.3 scorecard](../bobbench/results/20261017-141014/scorecard.v0.3.md) |
| 2:05–2:40 | “Third, we fine-tuned Qwen3-0.6B with LoRA to classify memory pairs as same, conflicting, or unrelated. We trained on 144 synthetic pairs. On the original 60-pair diagnostic, it improved from 32 to 42 correct. Five false conflicts remain, so it stays opt-in and the default judge is unchanged.” | [Published model](https://huggingface.co/Guangze/memops-small-qwen3-0.6b-lora/tree/b904e6ec0baea37bf70209093b8c59332d3c450a) and [experiment report](../docs/evaluation-report.md#experiment-7-small-memory-relation-checker-issue-7-pair-diagnostic) |
| 2:40–3:00 | “The app makes shared memory inspectable. Our benchmark makes its behavior measurable. Our fine-tuned checker explores a smaller model for one specific decision. Built by Jerel Velarde and Bonan Kou; the code, artifacts and limitations are in the repository.” | [Evidence and original contributions](evidence.md) |

## Rehearsal and live-demo notes

- Open/download V2, its transcript, the corrected scorecard, dataset and model links before presenting. Rehearse either timed route once. V2 is **2:50**; use [V1](../docs/demo/live-one-minute-20261017/README.md) when the submission field requires **60 seconds**.
- V2's write is an explicit frontend `Remember:` command routed to backend maintenance. The inspector only reads evidence. Do not describe this as autonomous tool choice, tuned-checker execution, or a live audit.
- If reenacting the app sequence, first verify a build containing the V2 chat command. Use fictional data in an isolated store and inspect the current preference before changing it. The recording's m74/m75 IDs are evidence from that run, not hard-coded live targets. This documentation update does not change the published app implementation.
- If live inference fails, say so and use the recorded excerpt. The [company-workspace evidence](live-workspace-20261017/README.md) separately covers organization approval and denied reads; the [backend audit demo](../backend/demo/DEMO.md) covers a different selected usefulness scenario.
- The [submission checklist](submission-status.md) still records hosting and receipt gates; the film does not verify a public deployment or a completed submission.

## Q&A reference

| Question | Answer boundary |
| --- | --- |
| Does maintenance beat append-only answers? | Not established: +4.0 macro CATS points, 95% interval −9.0 to 18.2. Correct state updates improved in the separate Rusty Rod suite. |
| Does the audit improve accuracy? | No measured gain in the frozen BANKING77 comparison or the cited LoCoMo comparison. Correctness and usefulness are separate checks. |
| Is the 0.6B checker the production model? | No. It is experimental and opt-in; confirmation/observe checks use saved responses and do not establish live-provider safety. |
| Is access control production authentication? | No. Current member selection is a development identity mechanism. Pilot disclosure counts cover only recorded surfaces and strings. |
| Which integrations ran? | Direct Crusoe inference and the Next/FastAPI app. NemoClaw's adapter is merged, but a sandbox run is pending. Switchyard and SQL are not integrated. |
| Is the context reduction a total cost saving? | No. The modified LongMemEval subset measured answer-context reduction with lower accuracy; total maintenance cost is a separate question. |
