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
