# BrainBob event animations

The main workspace connects the scenes to HTTP responses and SSE events; see [frontend integration](frontend-integration.md). The isolated **animation library** at `/animations` reuses the production scene components without calling the backend or changing memory. `/rehearsal`, `/demo`, and `/character-study` now redirect to the live workspace.

[Watch the recorded scene library](demo/animation-library-20261017/README.md), including update, retirement, retrieval, session-file handoff, and the evaluator lifecycle. Clips are animation previews, not live backend operations or evaluation evidence.

Choose a scene and an Individual, Team, or Organization cabinet, then **Play from start**. Pause and the position slider inspect the same deterministic clock. Reduced-motion preferences show a still tableau with manual seeking. The selected member is Maya; cabinet counts are zero because the isolated gallery loads no stored records.

## Scenes

| Wire event | Visual cue | Choreography |
| --- | --- | --- |
| `episode.ingested` | `arrived` | A conversation sheet flies into the office. |
| `memory.added` | `created` | Curator writes, carries a record toward the selected cabinet, and files its paper representation. |
| `memory.rejected` | `rejected` | The incoming paper bounces away from the cabinet and returns to sender. |
| `memory.retrieved` | `retrieved` | Runner visits the record’s tier cabinet and delivers a tabbed session folder to the task desk. |
| `answer.produced` | `answered` | An answer packet with sources moves to the front of the office; chat shows the actual answer and citations. |
| `evaluation.started`, `memory.checked`, `evaluation.finished` | `evaluated` | A calm evaluator Bob enters through the open right side, checks the cited record, and leaves. The current scene uses one operator; it does not mobilize the whole crew. Checks include unchanged verdicts. |
| `memory.promoted` | `promoted` | A golden record rises to the trusted shelf. It does not rewrite the claim. |
| `memory.retired` | `forgotten` | Cartoon fire spreads across the office, the operations Bob panics, papers fly from cabinets into the shredder, and strips tumble out. Fire fades at the end. The theatrical room-wide chaos represents retirement of the selected record, not deletion of the whole store. |
| `memory.flagged` | `flagged` | A red paper and flag mark the selected cabinet for owner review. The locked record remains present. |
| `memory.added` with `supersedes` | `updated` | Take the old paper to a desk, write with a pen, then file the new immutable record. Do not map promotion to this content-rewrite clip. |
| `memory.locked`, `memory.resolved` (keep) | `locked`, `resolved` | Show the owner lock or the owner's decision to keep a flagged record. |

The standalone evaluator scenes are isolated previews. The main route uses checked IDs and lifecycle events, including checks with no flip. `evidence.recorded` is retained for history but does not duplicate the check animation. Actual verdict quality still requires live backend validation.

## Playback and state

- `scene-animation.ts` defines wire-event names, logical scopes, tier-cabinet projection, clip durations, and pure worker paths.
- `event-stage.tsx` owns a single frame-loop clock. Workers, expressions, paper, lens, fire, and shredder effects all sample it. A new cue ID replaces the previous choreography; no stale completion callback can modify memory.
- `brain-bob.tsx` separates locomotion, arm pose, expression, and props. Added happy, worried, and focused faces; carrying, writing, panic, inspection, and presentation poses. The accepted yellow rounded rectangle and violet pants remain unchanged.
- Isolated preview cues drive the animation library. Main-route Retrace instead projects the backend event log at a selected sequence; neither version issues domain operations during playback.
- Animation-library controls do not append to memory history or send domain network requests. Fire is a visual effect only.
- Reduced motion shows a still tableau with the same text and manual seeking; it suppresses travel, blinking, gestures, flames moving, and flying/shredded-paper motion. It is not proof that an operation completed.

Teaching/learning interactions, skeletal animation, wrist/elbow reach, and authenticated authorization remain separate work. SSE wiring, status projection, and sequence-based reconnect/replay are implemented. Separate [live-workspace evidence](../judging/live-workspace-20261017/README.md) and the [V2 chat recording](https://github.com/user-attachments/assets/e75a7bcc-b46e-4c95-9e15-6edac63a0b38) document real-provider behavior.

## Dramatic direction

Deletion now dims the room into a warm night scene, with a short camera punch on ignition. Fourteen layered flames grow across the office, with taller flames behind the cabinets and shorter flames in front to keep the workers visible. Thirty papers arc into the shredder; 48 strips fall out. Smoke rises at the rear and embers drift above the fire. The single operations Bob hops, raises his hands, and sweats beneath the “EVERYBOB PANIC!” caption. The lights and camera return to normal as the scene ends.

Evaluation now keeps ordinary room lighting. The evaluator enters from the open side, stands at the evidence desk for checks, and exits afterward. The older violet room and scrambling crew staging is no longer used. Captions describe the performance; preview verdicts are illustrative.

Lighting, camera zoom, smoke, embers, sweat, and all other effects share the clip clock. Pause freezes them; seeking and replay reproduce the same moment. Camera motion is limited to a brief zoom of less than 10%, preserves user orbit/zoom, and is disabled for reduced motion. There is no camera shake, flashing alarm, or audio. Interrupting either scene with a different event restores its lighting and camera contribution.

## Verification

Automated checks cover deterministic seeking, no memory mutation during replay, distinct retrieval destinations, inspector-versus-runner roles, separated panic positions, finite in-room coordinates, distinct promotion/flag/retirement cues, bounded cinematic zoom, neutral lighting/camera at clip boundaries, and reduced-motion camera suppression. Browser checks cover the visible scenes, scope selection, pause/scrub/replay, and rapid replacement. No device performance benchmark or live backend evaluation is claimed.

The README now links the recorded scene library and explains the operations. Benchmark outcomes remain separate from these visual previews.
