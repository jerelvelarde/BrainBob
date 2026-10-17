# BrainBob — one-minute live demo

**Length:** exactly 60 seconds. **Voice:** warm, clear, conversational; approximately 130 words per minute. Give the final line a short pause before “BrainBob.”

The clean video is [output/brainbob-live-60s.mp4](output/brainbob-live-60s.mp4). Paste [voiceover.txt](voiceover.txt) into ElevenLabs. [voiceover.srt](voiceover.srt) and [voiceover-timing.json](voiceover-timing.json) provide the target timing; they are editorial guides, not forced alignment to generated audio.

| Time | Voiceover | Live picture |
| --- | --- | --- |
| 00–04s | One stale memory can put a whole team out of sync. | Live isometric office. |
| 04–15s | BrainBob gives each agent the context it can access: individual notes, team knowledge, and company decisions. Here’s Maya starting a fresh session. | New session; Bob collects Maya’s authorized context. |
| 15–27s | She asks for the approved Atlas deadline. NVIDIA models on Crusoe answer from saved context, while Bob retrieves the files beside the conversation. | Actual question and answer: November 13, approved by Mara Ellis. |
| 27–36s | Open the citation. There’s the original approval, its author, and its source. You can inspect the evidence behind the answer. | Click the answer’s citation and inspect the original approval note. |
| 36–48s | Now Maya changes a preference: three short bullets instead of three sentences. Save the correction, and Bob files the new version. | Open Individual; change Maya’s preference and save a real correction. |
| 48–52s | The previous memory stays in history. | Expand the correction chain; the prior record is retired. |
| 52–60s | A fresh session uses the correction immediately. BrainBob: shared memory you can see, inspect, and improve. | A separate fresh chat answers from the new record; return to the office. |

## ElevenLabs handoff

Generate a warm, natural narration that fits within 60 seconds. Prefer recording the seven timed blocks separately if exact picture synchronization matters. Pronounce BrainBob as “brain bob,” Crusoe as “KROO-soh,” and Atlas as “AT-lus.” The script has 119 words. No voice has been generated or account credits used for this deliverable.

Place the finished voiceover at `output/voiceover.wav`, then run:

```sh
python3 mux_voiceover.py output/voiceover.wav
```

This produces `output/brainbob-live-60s-vo.mp4`, pads short narration with silence, and refuses audio longer than 60 seconds so speech is never silently cut. Align/regenerate an overlong voice track before retrying.

## What the recording establishes

This is an edited recording of the running app and actual local backend operations, using fictional Rusty Rod records. All selected excerpts play at real-time speed. The final take’s inference wait is retained. It is not a continuous single take: idle time, setup, and an earlier drafting take are omitted. No UI, answer, event, or source was composited or fabricated.

The correction is a user-initiated change to a synthetic personal preference, not an automatic audit verdict. It creates m74, retires m30 as superseded, and a fresh task cites m74. The Atlas deadline was already corrected in the fixture before this recording; this clip inspects that approval rather than claiming to make it. No benchmark improvement, live evaluator run, or authentication implementation is demonstrated.
