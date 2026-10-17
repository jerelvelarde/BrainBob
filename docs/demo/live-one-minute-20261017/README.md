# One-minute live recording

- [Watch the 60-second silent video](output/brainbob-live-60s.mp4)
- [Timed demo script](SCRIPT.md)
- [ElevenLabs narration text](voiceover.txt)
- [Subtitle timing](voiceover.srt)
- [Actual backend event excerpt](backend-events.json)
- [Media verification and limitations](verification.json)

The video is 1920×1080 H.264, exactly 60.000 seconds, with no audio. Its frame captures are from the live localhost application and real backend operations on fictional data. Selected excerpts retain real-time speed; there are editorial cuts. Native capture was approximately 8–10 frames per second, encoded at 30 fps with repeated frames. No interpolated animation, fabricated response, or staged frontend event is introduced.

`capture.json` records every source frame’s timestamp and clip. `edit.json` records the chosen source intervals. Raw captures remain locally in ignored `raw/`; `render.py` reproduces the final video from those files. All final video bytes and metadata are retained here. No ElevenLabs audio has been generated yet.

The app was running from the shared development checkout while teammates worked on summaries and recording explainers. See verification.json for that disclosure. This milestone records the product; it does not change application or backend source.
