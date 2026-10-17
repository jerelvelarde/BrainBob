# BrainBob backend for the 3D frontend

## Run

```
cd backend
uv venv .venv   # once
uv pip install --python .venv fastapi uvicorn sse-starlette httpx pytest openai rank-bm25
.venv/Scripts/python server.py     # serves http://127.0.0.1:3001 (macOS/Linux: .venv/bin/python)
```

The real server calls Crusoe, so it needs the team's Crusoe key in `~/.config/crusoe/api.key` (one line; never commit it).
Verified at 11:40 PT: POST /episodes, POST /ask and GET /events work end to end against Crusoe.

CORS allows http://127.0.0.1:3000 and http://localhost:3000. All bodies are JSON.
Tests: `.venv/Scripts/python -m pytest tests -q` (fake core, no network).

## HTTP

**POST /episodes** `{"text": "Alex: let's launch Oct 24", "date": "2026-10-17", "source": "slack"}`
also takes `scope` (path, e.g. `"krusty-krab/sales"`) and `author`; the episode is saved to episodes.jsonl.
-> `{"episode_id": "ep-1a2b3c4d", "memories": [{"id":"m1","text":"Launch is Oct 24","author":"curator","origin":"ep-1a2b3c4d","date":"2026-10-17","status":"trial","scope":"team","reason":"","flagged":false,"supersedes":null,"owner":null}]}`
`origin` is the episode id.

**GET /episodes/{id}** -> `{id, text, date, source, scope}` (404 if unknown)

**POST /ask** `{"question": "When do we launch?", "now": "2026-10-17", "reader": "krusty-krab/sales/john"}`
(`reader` optional: only memories whose scope equals the reader path or is an ancestor of it; none means no filter)
-> `{"task_id": "t-9f8e7d6c", "answer": "Oct 24", "cited_ids": ["m1"], "memories": [Memory]}`

**POST /feedback** `{"task_id": "t-9f8e7d6c", "correct_answer": "October 25"}`
-> `{"evidence": [{"memory_id":"m1","shown":true,"correct":false,"task_id":"t-9f8e7d6c"}]}`
(404 if task_id unknown. Server grades with the judge, then runs leave-one-out.)

**POST /review** `{}` -> `{"decisions": [{"memory_id":"m1","action":"retire","reason":"...","task_ids":["t-..."]}]}`
(action: promote / retire / flag)

**POST /memories/{id}/correct** `{text, author}` -> `{memory, retired_id}` (new memory with `supersedes`; old one retired, reason `superseded by <new id>`)
**POST /memories/{id}/retire** `{reason, author}` -> `{memory}`
**POST /memories/{id}/lock** `{owner}` -> `{memory}` (status `locked`, `owner` set)
**POST /memories/{id}/resolve** `{owner, action: "keep"|"retire"|"correct", text?}` -> `{memory}` (the new memory for `correct`); 403 if not the recorded owner. Retire/correct on a locked memory by anyone else is also 403.
**GET /memories/{id}/history** -> `{chain: [Memory], events: [event]}` (supersedes chain oldest first, plus all events touching those ids)

**GET /memories?status=trial** -> `[Memory + evidence_count + evidence_flips]`

**GET /report** -> author ledger + retire reasons (shape set by the core evaluator).

**GET /events** -> SSE. Every message has `id: <seq>` and `data: {json}` (each event has `seq`). `?after=<seq>` or the `Last-Event-ID` header resumes. After the replayed history the server sends `replay.done {seq}`, then pushes live. Animate only events after `replay.done`; apply earlier ones as state. `EventSource` reconnects send `Last-Event-ID` automatically.

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
| evaluation.started | task_id, memory_ids | Inspector Bob walks to the shelf and heads for the cited records (one stop per id, in order) |
| memory.checked | task_id, memory_id, with_correct, without_correct, flipped | at that record: `evaluated`; if flipped, flash red (without_correct true = harmful) or green (with_correct true = helpful); no flip: a plain nod. With `reason: "confirm failed"` shake head, record stays |
| evaluation.finished | task_id, checked, flips | inspector walks back, caption "checked N, M flips" |
| memory.promoted | memory_id, reason | `updated` (record moves to trusted shelf) |
| memory.retired | memory_id, reason, task_ids, confirmed (always true) | `forgotten` (archive) |
| memory.flagged | memory_id, reason | mark record red (no existing action; add a flag state) |
| memory.locked | memory_id, owner | lock badge on the record |
| memory.resolved | memory_id, owner, action, new_id | owner decision; clear the red flag |
| memory.corrected | memory_id, new_id, author | old record replaced by new_id (memory.added and memory.retired also fire) |
| replay.done | seq | history finished; animate only events after this |

Note: the server emits episode.ingested, memory.retrieved, answer.produced; the core emits the memory.* and evidence.* events on the same bus.

## Permissions (Rusty Rod org mode)

Send header `X-BrainBob-Member: sales-01` on every request (fetch). For `new EventSource(url)` use `/events?member=sales-01` since headers cannot be set. **This is a demo identity marker, not authentication.**

- 401: no/unknown member. 404: not readable by this member (treat as "does not exist"). 403: you may not write there, or `authority: "approved"` without approver rights for that scope.
- Members see only: `rusty-rod`, their team path, their own individual path. Executives get no extra reads.
- `POST /episodes` body adds `authority` (`approved|tentative|discussion`); `author` defaults to the header member; `scope` defaults to the member's individual path.
- When the member switcher changes, reopen the EventSource with the new `?member=`.
