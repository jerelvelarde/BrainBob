# One Bob handles memory operations

Implementation: `997e1502ebb762e4ebd79a06f823664f9cc26952` (October 17, 2026, 5:23:13 PM PDT). Playback controls: `3204a8d`.

- Create: Memory Bob writes at home, carries the record, and files it in the selected cabinet.
- Update: the same Bob collects the old record, returns home to write, and files the replacement.
- Retire: Bob collects one record and carries it to the shredder. The paper clears the lid before entering the slot; strips follow. Room-wide fire, paper storms, and panic captions are removed.
- Paper handoffs and worker movement share one deterministic sampler. Held and transferred sheets never appear together.
- Completed gallery clips offer Replay. Reduced-motion playback controls are disabled; manual seeking remains available.

## Evidence

Screenshots captured through the local Chrome animation gallery after the implementation commit. The gallery uses production scene components with isolated preview cues, zero loaded memories, and no backend writes. Other agents' uncommitted README, demo, chat/backend, and proof-of-work edits were present in the workspace and are outside this implementation commit.

| Capture | Pacific capture time | Pose |
| --- | --- | --- |
| [Create](create.jpg) | October 17, 2026, 5:23:37 PM PDT | Team cabinet, 10%, writing |
| [Update](update.jpg) | October 17, 2026, 5:23:37 PM PDT | Team cabinet, 53%, correction |
| [Retire](retire.jpg) | October 17, 2026, 5:23:45 PM PDT | Organization cabinet, 82%, shredder handoff |

Exact capture times are in `captures.json`. These are appearance and choreography evidence, not proof of backend mutation or model quality. Earlier video/GIF recordings retain the old choreography.

## Validation

- `pnpm typecheck`: passed.
- `pnpm --filter @brainbob/web exec vitest run src/lib/scene-animation.test.ts src/lib/session-scene.test.ts`: 12 passed; output in `tests.txt`.
- Browser: create writing, update correction, retirement handoff/strips, scope change, seeking, pause, completed playback/replay, rapid scene replacement; no captured console errors.
- Full-suite run during concurrent chat work: 44 passed, 1 failed in `backend-chat-agent.test.ts` (expected trailing punctuation in a personal remember command). That failure was in independently edited files; those changes were preserved.
- No device performance measurements or browser emulation of reduced-motion preferences were performed.

Local commits only; nothing pushed by this task.
