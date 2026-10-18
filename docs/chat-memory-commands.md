# Conversational memory in chat

The live chat uses NVIDIA Nemotron 3 Super on Crusoe to choose a conversational action. You can ask questions, request a draft, share a durable fact, correct a preference, or ask Bob to forget a record without switching modes or memorizing command syntax.

Examples:

- “How do I prefer client updates?” retrieves the current preference.
- “Actually, I want bullet points now, not paragraphs” resolves the subject from the conversation and submits a correction.
- “The Atlas pilot added real-time voice as a requirement” records a personal report, without approving an organization-wide change.
- “Delete that from memory” removes one unambiguous saved record from active use.
- “Give me a brief” after discussing Atlas requests the brief; “everything” is a request to cover the available context, not to ask for another topic selection.

## Execution and permissions

`POST /api/conversation` is a server-side Next route outside the scored Python backend. It loads the selected member's permitted active memories, then asks Nemotron for one schema-constrained action: ask, reply, save, or retire. The selected action is validated again locally. Invalid or truncated output gets one plan-only retry. Failed planning never falls through to a memory write, and errors distinguish invalid output, timeout, configuration and connection failures. Credentials stay on the server.

The model selects an action; the existing backend executes and enforces it:

| Action | Execution |
| --- | --- |
| Ask / draft / brief | Existing `POST /ask`, preserving task IDs, citations, evaluation compatibility and session files |
| General conversation | A concise Nemotron reply, with no memory mutation |
| Personal fact or preference | `POST /episodes` in the current member's individual scope, with personal approval |
| Project / team / client update | `POST /episodes` in the current member's individual scope, with discussion authority |
| Forget | Re-read visible records and call `POST /memories/{id}/retire` only for one identified record |

The backend's extraction and maintenance models decide whether to add, supersede, retain a conflict as tentative, or reject. The chat does not call the manual correction endpoint or silently grant shared approval. Locks, scope permissions and owner checks remain in the backend. Removed records retain their source and history. The identity selector is still a development identity marker, not authentication.

The AG-UI renderers show actual `understand_request`, `consult_memory`, `save_memory` and `retire_memory` results. The interpretation receipt identifies the actual model. Save/retire confirmations come from backend results, not generated assurances. Existing backend events drive the 3D animations. The explicit command parser remains available for non-conversational bridge consumers and regression tests.

## Current memory wins over old replies

A successful save or retirement invalidates old answering context. Changes to the live memory version also invalidate that context. This prevents a retired paragraph preference from being reintroduced by an older assistant reply after the backend has already stored a bullet-point correction. Historical UI receipts remain snapshots of their original answers.

The router sees up to 200 permitted active records, with each text capped at 1,200 characters, plus up to ten prior conversational messages. This bounded live-app path is not a new benchmark result or a proof of perfect intent classification. Ambiguous removal requests should ask which record; no bulk deletion is implemented.

## Configuration and integration status

The route defaults to `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B` at Crusoe's inference endpoint. Override it with `BRAINBOB_CHAT_MODEL`, `BRAINBOB_CHAT_BASE_URL`, and `BRAINBOB_CHAT_API_KEY`; agent/base configuration remains a fallback. The local key file is `~/.config/crusoe/api.key`. No key belongs in a public environment variable or Git.

NemoClaw/OpenClaw's adapter and the Nano memory-summary integration are present from main. This chat path uses the direct Nemotron connection and existing memory API; it does not claim to run inside a verified NemoClaw sandbox.
