# BrainBob backend contract

Task-agnostic shared memory for an agent team. Deep modules, shallow interfaces.
Python 3.12. All model calls go to Crusoe Managed Inference.

## The loop

```
write:  Episode --curator.ingest--> memory.add          (dedupe + tombstones in code)
read:   Task --memory.search--> agent.answer --> Answer(text, cited_ids)
audit:  evaluator.observe: drop each cited memory, re-answer, task.grade both.
        If correctness flips -> evidence on that memory and its author.
        evaluator.review -> promote / retire (locked: flag only)
```

The core never knows which benchmark or product it serves. A task only brings
`episodes` (what happened) and `Task.grade` (was this answer right).

## Layout

```
backend/
  brainbob/            core, task-agnostic
    types.py           Episode, Memory, Task, Answer, Evidence, Decision
    llm.py             complete(role, messages) -> str
    memory.py          MemoryStore
    curator.py         ingest(episode, store) -> list[Memory]
    agent.py           answer(question, memories, now=None) -> Answer
    evaluator.py       Evaluator(store, strategy).observe / review / report
    events.py          emit(type, **data); subscribe() -> queue; events.jsonl
  adapters/
    longmemeval.py     one memory space per question; no evaluator (would leak)
    locomo.py          one memory space per conversation; audit/heldout split
  bench.py             runs an adapter through the loop, writes results/
  server.py            HTTP + SSE for the 3D frontend
  data/ cache/ results/   (gitignored)
```

## Types (brainbob/types.py)

```python
Episode(id: str, text: str, date: str, source: str)
Memory(id: str, text: str, author: str, origin: str, date: str,
       status: "trial"|"promoted"|"retired"|"locked", scope: str = "team")
Task(id: str, question: str, grade: Callable[[str], bool], now: str | None = None)
Answer(text: str, cited_ids: list[str])
Evidence(memory_id, shown: bool, correct: bool, task_id)   # one row per observation
Decision(memory_id, action: "promote"|"retire"|"flag", reason: str, task_ids: list[str])
```

## Module interfaces

| Module | Interface | Hides |
|---|---|---|
| llm | `complete(role, messages, **kw) -> str`, `usage() -> dict` | role->model map, Crusoe client, key file, retries, disk cache, cost, stripping think text / code fences / leading newlines |
| memory | `MemoryStore(path=None)`: `add(text, *, author, origin, date, scope="team", status="trial") -> (Memory or None, reason)`, `search(query, k=40) -> list[Memory]` (active only), `get(id)`, `all()`, `set_status(id, status, reason)` | BM25 index, normalized dedupe, tombstone Jaccard >= 0.8 vs retired, jsonl persistence |
| curator | `ingest(episode, store, author="curator") -> list[Memory]` | extraction prompt, JSON/bullet fallback parsing |
| agent | `answer(question, memories, now=None) -> Answer` | answer prompt; memories numbered [m1]..; model ends with `CITED: m3, m7`; parse to memory ids |
| evaluator | `Evaluator(store, strategy=leave_one_out, min_changes=3)`: `observe(task, memories, answer_fn) -> list[Evidence]`, `review(confirm_fn) -> list[Decision]`, `report() -> dict` | strategies (leave_one_out, sample_pct, random_half_hide), flip-only evidence, confirm-before-retire, author ledger |
| events | `emit(type, **data)`, `subscribe() -> queue.Queue`, `history() -> list` | in-process bus + append to events.jsonl |

Roles -> models (llm.py):

| role | model | notes |
|---|---|---|
| curator | nvidia/Nemotron-3.5-Lightning-30B-A3B | thinking off |
| agent | nvidia/Nemotron-3.5-Lightning-30B-A3B | temperature 0, max_tokens >= 1024; Super ($0.30/$2.40) only via env BRAINBOB_AGENT_MODEL, and never mixed across conditions of one comparison |
| judge | openai/gpt-oss-120b | temperature 0; different family from agent |

Anti-leak rule: gold answers are only ever used inside `Task.grade` as a
right/wrong signal. Nothing derived from a gold answer is written to memory.

## Events (for the 3D frontend)

Every state change emits one JSON event: `{"type", "ts", ...data}`.

| type | data | 3D visual (friend's table) |
|---|---|---|
| episode.ingested | episode_id, source, n_memories | conversation arrives |
| memory.added | memory | worker files a new record |
| memory.rejected | text, reason (duplicate / tombstone) | record bounced at the cabinet |
| memory.retrieved | task_id, memory_ids | worker pulls records |
| answer.produced | task_id, answer, cited_ids | answer delivered |
| evidence.recorded | memory_id, author, shown, correct, task_id | inspector checks a record |
| memory.promoted | memory_id, reason | record moved to the trusted shelf |
| memory.retired | memory_id, reason, task_ids | record archived |
| memory.flagged | memory_id, reason | locked record marked red for its owner |

## HTTP API (server.py, port 3001)

`create_app(store, curator, agent, evaluator, judge)` builds the app, so it can be tested with fakes.

| method | path | body | returns |
|---|---|---|---|
| POST | /episodes | {text, date?, source?} | {episode_id, memories: [Memory]} |
| POST | /ask | {question, now?} | {task_id, answer, cited_ids, memories: [Memory]} |
| POST | /feedback | {task_id, correct_answer} | {evidence: [Evidence]}  (grade = judge(question, correct_answer, answer); runs leave_one_out on that task) |
| POST | /review | {} | {decisions: [Decision]} |
| GET | /memories | ?status= | [Memory + evidence counts] |
| GET | /report | | author ledger + retire reasons |
| GET | /events | | SSE stream; replays history first |

CORS open for http://127.0.0.1:3000 and http://localhost:3000.
