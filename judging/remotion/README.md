# BrainBob Remotion presentation

**Historical presentation source.** For judging, start with the [finished narrated live recording](../../docs/demo/live-one-minute-20261017/README.md) and [current judge's guide](../README.md). This package remains available to reproduce the earlier presentation; its rendered outputs are not committed.

A three-minute narrated product showcase, a one-minute cut, and a silent presenter composition. Actual project screenshots, a recorded model-run excerpt, and measured benchmark results have distinct on-screen labels. No generated product mockups or fabricated model responses.

## Watch and present

- `out/brainbob-full.mp4`: 3:00, 1920×1080, 30 fps, synthetic guide narration and selectable English captions.
- `out/brainbob-short.mp4`: 1:00, same format.
- [Timed presenter script](SCRIPT.md): narration, exact UI actions, and fallback instructions for both cuts.
- [Latest-state briefing](LATEST-STATE.md): inspected capabilities, results, current gaps, and evidence sources.
- [Capture provenance](evidence/captures.json): actual capture times and dirty-tree disclosure.

The visual format is a motion presentation of captured application screens, not a continuous screen recording. The recorded backend portion displays exact archived response text. Narration uses the installed macOS Samantha voice as a rehearsal guide. Substitute a human voice for a final stage delivery if desired.

## Reproduce locally

This package is isolated under `judging/remotion` so it does not alter the app workspace or root lockfile. Requires Node 22+, Chrome, and FFmpeg/ffprobe. Audio generation uses macOS `say`; other platforms can prepare a silent composition.

```sh
cd judging/remotion
npm ci --ignore-scripts
npm run assets
npm run typecheck
npm run check
npm run stills
npm run render
npm run studio
```

Studio opens at port 3010. Compositions:

- `BrainBobShowcase`: full film with voice.
- `BrainBobOneMinute`: short film with voice.
- `BrainBobPresenter`: full film without voice; use the chapter timeline and `SCRIPT.md` to present at your own pace.

On another platform use `npm run assets -- --silent`, or provide WAV tracks before rendering. Set `BRAINBOB_CHROME` to a Chrome executable if auto-discovery is unsuitable. `BRAINBOB_VOICE` selects another installed macOS voice. The renderer may download a supported browser if none is supplied.

## Edit the story

`src/story.json` is the source of truth for titles, scene durations, narration, and demo actions. Full and short durations are checked at 180 and 60 seconds. `scripts/prepare.mjs` generates the audio manifest, captions, and `SCRIPT.md`. The React composition lives in `src/index.tsx`; results excerpts and raw screenshot bytes remain separately reviewable.

Replace `public/audio/<cut>-<scene>.wav` with your narration within that scene's duration and render **without rerunning assets**, which would regenerate it. Scene audio begins 0.4 seconds into each scene. Update captions when replacing narration. Captions use approximate sentence timing; they are not force-aligned.

`out/` and generated audio are local deliverables excluded from Git. Source, package lock, screenshots, compact result evidence, and presenter script are committed. Render the package to reproduce the videos. No new inference calls, deployment, upload, or push is required.

Implementation references: [Remotion rendering](https://www.remotion.dev/docs/renderer/render-media), [Remotion compositions](https://www.remotion.dev/docs/composition).
