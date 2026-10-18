# BrainBob V2 — 2:50

New ElevenLabs narration, Roger / Eleven v4. The live section shows an explicit personal-memory request through agent chat; the frontend routes `Remember:` to the backend maintenance loop. It is not an autonomous model-selected write.

## 0:00–0:10 · problem

One stale memory can put an entire agent team out of sync. The problem isn't storing more context. It's keeping shared knowledge correct.

## 0:10–0:24 · solution

BrainBob checks new information against evidence, authority, and existing memories. Agents receive permitted context, while our three-dimensional office makes memory operations visible. NVIDIA models run on Crusoe.

## 0:24–0:34 · baseline

Here's Maya's live session. Her agent retrieves a saved preference: client updates should use three short bullets. The answer cites the memory it used.

## 0:34–0:57 · update

Now Maya changes that preference through chat. She types Remember, followed by her new instruction: two short paragraphs. The backend extracts the note, checks existing knowledge, and replaces the conflicting preference. The tool receipt reports the actual update. No manual memory edit is needed.

## 0:57–1:18 · fresh

We start a fresh session. Bob collects a new file containing Maya's accessible context. Ask the same question again, and the new agent now answers: two short paragraphs. The correction survives beyond the original conversation, with a citation to the updated memory.

## 1:18–1:24 · history

The source is Maya's chat. The previous record remains in the correction history.

## 1:24–1:37 · memops

Behind the scene: create, retrieve, update, and retire. Updates supersede earlier records. Forgetting removes a memory from normal retrieval while preserving its history and evidence.

## 1:37–1:57 · evaluation

We separate two questions. Correctness asks whether source evidence still supports a fact. Usefulness removes one cited memory, re-answers, and compares the result. Helpful doesn't necessarily mean true. Recent audits sample conversations with a recorded seed, and report evidence coverage separately.

## 1:57–2:17 · benchmark

Our synthetic organizational benchmark measures whether the next agent answers correctly within its boundaries. Maintained memory scores seventy-two percent, versus twenty-five without memory. Its four-point lead over append-only is inconclusive. These are small-pilot results under a corrected scorer, not a claim of proven superiority.

## 2:17–2:35 · finetune

We also fine-tuned a small Qwen model to classify memory pairs as same, conflicting, or unrelated. It improved from thirty-two to forty-two correct on sixty diagnostic pairs. It's experimental and opt-in, with false conflicts still remaining.

## 2:35–2:50 · creators

Explore BrainBob on GitHub: the code, benchmark, model adapter, and proof of work. Built by Jerel Velarde of CopilotKit and Bonan Kuo of EarthOnline. Help us make shared agent memory worth trusting.
