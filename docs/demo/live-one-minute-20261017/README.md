# One-minute live recording

- [Watch the finished 60-second narrated video](output/brainbob-live-60s-vo.mp4)
- [Voiceover MP3](output/voiceover.mp3) · [Uncompressed WAV](output/voiceover.wav)
- [Original silent video](output/brainbob-live-60s.mp4)
- [Timed demo script](SCRIPT.md)
- [ElevenLabs narration text](voiceover.txt)
- [Subtitle timing](voiceover.srt)
- [Actual backend event excerpt](backend-events.json)
- [Media verification and limitations](verification.json)

The finished video is 1920×1080 H.264, exactly 60.000 seconds, with ElevenLabs narration. Its frame captures are from the live localhost application and real backend operations on fictional data. Selected excerpts retain real-time speed; there are editorial cuts. Native capture was approximately 8–10 frames per second, encoded at 30 fps with repeated frames. No interpolated animation, fabricated response, or staged frontend event is introduced.

`capture.json` records every source frame’s timestamp and clip. `edit.json` records the chosen source intervals. Raw captures remain locally in ignored `raw/`; `render.py` reproduces the silent video from those files. All final video bytes and metadata are retained here.

The seven narration clips were generated through the signed-in ElevenLabs Chrome UI using **Roger — Laid-Back, Casual, Resonant**, **Eleven v4**, stability 50%, similarity 75%. Generation 1 was downloaded for each block; the originals are in `elevenlabs/`. All clips keep their original pace except the closing line, accelerated by 5.84% without changing pitch to fit its eight-second scene. No speech is trimmed. The voiceover is padded to the scene boundaries and normalized with a -16 LUFS target (measured -16.82 LUFS, -1.49 dBTP). [Alignment and provenance](elevenlabs/alignment.json) and [export checks](elevenlabs/verification.json) record the details. The original video bitstream is preserved, and the final audio/video decode without errors.

To reproduce the narration edit:

```sh
python3 assemble_voiceover.py
python3 mux_voiceover.py output/voiceover.wav
ffmpeg -y -i output/voiceover.wav -c:a libmp3lame -b:a 192k output/voiceover.mp3
```

The app was running from the shared development checkout while teammates worked on summaries and recording explainers. See verification.json for that disclosure. This milestone records the product; it does not change application or backend source.
