# Spec: Memory Correctness for Rusty Rod

Source of requirements: Jerel's prompt (12:36 PT), [docs/sample-company.md](../docs/sample-company.md), and the Custom BrainBob Suite in [docs/benchmarks.md](../docs/benchmarks.md). This file fixes the interfaces so the work can run in parallel lanes. Everything here is additive: existing modules keep working.

## Two separate signals

| Signal | Question it answers | Module |
| --- | --- | --- |
| Correctness | Is this memory supported, current and authorized? | `brainbob/maintain.py` (at write time) and `brainbob/audit.py` (recent-conversation audit) |
| Usefulness | Did this memory change an answer's correctness? | `brainbob/evaluator.py` (leave-one-out, unchanged) |

A memory helping an answer does not prove it is correct. Reports keep the two apart.

## Organization and permissions (`brainbob/acl.py`, fixture `fixtures/rusty_rod/org.json`)

- Members: `exec-01..03` (team `executive`, role `approver`), `sales-01..05` (team `sales`), `eng-01..10` (team `engineering`).
- Scope paths: org `rusty-rod`; team `rusty-rod/<team>`; individual `rusty-rod/<team>/<member>`. 22 scopes.
- `can_read(member, scope)`: true only for `rusty-rod`, the member's team path, and the member's own individual path. Executives get no extra reads.
- `can_write(member, scope)`: own individual path, own team path, or `rusty-rod`.
- `can_approve(member, scope)`: `rusty-rod` needs role `approver`; a team path needs membership of that team; an individual path needs the member themself.
- Every read endpoint takes the viewer from header `X-BrainBob-Member` (demo identity, not authentication; documented as such) and filters by `can_read`: `/ask` retrieval, `/memories`, `/memories/{id}`, `/memories/{id}/history`, `/episodes/{id}`, `/report`, and `/events` (an event is delivered only if every memory or episode it references is readable). Unreadable ids return 404, not 403, so their existence does not leak.
- Writes check `can_write`; an episode with `authority: "approved"` also needs `can_approve`, otherwise 403.

## Data model additions (`brainbob/types.py`)

- `Episode`: add `author` (member id), `scope`, `authority` in `{"approved", "tentative", "discussion"}` (default `discussion`).
- `Memory`: add `authority` (copied from the episode), `model` (actual model id that wrote it), and status value `tentative` besides trial/promoted/retired/locked.
- Every event that creates or changes a memory carries `model` and, for evaluator decisions, the evaluator's model id.

## Write-time maintenance (`brainbob/maintain.py`)

`ingest(episode, store, acl) -> list[Decision]` wraps `curator.extract`. For each extracted candidate:

1. Find active memories in readable scopes of the author that may describe the same thing (BM25 top 5), then one judge call per pair: `same`, `conflict` (same subject, different value) or `unrelated`. JSON output.
2. Deterministic rules:

| Case | Action | Event |
| --- | --- | --- |
| `same` | drop the candidate as a duplicate | `memory.rejected` reason `duplicate` |
| `conflict`, candidate `approved`, author can approve the old memory's scope, candidate date >= old date | add candidate, retire old with `supersedes` link | `memory.added`, `memory.retired` reason `superseded by <id>`, `memory.corrected` |
| `conflict`, candidate `approved`, but older than the old memory | reject as stale | `memory.rejected` reason `stale` |
| `conflict`, candidate `tentative` or `discussion`, or author cannot approve | add candidate with status `tentative`, old stays active | `memory.added`, `memory.conflict {new_id, old_id}` |
| `unrelated` everywhere | add normally | `memory.added` |

3. Never delete because evidence is missing.

The append-only baseline is `curator.ingest` alone (every candidate becomes active).

## Agent answers

`agent.answer` shows each memory with its date, scope, authority and status. Tentative memories are labeled "tentative, conflicts with [mX]". The prompt says: rely on approved and active memories; mention unresolved tentative conflicts; answer "I don't know" when the memories do not contain the answer.

## Recent-conversation audit (`brainbob/audit.py`)

`audit_recent(store, episodes, latest=50, sample=10, seed) -> AuditReport`: sample 10 of the latest 50 eligible episodes without replacement, record the seed and selected ids, and judge each related active memory against each sampled episode as `supported`, `contradicted` or `insufficient`. `contradicted` with authorized evidence proposes a correction through `maintain`; `insufficient` never changes anything. The report separates evidence coverage (was the decisive episode in the sample) from judgment accuracy (given the evidence, was the call right). Events: `audit.started {seed, eligible_ids, sampled_ids}`, `audit.checked {memory_id, episode_id, verdict}`, `audit.finished`.

## Correctness suite (`fixtures/rusty_rod/scenarios.json`, runner `bench.py correctness`)

- 30 held-out scenarios, 5 per group (Extraction, Updates, Retention, Forgetting, Shared handoff, Insufficient evidence), plus 6 development scenarios used only for prompt work. Scenario 1 of Updates is the Atlas scenario from sample-company.md.
- A scenario is a list of episodes (`author`, `scope`, `authority`, `date`, `text`) and a list of questions (`member`, `question`, `expect`): accepted answer strings, `abstain`, or `uncertain`; `forbid`: stale values that must not appear; `must_not_retrieve`: scopes the member cannot read. Expected outcomes are written before running anything. Gold never enters memory or agent context.
- Conditions with the same answering model and retrieval budget (top 10): `none`, `append_only`, `maintained`. Each question is answered by a fresh agent.
- Metrics per condition: answer accuracy, stale-fact usage, correct-update rate, unjustified forgetting (an expected-active memory retired), abstention and uncertainty accuracy, access leakage (must be 0; deterministic), and cost per stage. Paired bootstrap 95% intervals for maintained minus append_only.
- Deterministic system checks (pytest, no model): scope isolation on every endpoint, stale concurrent writes, duplicate operations, read-only replay.

## Integration status to document

NemoClaw sandboxes and Switchyard routing are not integrated. All inference goes directly to Crusoe Managed Inference with NVIDIA Nemotron models (Lightning for writing and answering) and `openai/gpt-oss-120b` for judging.
