# BrainBob V2 — app, benchmark, and fine-tuned model

**[Watch V2 — 2:50](https://github.com/user-attachments/assets/e75a7bcc-b46e-4c95-9e15-6edac63a0b38)** · [Repository MP4](output/brainbob-v2.mp4) · [Recorded narration script](SCRIPT.md) · [Three-minute presenter script](../../../judging/demo-runbook.md)

V2 presents three things we built: the BrainBob shared-memory application, our public Bob Benchmark dataset and evaluation harness, and our fine-tuned Qwen3-0.6B LoRA memory checker. ElevenLabs narration accompanies edited footage of the running local app and separately authored explanation slides.

## Chapters

| Video time | What to look for |
| --- | --- |
| 0:00–0:24 | The memory-correctness problem and BrainBob solution |
| 0:24–1:24 | **The app:** Maya's existing preference, an explicit chat update, a fresh session using the new memory, and source/history inspection |
| 1:24–1:57 | Memory operations; source correctness and task usefulness as separate evaluation signals |
| 1:57–2:17 | **Our benchmark:** organizational pilot, measured results and uncertainty |
| 2:17–2:35 | **Our fine-tuned model:** memory-relation classification, base-versus-tuned result and opt-in status |
| 2:35–2:50 | Creators and repository |

## What the recorded app actually does

Maya types `Remember: I now prefer client updates as two short paragraphs instead of three short bullets.` The explicit frontend command emits `save_memory` and sends an owner-scoped personal note through `/episodes`. The backend extracts **m75**, supersedes **m74**, and a fresh session answers with the new preference while citing **m75**. The inspector reads source/history; it does not perform this edit.

[Backend events 153–160](backend-events.json) preserve baseline task `t-5ad057be`, the correction and fresh-session task `t-d3a53678`. `Remember:` is an explicit command, not autonomous model tool selection. Backend authority, scope, date and lock rules govern maintenance. No live audit or tuned-checker inference is demonstrated in this take.

## Provenance and limits

This compact publication preserves the original MP4, transcript, backend-event excerpt and media-verification JSON byte for byte from local recording commit `f7f5ab58436842527f7dee905bedaf4a8313b8e4` (October 17, 2026, 4:52:03 PM PDT). That source commit identifies the original local package; it is not represented as a public deployment or the current main build. The original notes identify chat implementation `91c686b`; a live reenactment requires a build containing that command. This documentation change does not add app behavior.

[Original media verification](verification.json): **170.000 seconds**, H.264 1920×1080 at encoded 30 fps, AAC 48 kHz mono, 8,219,874 bytes. SHA-256: `63ba72759ff426a3408804f34c13a5569df9f4099551e343ceb9f641586c3b6c`. The local MP4 hash was rechecked when preparing these judging documents. Original verification records a successful decode; this pass did not repeat the decode or compare the uploaded attachment's bytes.

The source used timestamped native browser frames at 1600×900, repeated to encode 30 fps. Chronological live excerpts retain real-time speed, with waiting time cut. Graphics explain mechanisms and measured historical results; they are not additional executions. Narration used Roger / Eleven v4 in eleven blocks. The shared development checkout contained other work, so the recording is not a clean hosted-release verification.

The film rounds the benchmark headline to 72%; the exact corrected v0.3 result is **71.9%**, versus 25.0% without memory, 67.9% append-only and 92.0% full authorized history. The append-only difference remains inconclusive. The fine-tuned checker improved **32/60 → 42/60** on the original public synthetic diagnostic, with five false conflicts; gpt-oss-120b remains the default. See the [evaluation report](../../evaluation-report.md).

V2 is the featured extended demo. The [historical V1 recording](../live-one-minute-20261017/README.md) remains the 60-second option; V2 does not satisfy a one-minute duration limit. The [presenter script](../../../judging/demo-runbook.md) is separate from the preserved narration transcript; no video or narration was regenerated for this update.
