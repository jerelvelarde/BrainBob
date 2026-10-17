# Conversation and memory inspection

BrainBob opens a normal conversation for the person at the selected desk. The composer has one purpose: send a message. The old Ask, Remember, Usefulness, and Review switches are absent from chat. Memory management remains in the inspector.

The welcome screen offers three short actions derived from accessible, active company records. Their visible messages contain the request, while formatting and grounding instructions stay inside the adapter. Chats remain separate per desk and identity.

## Activity and tool rendering

`BackendChatAgent` wraps the real `POST /ask` request in AG-UI `TOOL_CALL_START`, `TOOL_CALL_ARGS`, `TOOL_CALL_END`, and `TOOL_CALL_RESULT` events named `consult_memory`. CopilotKit's registered tool renderer displays a collapsed **Working… / Worked for …** disclosure. Expanding it shows the request status, returned memory count, cited-memory previews, and a link to the explorer.

The backend retrieves and answers within one HTTP request. The elapsed time is measured across that entire request, not model thinking time or an isolated search duration. Counts appear only after the response. Failed and cancelled requests never display a successful retrieval receipt. No fabricated reasoning, inference stages, or model chain of thought is shown.

## Sources and snapshots

Each assistant message has a distinct message ID bound to its own answer and memory snapshot. Follow-ups do not replace earlier evidence. Up to three compact source chips appear beneath each reply; the memory count opens all cited records. These are answer-level citations supplied by the backend, not claims of sentence-level attribution.

The **Memory** drawer defaults to sources used in the selected reply. **Saved** shows the currently accessible, non-retired records. Before the first answer, it opens directly to saved context. Sources are grouped as about you, your team, and your organization only inside the explorer.

Clicking a source opens the existing original-conversation and correction-history inspector. A saved reply's snapshot stays unchanged; its source inspector shows the current record. Snapshot downloads include the actual returned records and answer. They are not a full model prompt or source archive.

On narrow screens, inspection covers the conversation and makes it inert. Escape dismisses inspection first, then the chat. Closing chat returns to the brain and keeps the current desk's conversation available.

This interface uses the existing CopilotKit message, Markdown, composer, copy, cancellation, and tool-rendering primitives. It adds no backend endpoints and does not automatically persist every chat message as memory.

## Brain beside the conversation

The desktop chat keeps a wide 3D memory office beside the transcript. The same event queue drives this view and the full brain view, with one mounted scene for the selected desk. Source inspection uses the lower half of the panel so the Bobs remain visible during correction and retirement. On mobile, **Brain & memory** opens the panel over the conversation; closing it returns focus to the trigger.

Idle crew stay at three stations instead of walking laps. Movement represents a memory operation: filing, retrieving, correcting, retiring, promoting, locking, flagging, resolving, or evaluating. Correctness-audit checks carry source verdict labels, separately from the cited-memory usefulness checks. Correction bookkeeping and retirement of a superseded predecessor do not trigger duplicate fire scenes. Retirement is a tombstone with history, not hard deletion.

Starting a person’s first chat, switching people, or creating a new session loads permitted context through the actual `/memories` endpoint. After that load succeeds, a presentation-only sequence collects a file from each non-empty accessible tier and delivers it to the selected desk. It is labeled **Session file**; it does not invent an SSE event, call inference, or assert that all saved context was used in an answer. Empty/failed loads do not invent files, and reconnecting does not repeat the introduction. Historical SSE replay remains state-only.

Cabinet and drawer counts use accessible, non-retired records. Click a 3D cabinet or a folder row to open Individual, Team, or Organization files. The folder browser supports search and source/history inspection. Other teams and the separate client organization show locks, never their contents or counts. The activity list is explicitly recorded history. The current action shows animation progress, not backend processing progress.

Reduced-motion mode keeps state and recorded activity current without waiting for choreography. Pause and skip affect presentation only. Backend changes and chat responses never wait for a Bob to finish walking.
