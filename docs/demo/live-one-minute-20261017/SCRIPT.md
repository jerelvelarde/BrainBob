# BrainBob — one-minute live demo

**Length:** exactly 60 seconds. **Voice:** warm, clear, conversational; approximately 130 words per minute. Give the final line a short pause before “BrainBob.”

The finished narrated video is [output/brainbob-live-60s-vo.mp4](output/brainbob-live-60s-vo.mp4); the [clean video](output/brainbob-live-60s.mp4) is also retained. [voiceover.txt](voiceover.txt) contains the ElevenLabs script. [voiceover.srt](voiceover.srt) and [voiceover-timing.json](voiceover-timing.json) provide the scene timing; they are editorial guides, not word-level forced alignment.

| Time | Voiceover | Live picture |
| --- | --- | --- |
| 00–04s | One stale memory can put a whole team out of sync. | Live isometric office. |
| 04–15s | BrainBob gives each agent the context it can access: individual notes, team knowledge, and company decisions. Here’s Maya starting a fresh session. | New session; Bob collects Maya’s authorized context. |
| 15–27s | She asks for the approved Atlas deadline. NVIDIA models on Crusoe answer from saved context, while Bob retrieves the files beside the conversation. | Actual question and answer: November 13, approved by Mara Ellis. |
| 27–36s | Open the citation. There’s the original approval, its author, and its source. You can inspect the evidence behind the answer. | Click the answer’s citation and inspect the original approval note. |
| 36–48s | Now Maya changes a preference: three short bullets instead of three sentences. Save the correction, and Bob files the new version. | Open Individual; change Maya’s preference and save a real correction. |
| 48–52s | The previous memory stays in history. | Expand the correction chain; the prior record is retired. |
| 52–60s | A fresh session uses the correction immediately. BrainBob: shared memory you can see, inspect, and improve. | A separate fresh chat answers from the new record; return to the office. |

## ElevenLabs recording

Generated the seven blocks separately in the signed-in ElevenLabs Chrome session, using Roger — Laid-Back, Casual, Resonant and Eleven v4. The script has 119 words. Original MP3 clips, selected generation, settings, timing, and checksums are retained in [elevenlabs/](elevenlabs/). The final line uses a 1.0584× pitch-preserving tempo adjustment; the other six retain their original pace. The account displayed 10,000 credits before and 9,257 afterward.

Rebuild the aligned voiceover and narrated video:

```sh
python3 assemble_voiceover.py
python3 mux_voiceover.py output/voiceover.wav
```

This produces `output/brainbob-live-60s-vo.mp4`. The assembly pads clips to their scenes, refuses excessive speed adjustment, and does not truncate speech. The mux step refuses audio longer than 60 seconds.

## What the recording establishes

This is an edited recording of the running app and actual local backend operations, using fictional Rusty Rod records. All selected excerpts play at real-time speed. The final take’s inference wait is retained. It is not a continuous single take: idle time, setup, and an earlier drafting take are omitted. No UI, answer, event, or source was composited or fabricated.

The correction is a user-initiated change to a synthetic personal preference, not an automatic audit verdict. It creates m74, retires m30 as superseded, and a fresh task cites m74. The Atlas deadline was already corrected in the fixture before this recording; this clip inspects that approval rather than claiming to make it. No benchmark improvement, live evaluator run, or authentication implementation is demonstrated.
