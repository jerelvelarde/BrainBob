# BrainBob event animations

Implemented October 17, 2026 for Jerel's visualization request, against Bonan's [frontend event contract](../backend/FRONTEND.md). This is the **animation rehearsal layer**. It does not call the backend, write memories, enforce scopes, or claim evaluation results.

Open **Events** in the local frontend. Choose **Krusty Krab (organization)**, **Sales Team (team)**, or **John (individual)**, then choose a scene. These names are fixture labels pending backend ownership fields. Replay restarts the clip; the slider seeks to a deterministic moment. The existing pause and speed controls apply. Closing the panel leaves the office visible.

## Scenes

| Wire event | Visual cue | Choreography |
| --- | --- | --- |
| `episode.ingested` | `arrived` | A conversation sheet flies into the office. |
| `memory.added` | `created` | Curator writes, carries a record toward the selected cabinet, and files its paper representation. |
| `memory.rejected` | `rejected` | The incoming paper bounces away from the cabinet and returns to sender. |
| `memory.retrieved` | `retrieved` | Runner visits the selected cabinet and delivers paper to the task desk. A live adapter must expand `memory_ids` into cues. |
| `answer.produced` | `answered` | An answer packet with sources moves to the front of the office. Actual answer text/citations await the live adapter. |
| `evidence.recorded` | `evaluated` | A calm evaluator Bob arrives wearing a beret and graphic glasses. Worried workers rush to the three cabinets, carry papers, then gather at his desk. A magnifying glass scans the records beside a “with memory / without” label. |
| `memory.promoted` | `promoted` | A golden record rises to the trusted shelf. It does not rewrite the claim. |
| `memory.retired` | `forgotten` | Cartoon fire spreads across the office, workers panic, papers fly from cabinets into the shredder, and strips tumble out. Fire fades at the end. The theatrical room-wide chaos represents retirement of the selected record, not deletion of the whole store. |
| `memory.flagged` | `flagged` | A red paper and flag mark the selected cabinet for owner review. The locked record remains present. |
| No backend content-update event yet | `updated` | A separate rewrite rehearsal takes the old paper to a desk, writes with a pen, then refiles it. Do not map promotion to this content-rewrite clip. |

The evaluator scene is deliberately a rehearsal of the requested inspection visit. The current backend only emits evidence on correctness flips; it cannot yet establish that all records were checked or provide evaluation start/end boundaries. A future adapter should use real checked IDs and lifecycle events, or explicitly label the animation as a visualization of the available evidence.

## Playback and state

- `scene-animation.ts` defines wire-event names, scope destinations, clip durations, and pure worker paths.
- `event-stage.tsx` owns a single frame-loop clock. Workers, expressions, paper, lens, fire, and shredder effects all sample it. A new cue ID replaces the previous choreography; no stale completion callback can modify memory.
- `brain-bob.tsx` separates locomotion, arm pose, expression, and props. Added happy, worried, and focused faces; carrying, writing, panic, inspection, and presentation poses. The accepted yellow rounded rectangle and violet pants remain unchanged.
- Existing recorded frontend memory actions also drive clips. Retrace seeks to an illustrative pose and can play forward without issuing domain operations. This is still browser-local scripted history.
- Rehearsal clicks do not call `makeEvent`, append to memory history, or send network requests. Fire is a visual effect only.
- Reduced motion shows a still tableau with the same text and manual seeking; it suppresses travel, blinking, gestures, flames moving, and flying/shredded-paper motion. It is not proof that an operation completed.

Teaching/learning interactions, skeletal animation, wrist/elbow reach, backend SSE wiring, real status projection, authorization, and reliable reconnect/replay remain separate work.

## Dramatic direction

Deletion now dims the room into a warm night scene, with a short camera punch on ignition. Fourteen layered flames grow across the office, with taller flames behind the cabinets and shorter flames in front to keep the workers visible. Thirty papers arc into the shredder; 48 strips fall out. Smoke rises at the rear and embers drift above the fire. Workers hop, raise their hands, and sweat beneath the “EVERYBOB PANIC!” caption. The lights and camera return to normal as the scene ends.

Evaluation dims the surroundings to violet. A spotlight and translucent cone follow the calm evaluator as he enters, while the crew scrambles to collect records. Extra front lighting preserves the characters’ bright yellow color and readable faces. Captions describe the performance, not a verdict from the backend.

Lighting, camera zoom, smoke, embers, sweat, and all other effects share the clip clock. Pause freezes them; seeking and replay reproduce the same moment. Camera motion is limited to a brief zoom of less than 10%, preserves user orbit/zoom, and is disabled for reduced motion. There is no camera shake, flashing alarm, or audio. Interrupting either scene with a different event restores its lighting and camera contribution.

## Verification

Automated checks cover deterministic seeking, no memory mutation during replay, distinct retrieval destinations, inspector-versus-runner roles, separated panic positions, finite in-room coordinates, distinct promotion/flag/retirement cues, bounded cinematic zoom, neutral lighting/camera at clip boundaries, and reduced-motion camera suppression. Browser checks cover the visible scenes, scope selection, pause/scrub/replay, and rapid replacement. No device performance benchmark or live backend evaluation is claimed.

The existing README, architecture plan, and demo runbook were intentionally left untouched pending Jerel's approval of their backend revisions.
