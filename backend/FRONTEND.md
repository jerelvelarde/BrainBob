# BrainBob backend for the 3D frontend

## Run

```
cd backend
uv venv .venv   # once
uv pip install --python .venv fastapi uvicorn sse-starlette httpx pytest
.venv/Scripts/python server.py     # serves http://127.0.0.1:3001
```

CORS allows http://127.0.0.1:3000 and http://localhost:3000. All bodies are JSON.
Tests: `.venv/Scripts/python -m pytest tests -q` (fake core, no network).

## HTTP

**POST /episodes** `{"text": "Alex: let's launch Oct 24", "date": "2026-10-17", "source": "slack"}`
-> `{"episode_id": "ep-1a2b3c4d", "memories": [{"id":"m1","text":"Launch is Oct 24","author":"curator","origin":"ep-1a2b3c4d","date":"2026-10-17","status":"trial","scope":"team"}]}`

**POST /ask** `{"question": "When do we launch?", "now": "2026-10-17"}`
-> `{"task_id": "t-9f8e7d6c", "answer": "Oct 24", "cited_ids": ["m1"], "memories": [Memory]}`

**POST /feedback** `{"task_id": "t-9f8e7d6c", "correct_answer": "October 25"}`
-> `{"evidence": [{"memory_id":"m1","shown":true,"correct":false,"task_id":"t-9f8e7d6c"}]}`
(404 if task_id unknown. Server grades with the judge, then runs leave-one-out.)

**POST /review** `{}` -> `{"decisions": [{"memory_id":"m1","action":"retire","reason":"...","task_ids":["t-..."]}]}`
(action: promote / retire / flag)

**GET /memories?status=trial** -> `[Memory + evidence_count + evidence_flips]`

**GET /report** -> author ledger + retire reasons (shape set by the core evaluator).

**GET /events** -> SSE. Replays the full history first, then pushes live. Each message is `data: {json}`.

```js
const es = new EventSource("http://127.0.0.1:3001/events");
es.onmessage = (e) => handle(JSON.parse(e.data)); // {type, ts, ...}
```

## SSE events -> scene actions

Existing actions in `apps/web/src/lib/memory.ts`: created, retrieved, evaluated, updated, forgotten
(`MemoryAction`, `makeEvent`). Map backend events onto them:

| event type | data | scene action (MemoryAction) |
|---|---|---|
| episode.ingested | episode_id, source, n_memories | conversation arrives (caption only; no memory action) |
| memory.added | memory | `created` (worker files a new record) |
| memory.rejected | text, reason | bounce animation at cabinet (no memory change; closest: caption) |
| memory.retrieved | task_id, memory_ids | `retrieved` for each id (Runner Bob pulls records) |
| answer.produced | task_id, answer, cited_ids | answer delivered; show answer text, highlight cited_ids |
| evidence.recorded | memory_id, author, shown, correct, task_id | `evaluated` (Inspector Bob checks the record) |
| memory.promoted | memory_id, reason | `updated` (record moves to trusted shelf) |
| memory.retired | memory_id, reason, task_ids | `forgotten` (archive) |
| memory.flagged | memory_id, reason | mark record red (no existing action; add a flag state) |

Note: the server emits episode.ingested, memory.retrieved, answer.produced; the core emits the memory.* and evidence.* events on the same bus.
