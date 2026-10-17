# Tier cabinets and agent session files

The room has Individual, Team, and Organization cabinets. Each drawer represents a person, team, or organization. A Sales member can access their own drawer, Sales, and Rusty Rod; Executive and other people's personal drawers stay closed. Atlas Harbor is a fictional client, not an inherited permission scope.

A session file is a snapshot of the accessible records returned for an agent task. It does not create a new permission scope or replace canonical memory. Source data comes from [the synthetic company corpus](../fixtures/company/rusty-rod.json); the running backend performs extraction, retrieval, and answering.

## Three independent desks

Iris sits on the left, Maya in the center, and Mara on the right. Click a desk/Bob to resume its chat or its folder to inspect its session file. The account popup also provides keyboard-accessible desk shortcuts. New session or selecting a replacement person resets only the selected desk.

Each desk has its own CopilotKit agent, draft, chat history, and request state. Ask drives Working, Answer ready, Failed, or Stopped. Successful Ask turns supply up to four turns of follow-up context. Remember, Usefulness, and Review do not replace the answer file or contribute evaluation gold to subsequent answering context. Closing chat or switching desks preserves conversations. Reloading clears browser-local conversations and files.

Only the selected desk renders a canvas and subscribes to SSE; its saved cursor resumes on return. Other desk agents retain in-flight requests. Late callbacks from replaced desk revisions are ignored. Bob writes while a request is running; pause and reduced-motion preferences freeze the gesture.

## Suggested actions

The personalized welcome offers three actions based on the selected person's accessible records: draft an update, prepare a call/handoff/decision brief, and refine a message or clarify an unresolved question. Memory tiers remain in the file inspector, not in suggestion labels. Retired and flagged records are excluded; tentative context is explicit. Empty stores produce generic discovery actions, not invented company facts.

Suggestions are deterministic UI recommendations grounded in the loaded records. They do not execute local scripts or generate answers. Selecting one calls `/ask`, which retrieves the current evidence again.

## Inspection and persistence

The full-screen **Memory** panel opens on **Summary**, an overview of current saved memory. Switch to **Memory files** to inspect records and reply evidence. Summary uses its own read-only Crusoe Nano role and never changes the reply snapshot; it is not evidence of what the answering model saw. [Summary behavior](live-workspace.md#memory-summary-and-files).

After Ask completes, the file snapshots its task ID, question, answer, cited IDs, and accessible `/ask.memories`, grouped by Individual, Team, and Organization. Download exports JSON. Later SSE changes do not rewrite this snapshot; the next Ask creates a new current file at that desk. Before an answer, or after failure/cancellation, no completed file is invented.

Source/history controls open the current memory inspector. Source bodies and the exact rendered model prompt are not embedded in the file. Returned retrieval records alone do not establish context completeness. These are browser-local sessions, not a global session registry. Canonical memory, source episodes, and events persist on the backend; durable conversations, historical task files, and complete prompt tracing remain future backend work.

The former scripted session assembler and scripted chat agent were removed. Old URLs redirect to `/`. Historical screenshots in proof of work document the earlier iterations.
