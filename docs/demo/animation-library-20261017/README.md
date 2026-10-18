# Memory animation library

[Watch the full reel](brainbob-memory-animations.mp4) · [Video gallery](gallery.html) · [Interactive preview](http://127.0.0.1:3000/animations)

Fifteen native recordings of the same React Three Fiber scene components used in BrainBob. These are **isolated animation previews**, not live backend operations or benchmark evidence. The gallery calls no domain API, uses no stored memories, and cannot modify the memory store. All cabinet counts are zero because no records are loaded.

## Scenes

| Scene | Trigger in the live workspace | What the animation means |
| --- | --- | --- |
| [Conversation](clips/arrive.mp4) | `episode.ingested` | A conversation sheet arrives. This is a recorded-ingestion cue; it does not run extraction itself. |
| [Create](clips/create.mp4) | `memory.added` | Bob writes and files a candidate that the backend accepted as a new memory. |
| [Retrieve](clips/retrieve.mp4) | `memory.retrieved` | A runner goes to the appropriate tier cabinet and brings back a tabbed file. |
| [Session file](clips/session.mp4) | `session context returned` | A runner delivers a file to Maya’s desk. Real session context combines relevant, accessible individual, team, and organization records. This single-file scene illustrates delivery, not three separate retrieval calls. |
| [Update](clips/update.mp4) | `memory.added with supersedes / linked correction` | Bob pulls the old record, writes at the desk, and files its replacement. The new immutable memory supersedes the old one; history remains available. |
| [Retire / delete](clips/retire.mp4) | `memory.retired` | Fire fills the office; papers arc into the shredder and emerge as strips. The effect represents retirement of the selected record. It does not delete the whole store, erase history, or establish that retirement was confirmed. |
| [Evaluator enters](clips/evaluator-enter.mp4) | `evaluation.started` | Evaluator Bob enters from the open right side. Only the evaluator moves into the room; the crew is not mobilized. |
| [Check a citation](clips/evaluator-check.mp4) | `memory.checked` | The evaluator checks a cited record. This illustrative cue uses unchanged: no with/without correctness flip. It is not an executed evaluation result. |
| [Evaluator leaves](clips/evaluator-exit.mp4) | `evaluation.finished` | Evaluator Bob leaves once the cited-memory checks finish. This does not mean every memory in the brain was audited. |
| [Promote](clips/promote.mp4) | `memory.promoted` | A golden record rises toward the trusted shelf. Status changes; claim text is not rewritten. |
| [Flag](clips/flag.mp4) | `memory.flagged` | A red flag marks an owner-review concern. The locked memory remains present. |
| [Lock](clips/lock.mp4) | `memory.locked` | A padlock identifies an owner-protected record. Harmful locked records are flagged instead of automatically retired. |
| [Owner keeps it](clips/resolve.mp4) | `memory.resolved — keep` | The recorded owner keeps a flagged memory. Correct and retire resolutions use their corresponding operations. |
| [Reject](clips/reject.mp4) | `memory.rejected` | An incoming paper bounces back. The candidate does not become a new active memory. |
| [Answer](clips/answer.mp4) | `answer.produced` | An answer packet is delivered with its source records; actual response text and citations appear in chat. |

## Capture and playback

- Capture implementation commit: `5196b05`; identical gallery code published as `cae5c11` — isolated gallery using production `BrainScene` / `EventStage` and the existing animation clock.
- Captured October 17, 2026 from the local Next.js development server. Exact timestamps are in the per-scene capture manifests; source clock times are preserved.
- Native screenshots sampled at approximately 8–10 fps, encoded as silent H.264 1600×900 at 15 fps with repeated frames. Each clip includes its full operation and a short closing hold. No fabricated UI, model outputs, or memory operations were composited into the recordings.
- Six GIF derivatives are scaled to 800px and 8 fps for the README. Original screenshots selected as posters remain unmodified. GIFs loop; the full reel plays each scene once.
- Scope choices: individual for update, session, and answer; organization for creation, ingestion, evaluator entry, and owner states; team for the remaining scenes. These are preview targets, not permission decisions.
- The current scene has one operations Bob. The evaluator simply enters and exits, without the older crowd animation.
- The live event mapper may group or queue related backend events. The gallery isolates each visual cue so it can be inspected.
- The gallery honors reduced motion and has pause, replay, cabinet selection, and a deterministic scrubber. Recordings captured normal motion.
- Validation: typecheck and nine existing scene-animation tests passed; clips were decoded and keyframes inspected. This does not validate backend evaluation correctness.

## Files

`manifest.json` lists all clips and their timestamps. `*.capture.json` contains frame metadata; original native frames remain locally under ignored `raw/`. `render.py` creates individual MP4s, six GIFs, unmodified poster frames, and the combined reel. `verification.json` records export checks.

For actual chat writes and fresh-session reuse, see the separate [V2 film](https://github.com/user-attachments/assets/e75a7bcc-b46e-4c95-9e15-6edac63a0b38). For the event projection, see [backend-state.ts](../../../apps/web/src/lib/backend-state.ts) and [event animation documentation](../../event-animations.md).
