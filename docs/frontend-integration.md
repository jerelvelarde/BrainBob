# Frontend connection to the shared brain

Implemented October 17, 2026 against Bonan's [frontend contract](../backend/FRONTEND.md) and [seven decisions](../backend/FRONTEND-QA.md). The main route uses backend HTTP responses and SSE events. `/rehearsal` preserves the standalone animation playground. The [Rusty Rod correctness walkthrough](rusty-rod-demo.md) is at `/demo`; it is explicitly scripted.

## Run with Bonan's backend

1. Start the Python backend using its documented setup, on `http://127.0.0.1:3001`.
2. Run `pnpm dev` from the repository root and open `http://127.0.0.1:3000/`.
3. The header becomes **Connected** after `replay.done`. Without a server it shows **Backend offline** and retries the event connection every three seconds.

For a different server, set `NEXT_PUBLIC_BRAINBOB_API_URL` in `apps/web/.env.local` and restart Next. The backend must allow the frontend origin through CORS. This is a public URL setting; keep Crusoe credentials exclusively on the backend. Reload the page when switching servers or resetting the backend event log.

## Chat and inspection

CopilotKit v2 renders chat through a self-managed AG-UI agent. The adapter emits run/message lifecycle events around the backend's HTTP responses; it does not pretend those responses are token streams or use the old scripted command parser.

| Control | Request | Result shown |
| --- | --- | --- |
| Ask | `POST /ask {question, reader}` | Actual answer and clickable cited memories |
| Remember | `POST /episodes {text, scope, author, source}` | Actual stored memories, or a no-new-memories receipt |
| Usefulness | `POST /feedback {task_id, correct_answer}` | Evidence for correctness flips on the last answer's cited memories |
| Review | `POST /review {}` | Actual promotion, retirement, or flag decisions and reasons |
| Original conversation | `GET /episodes/{id}` | Source text, date, and source label |
| Correction/status history | `GET /memories/{id}/history` | Full correction chain and events that can be retraced |
| Save correction | `POST /memories/{id}/correct` | New immutable record; predecessor stays retired in history |
| Retire / lock | `POST /memories/{id}/retire` or `/lock` | Backend status change |
| Owner resolution | `POST /memories/{id}/resolve` | Keep and clear flag, retire, or correct |

The member selector has 18 Rusty Rod members across Executive, Sales, and Engineering. For example, `sales-01` reads `rusty-rod/sales/sales-01`, `rusty-rod/sales`, and `rusty-rod`. Executive membership adds no descendant access. Remember writes into the selected member’s individual scope. Changing readers starts a fresh chat context. The 22 scope paths are mapped to the three cabinet levels; labels follow the current member.

**Acting as (demo)** supplies an owner string, not an authenticated identity. The UI disables another owner's resolution controls, and backend 403s remain visible. The current global memory/event endpoints and client filtering are demonstration behavior, not an authorization boundary.

## Events, animation, and retrace

`GET /events?after=<seq>` resumes the in-memory cursor. The reducer validates events, ignores duplicate sequence numbers, and applies replay events without animation until `replay.done`. Reloading requests the complete event history. `/memories` backfills records absent from that history without overwriting newer event projections.

| Event | Scene behavior |
| --- | --- |
| `memory.added` | File a new paper; `supersedes` selects the correction/writing scene |
| `memory.retrieved` | One cabinet visit per visible scope, retaining the real memory IDs |
| `answer.produced` | Deliver an answer with citations |
| `evaluation.started` | Evaluator enters; caption explicitly says **checks the cited memories** |
| `memory.checked` | Visit that record's cabinet; helpful, harmful, no-flip, or failed-confirmation pose |
| `evaluation.finished` | Evaluator leaves; display actual checked/flip counts |
| `memory.promoted` | Raise a record to the trusted shelf |
| `memory.retired` | Office fire, flying papers, and shredder; retain the record as a tombstone |
| `memory.flagged` | Red flag on the cabinet; locked record stays available |
| `memory.locked` / owner keeps | Padlock / owner resolution scene |

Supersession retirement does not trigger the fire scene. `memory.corrected`, `evidence.recorded`, and retire/correct resolution bookkeeping do not duplicate scenes already driven by other events. Unscoped `episode.ingested` and `memory.rejected` events update the log but cannot safely be attributed to a cabinet; their request receipts stay in chat. The 22 registered Rusty Rod paths map to individual, team, or organization cabinet positions; unregistered paths are not silently assigned to them.

Retrace projects the event log at a selected sequence and poses the corresponding scene. It never resends requests. Mutations and chat input are disabled while retracing; the full correction chain remains available as historical context. Return to live restores current state without bursting through missed animations. Reduced motion uses static poses and manual event selection.

**Fresh retirement confirmation passed** appears only for a `memory.retired` event carrying `confirmed: true`. A manual retirement or correction has no such claim. A failed fresh check displays that the memory was kept.

## Verification without inference

The real backend was unavailable on this machine during integration. No live Crusoe inference or evaluation quality result is claimed.

For repeatable frontend QA only, run `node apps/web/scripts/contract-fixture.mjs` while port 3001 is free, then reload the frontend. This loopback-only, in-memory fixture implements representative HTTP/SSE flows, labels its records and answers **Contract fixture**, and makes no model calls. Its review deterministically flags the locked house rule; its feedback verdicts are scripted. Stop it before starting the real backend, and reload to clear the fixture projection.

Automated tests cover event replay/deduplication, scope ancestry, correction history, locked flags, confirmation truthfulness, cited-memory verdicts, request payloads, AG-UI lifecycle, and error handling. Browser checks exercised scoped reads, chat requests, original sources, immutable corrections, retracing, locks/flags, and manual retirement against that fixture. Production build and TypeScript checks also pass.

Remaining live validation: run the same flow against Bonan's server and Crusoe, including a real fresh retirement check. Backend task/evaluation state currently lives in process memory; after a backend restart an old feedback task may return 404. The UI surfaces that response and requires a new Ask. Records without a corresponding creation event can be shown from the memory snapshot but cannot be reconstructed at earlier timeline positions.

The README, architecture plan, and judging runbook retain their earlier wording pending Jerel's authorization to update those files.
