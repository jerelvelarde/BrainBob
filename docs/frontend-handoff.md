# Frontend Handoff: Connecting the 3D Brain to the Live Backend

For Jerel's agent. Read this first, then [backend/FRONTEND.md](../backend/FRONTEND.md) (endpoints and event fields) and [docs/backend-design.md](backend-design.md) (why it works this way). Written 12:30 PT, 2026-10-17. Bonan owns `backend/` and `bench/`; the frontend owns `apps/web/`.

## 1. What the backend does

BrainBob is a shared memory for an agent team. Any agent can write to it. The evaluator checks each memory by its results, then tells you which memories, and which writers, to trust.

```
write:  an episode (conversation, finished task) -> a writer agent extracts memories or a lesson
read:   a task -> retrieve memories -> agent answers and cites the memories it used
audit:  drop one cited memory, re-answer, grade both answers
        flip right->wrong: the memory helped (credit to it and its author)
        flip wrong->right: the memory harmed (blame to it and its author)
        review: promote helpful memories, retire harmful ones after a fresh confirm re-run,
                flag locked ones for their owner
```

Writers are different models: a careful one (Nemotron Lightning), a careless one (Nemotron Nano at high temperature), and Qwen. The author ledger shows, by measured results, whose memories help.

## 2. Status

| Piece | Status |
| --- | --- |
| Backend server on port 3001: write, ask, feedback, review, inspect, lock, correct, SSE events | Live. Verified end to end against Crusoe at about 12:00 PT |
| Evaluation events (`evaluation.started`, `memory.checked`, `evaluation.finished`) and confirmed retirements | Live |
| Author probation (stop using a writer's trial memories when its record is clearly bad) | In progress |
| Benchmark proof that the audit makes memory better | **In progress, not proven yet.** Use no audit numbers until section 6 says so |

## 3. Run it

```
cd backend
uv venv .venv
uv pip install --python .venv fastapi uvicorn sse-starlette httpx pytest openai rank-bm25 pyarrow huggingface_hub
.venv/Scripts/python server.py        # macOS/Linux: .venv/bin/python server.py
```

- Needs the team Crusoe key in `~/.config/crusoe/api.key` (one line). Bonan sends it privately. Never commit it.
- State lives in `backend/memory.jsonl`, `events.jsonl` and `episodes.jsonl` in the working directory. Delete them to reset.
- Tests (no network): `.venv/Scripts/python -m pytest -q tests`.

## 4. Contract essentials

Full request and response examples are in [FRONTEND.md](../backend/FRONTEND.md). The rules that matter for the UI:

- **Events:** every event has `seq`. SSE sends `id: <seq>`. Reconnect with `Last-Event-ID` (EventSource does this) or `GET /events?after=<seq>`. After replaying history the server sends `replay.done`. Animate only events after it; apply earlier ones as state.
- **What the evaluator checks:** only the memories the agent **cited** for that task, not every memory. Say "checks the cited memories" on screen.
- **Retirement:** `memory.retired` with `confirmed: true` passed a fresh re-run. Only then may the UI say "confirmed". A failed confirm emits `memory.checked` with `reason: "confirm failed"` and the memory stays in trial.
- **Locked memories** are never retired. When judged harmful they are flagged (`memory.flagged`). Only the owner resolves them (`POST /memories/{id}/resolve`).
- **Corrections** never edit a memory. They add a new one with `supersedes` and retire the old one. History: `GET /memories/{id}/history`.
- **Scope:** pass `scope` (for example `krusty-krab/sales`) on `/episodes` and `reader` (for example `krusty-krab/sales/john`) on `/ask`. A reader sees its own path and its ancestors. Memories written without a scope default to `team`.
- **Source:** `memory.origin` is the episode id. `GET /episodes/{id}` returns the original text.

## 5. Frontend tasks, in order

1. **SSE client.** Connect to `/events`, keep the last `seq`, resume on reconnect, and treat `replay.done` as the boundary between state and animation.
2. **Event to scene mapping.** Map every event in FRONTEND.md's table to an existing `MemoryAction` in `apps/web/src/lib/memory.ts`. The new evaluator events drive the Inspector: walk to the shelf on `evaluation.started`, check each record on `memory.checked`, and finish on `evaluation.finished`.
3. **New record states.** Add flagged (red), locked (badge), and retired with reason (including `author on probation`) to the cabinets and inspector.
4. **Chat panel to real calls.** Replace the scripted commands: teach (`POST /episodes`), ask (`POST /ask`, show the answer and highlight the cited memories), give the right answer (`POST /feedback`), and review (`POST /review`).
5. **Inspector.** Show the source episode (`GET /episodes/{id}`) and the revision chain (`GET /memories/{id}/history`).
6. **Author ledger.** Show `GET /report` per writer: written, helped, harmed, retired. Keep it a panel inside the room, not the main screen; the rules disqualify dashboard-first projects.
7. **Recorded benchmark replay.** Benchmark runs write `backend/results/<run>/events.jsonl` in the same event format. Let the retrace timeline load one, and label it "recorded run" everywhere it appears.
8. **README.** The "Memory Evaluation — The Critical Part" section still describes the random 10-of-50 audit. Replace it with change and observe and link [backend-design.md](backend-design.md).
9. **Proof of work.** Add each frontend milestone to `judging/proof-of-work/index.html` per its `agent.md`.

## 6. Demo use case and allowed claims

The use case is **a support team with a careless teammate**. Three writer agents route bank customer messages into 77 intents (the public BANKING77 dataset). After each ticket the agent that handled it writes a lesson. One writer is careless. Live demo, three minutes:

1. Teach: a few tickets come in; workers file lessons, each tagged with its writer.
2. Ask: a new ticket; Runner Bob pulls lessons; the answer cites two of them.
3. Feedback and audit: the Inspector drops each cited lesson and re-answers. A careless lesson flips the answer from wrong to right when removed, so it is blamed.
4. Review: the harmful lesson is confirmed and archived. The ledger shows the careless writer at the bottom.
5. Close: the benchmark result from the recorded run, only once it is measured.

Numbers you may use now:
- Memory vs no memory on LoCoMo: 11% vs 53% on 760 held-out questions.
- Memory vs full history on a 50-question LongMemEval subset: about 1/40 of the context, 8 points lower accuracy, within noise.
- First stream run on BANKING77 (60 held-out): all lessons 55% vs no lessons 65%; ledger: careless writer helped 3 times and harmed 8, careful writer helped 8 and harmed 2. Too small to claim an audit gain.

The audit-gain number (audited vs all lessons, 300 held-out, with a 95% interval) is being measured now. Bonan will add it here when it lands. Until then, say "we are measuring it", not "it improves accuracy".

## 7. Rules

- Do not edit `backend/` or `bench/`. Ask Bonan for backend changes.
- Atomic commits; stage explicit files only (AGENTS.md).
- Label scripted, recorded and live behavior honestly. Never show a number that is not in this file or in `backend/results/`.
- All user-facing text in English.
