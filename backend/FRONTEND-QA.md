# Frontend Questions: Decisions

Answers to Jerel's seven questions (11:45 PT). Rule used throughout: build on what exists (memories, statuses, the event log) and add no new mechanism unless needed. Status column says what is live.

| # | Topic | Decision | Status |
| --- | --- | --- | --- |
| 1 | Scope | Scope is a path: `krusty-krab`, `krusty-krab/sales`, `krusty-krab/sales/john`. Writes carry a `scope`. Reads carry a `reader` path and see memories whose scope equals the reader path or is an ancestor of it (John sees Sales and Krusty Krab memories; Sales does not see John's). No `reader` means no filter (benchmarks). Display names are labels; paths use slugs. | live (12:00) |
| 2 | Updates and deletion | Memories are immutable. A correction is a new memory with `supersedes: <old id>`; the old memory is retired with reason `superseded by <new id>`. There is no hard delete: retired memories stay for retracing and as tombstones. | live (12:00) |
| 3 | Evaluation events | New events: `evaluation.started {task_id, memory_ids}`, `memory.checked {task_id, memory_id, with_correct, without_correct, flipped}` for every check including no flip, `evaluation.finished {task_id, checked, flips}`. The evaluator checks the memories the agent **cited** for that task, not every memory in the brain. The scene should say "checks the cited memories". | after the stress test finishes (same file) |
| 4 | Reliable replay | Every event gets `seq` (monotonic integer, persisted in `events.jsonl`, continues after restart). SSE sends `id: <seq>`. `GET /events?after=<seq>` or the `Last-Event-ID` header resumes. After replaying history the server sends `replay.done {seq}`. Animate only events after `replay.done`; apply earlier ones as state. | live (12:00) |
| 5 | Inspection | `memory.origin` is the episode id (bug fix: it was the source label). `GET /episodes/{id}` returns the original text, date and source. `GET /memories/{id}/history` returns the supersedes chain and every status change, read from the event log. | live (12:00) |
| 6 | Locked records | `POST /memories/{id}/lock {owner}` sets status `locked` and records `owner`. The evaluator never retires a locked memory; if it is judged harmful it is flagged (`memory.flagged`). Only the recorded owner can resolve it: `POST /memories/{id}/resolve {owner, action: keep or retire or correct, text?}`. Demo: Mr. Krabs locks a house rule. | live (12:00) |
| 7 | Retirement confirmation | Correct, the server's `/review` used an always-true confirmation. Fix: confirm by a fresh, uncached re-answer of a task the memory harmed, with that memory removed, graded by the same judge against the stored correct answer. `memory.retired` carries `confirmed: true`. If the check does not confirm, the memory stays in trial. Until this ships, the UI must not say a retirement was confirmed. | after the stress test finishes (needs `llm.complete(..., fresh=True)`) |

## New and changed endpoints

| method | path | body or query | returns |
| --- | --- | --- | --- |
| POST | /episodes | `{text, date?, source?, scope?, author?}` | `{episode_id, memories}` |
| POST | /ask | `{question, now?, reader?}` | `{task_id, answer, cited_ids, memories}` |
| GET | /episodes/{id} | | `{id, text, date, source, scope}` |
| GET | /memories/{id}/history | | `{chain: [Memory], events: [event]}` |
| POST | /memories/{id}/correct | `{text, author}` | `{memory, retired_id}` |
| POST | /memories/{id}/retire | `{reason, author}` | `{memory}` |
| POST | /memories/{id}/lock | `{owner}` | `{memory}` |
| POST | /memories/{id}/resolve | `{owner, action, text?}` | `{memory}`; 403 if not the owner |
| GET | /events | `?after=<seq>` or `Last-Event-ID` | SSE with `id: <seq>`, then `replay.done` |

`Memory` gains `supersedes: str or null` and `owner: str or null`.

## Implementation notes (12:00)

- Anyone other than the owner gets 403 on `/correct` or `/retire` of a locked memory; the owner uses `/resolve`.
- `resolve` with `correct` returns the new memory, which inherits `locked` and `owner`. `keep` only clears the flag.
- `/correct` skips dedupe and tombstone checks, so a small correction is not rejected as a near-copy of what it replaces.
- Always send `scope` on `/episodes` when you send `reader` on `/ask`: memories written without a scope default to `team` and are invisible to a reader path that does not start with `team`.
- `replay.done` is not stored in the event log.
