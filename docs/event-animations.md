# BrainBob event animations

The main workspace connects the scenes to HTTP responses and SSE events; see [frontend integration](frontend-integration.md). The isolated **animation library** at `/animations` reuses the production scene components without calling the backend or changing memory. `/rehearsal`, `/demo`, and `/character-study` now redirect to the live workspace.

[Watch the recorded scene library](demo/animation-library-20261017/README.md), including update, retirement, retrieval, session-file handoff, and the evaluator lifecycle. Those recordings predate the single-Bob create/update/retirement choreography below. Clips are animation previews, not live backend operations or evaluation evidence.

Choose a scene and an Individual, Team, or Organization cabinet, then **Play from start**. Pause and the position slider inspect the same deterministic clock. Reduced-motion preferences show a still tableau with manual seeking. The selected member is Maya; cabinet counts are zero because the isolated gallery loads no stored records.

## Scenes

| Wire event | Visual cue | Choreography |
| --- | --- | --- |
| `episode.ingested` | `arrived` | A conversation sheet flies into the office. |
| `memory.added` | `created` | Memory Bob writes at his home position, carries one record to the selected cabinet, and files it. |
| `memory.rejected` | `rejected` | The incoming paper bounces away from the cabinet and returns to sender. |
| `memory.retrieved` | `retrieved` | Runner visits the record’s tier cabinet and delivers a tabbed session folder to the task desk. |
| `answer.produced` | `answered` | An answer packet with sources moves to the front of the office; chat shows the actual answer and citations. |
| `evaluation.started`, `memory.checked`, `evaluation.finished` | `evaluated` | A calm evaluator Bob enters through the open right side, checks the cited record, and leaves. The current scene uses one operator; it does not mobilize the whole crew. Checks include unchanged verdicts. |
| `memory.promoted` | `promoted` | A golden record rises to the trusted shelf. It does not rewrite the claim. |
| `memory.retired` | `forgotten` | Memory Bob collects the selected record, carries it around the desks to the shredder, and feeds it through the slot. Strips appear only after the paper enters; the room stays calm and history is preserved. |
| `memory.flagged` | `flagged` | A red paper and flag mark the selected cabinet for owner review. The locked record remains present. |
| `memory.added` with `supersedes` | `updated` | The same Memory Bob collects the old paper, returns home to write the correction, and carries the replacement back to the cabinet. Do not map promotion to this content-rewrite clip. |
| `memory.locked`, `memory.resolved` (keep) | `locked`, `resolved` | Show the owner lock or the owner's decision to keep a flagged record. |

The standalone evaluator scenes are isolated previews. The main route uses checked IDs and lifecycle events, including checks with no flip. `evidence.recorded` is retained for history but does not duplicate the check animation. Actual verdict quality still requires live backend validation.

## Playback and state

- `scene-animation.ts` defines wire-event names, logical scopes, tier-cabinet projection, clip durations, and pure worker paths.
- `event-stage.tsx` owns a single frame-loop clock. Workers, expressions, paper, lens, and shredder effects all sample it. A new cue ID replaces the previous choreography; no stale completion callback can modify memory.
- `brain-bob.tsx` separates locomotion, arm pose, expression, and props. Added happy, worried, and focused faces; carrying, writing, panic, inspection, and presentation poses. The accepted yellow rounded rectangle and violet pants remain unchanged.
- Isolated preview cues drive the animation library. Main-route Retrace instead projects the backend event log at a selected sequence; neither version issues domain operations during playback.
- Animation-library controls do not append to memory history or send domain network requests. The shredder is a visual effect only.
- Reduced motion shows a still tableau with the same text and manual seeking; it suppresses travel, blinking, gestures, paper transfers and shredded-paper motion. It is not proof that an operation completed.

Teaching/learning interactions, skeletal animation, wrist/elbow reach, and authenticated authorization remain separate work. SSE wiring, status projection, and sequence-based reconnect/replay are implemented. Separate [live-workspace evidence](../judging/live-workspace-20261017/README.md) and the [V2 chat recording](https://github.com/user-attachments/assets/e75a7bcc-b46e-4c95-9e15-6edac63a0b38) document real-provider behavior.

## Single-Bob choreography

Create, update, and retirement share `memoryOperationAt`: one operator owns the record from start to finish. Carried paper uses Bob's hand prop. A separate mesh appears only during cabinet pickup, cabinet filing, or feeding the shredder, so the carried and transferred paper never duplicate each other. Writing uses Bob's notebook and pen at his home position. Paths use the rear and side aisles to reach the cabinets and shredder.

The old room-wide fire, panic captions, paper storm, smoke, and camera punch have been removed from retirement. One retired record produces a short, local strip effect. The evaluator still enters and exits through the open side with ordinary room lighting.

All phases share the clip clock. Pause freezes the scene, seeking reproduces the same pose, and reduced motion keeps manual seeking available. The animation library stops at completion and offers Replay; its playback buttons are disabled under reduced motion.

## Verification

Automated checks cover deterministic seeking, no memory mutation during replay, distinct retrieval destinations, inspector-versus-runner roles, single-operator ownership, nonoverlapping paper handoffs, shredder arrival before strips, finite in-room coordinates, distinct promotion/flag/retirement cues, and neutral retirement lighting/camera. Browser checks cover the visible scenes, scope selection, pause/scrub/replay, and rapid replacement. No device performance benchmark or live backend evaluation is claimed.

The README now links the recorded scene library and explains the operations. Benchmark outcomes remain separate from these visual previews.
