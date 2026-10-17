# NemoClaw integration alignment with PR #12

Verification performed on October 17, 2026 (America/Los_Angeles).

- Integration commit: [651d72464c440c63dcec8eddab21ba7fe9b86732](https://github.com/jerelvelarde/BrainBob/commit/651d72464c440c63dcec8eddab21ba7fe9b86732), committed 2026-10-17T16:11:24-07:00.
- Base: `fa0fe6beb9bd998d3877ef10db4be04970bcee38`, PR #12 merged into main.
- Original adapter implementation: `5e924395c4122438ce13ad7b540aa09b5f521ff8`.
- Merge completed without conflicts, preserving published history.
- `git diff origin/main -- apps/web backend` was empty at the tested integration commit.

## Checks at the integration commit

| Command | Observed result |
| --- | --- |
| `python3 -B -m unittest discover -s integrations/nemoclaw/tests -v` | 10 passed; fake HTTP transport |
| `python -B -m pytest backend/tests -q -p no:cacheprovider` | 287 passed in 8.89 seconds |
| `pnpm test` | 8 files, 40 tests passed |
| `pnpm typecheck` | Passed, exit 0 |

Backend tests used the existing checkout's Python virtual environment. Frontend
checks reused its installed dependencies via symlinks; no fresh dependency install
was performed. The first backend collection attempt was denied permission to create
the worktree cache directory; the permitted rerun passed. The test run did not
change tracked source files. Subsequent changes are documentation only.

## Compatibility and limits

The adapter uses the same member-scoped `/memories`, `/episodes`, and source routes
consumed by the live workspace. Its discussion proposals preserve backend ownership
of scope and authority. The workspace can inspect committed records and backend
events when connected to the same backend and member. Adapter reads do not emit
retrieval/answer events, and external conversations do not appear as desk chat.

NemoClaw/OpenShell installation, MCP stdio execution, effective egress policy,
managed inference, and the eight-step live sandbox story remain unverified.
No new UI screenshot, production build, deployment, model call, or benchmark gain
is claimed. PR #12's existing visual evidence remains unchanged.
