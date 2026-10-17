# Tier cabinets and agent session files

The room has **Individual, Team, and Organization cabinets**. Each drawer is a person, team, or organization. For a Sales member, the accessible drawers are their own, Sales, and Rusty Rod. Executive and other members’ individual drawers stay closed. Atlas Harbor is a fictional logistics client, not an inherited permission scope.

A **session file** combines the relevant, accessible memory needed for a specific agent task. Access covers all records in the three permitted scopes; relevance determines which current records enter this particular file. It is a derived snapshot, not a new permission scope or a replacement for canonical memory.

```mermaid
flowchart LR
    PERSONAL["Individual cabinet · Maya drawer"] --> FILE["Maya’s Atlas session file"]
    TEAM["Team cabinet · Sales drawer"] --> FILE
    SHARED["Organization cabinet · Rusty Rod drawer"] --> FILE
    CLOSED["Executive / other people / private client drawers · no access"]
    FILE --> AGENT["Agent working for Maya"]
```

## The demo file

At `/demo`, select **Maya Flores**, open **Session file**, and download `sales-01-atlas-session.md`. A seated Bob stays at the center desk with the file; clicking Bob, the folder, or its label opens the same panel. Clicking a cabinet opens its tier inspector with accessible and closed drawers; its session-file button opens the assembled file. The file contains:

- Individual: Maya’s preference for a concise, three-sentence client update.
- Team: Sales guidance to cite the approved commitment and preserve the reporting goal.
- Organization: the current Atlas delivery date, unchanged reporting goal, and the published Atlas Harbor client brief.
- Evidence: source IDs, source text, author IDs, timestamps, authority labels, and exact record revisions.

After the approved correction, November 13 replaces the retired November 6 record in the file. The earlier revision stays in the separate evidence/history view. Switching to Leo Park uses his own preference. Switching to Iris Tan adds relevant Engineering context, explicitly marking estimates as tentative and unknown dependencies as unresolved.

The unrelated bicycle-parking policy stays in memory but is excluded from this task. Other people’s private notes, other teams’ sources, and private Atlas Harbor records are excluded. A record whose source is unavailable or inaccessible is not included; a missing-evidence count marks the file as incomplete. That exclusion does not delete or retire anything.

The client brief is published into Rusty Rod organization memory. Atlas Harbor is not an ancestor or descendant of Rusty Rod; the relationship itself grants no private-data access. There remain 22 internal Rusty Rod scopes.

## Assembly contract

1. Identify the represented member, task, and memory snapshot. Authenticate this identity on the server for live operation.
2. Enforce access before relevance selection, including access to evidence. A drawer label must not reveal another member’s individual records or files.
3. Select current records relevant to the task; preserve tentative and unresolved information as labeled context. Do not treat them as approved facts.
4. Attach the exact IDs/revisions and accessible evidence. Report missing required evidence or insufficient task context rather than asserting completeness.
5. Freeze the selected context as the session’s input. Later corrections can produce a new file; retracing an earlier session must retain its earlier snapshot.
6. Let the agent read that file before working. Proposed updates afterward go through the existing write/correct/evaluate flow with their original scope and authority checks; editing the assembled file does not authorize a canonical write.

## Current implementation and handoff

The frontend assembler is deterministic and uses authored `atlas-update` relevance tags. Its Markdown download is real, but the scenario and sources are synthetic. It does not call a relevance model, establish context completeness for arbitrary tasks, or run Crusoe inference. All fixture data ships in the browser; client filtering is a presentation preview, not an access boundary.

The main HTTP/SSE route also gives the selected member a seated Bob and an inspectable session file. The current chat is the session boundary: Ask drives Working, Answer ready, Failed, or Stopped state. Remember, Usefulness, and Review do not replace its answer file. Bob writes while an Ask is in flight; pause and reduced motion freeze the gesture. The file can also be opened through the keyboard-accessible Session button.

After Ask completes, the file snapshots the returned task ID, question, answer, cited IDs, and accessible records from `/ask.memories`, grouped by Individual, Team, and Organization. It can be downloaded as JSON. Subsequent SSE changes do not rewrite this snapshot; the next Ask starts a new file, and switching members clears the previous member’s chat and file. Before Ask, or after failure/cancellation, the UI does not invent a completed file. This is the current chat’s file, not a historical file reconstructed by event retrace.

**Server-side session-file assembly, persistence, and full model-input tracing remain unimplemented.** Returned retrieval records do not establish the exact prompt or complete context supplied to the model. Source/history links open the current record inspector; source bodies are not embedded in the live file. The scene represents the selected local chat, not a global registry of concurrently running backend sessions.

Bonan’s backend handoff should provide a session/task ID, represented member, selected memory IDs/revisions, accessible source references, relevance/omission metadata, snapshot/event sequence, actual model attribution, and cost where available. Keep factual correctness, leave-one-out usefulness, and retrieval relevance distinct. Do not add a wire event until both sides agree its contract. Backend and bench remain Bonan’s files.
