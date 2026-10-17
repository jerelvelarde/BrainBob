# Personal memory updates in chat

Start a message with `Remember:` (or `Please remember:`) to save a personal note from the current member's chat. For example:

> Remember: I now prefer client updates as two short paragraphs instead of three short bullets.

This is an explicit command route, not autonomous model tool selection. The frontend sends the note to `POST /episodes` under the represented member's own individual scope, with their explicit personal approval. The existing backend models extract candidate facts and compare them with saved memories; backend permissions, dates, authority and locks determine whether to add, supersede, retain as tentative, or reject. The client does not select a memory to overwrite or call the manual correction endpoint.

The `save_memory` AG-UI tool displays the actual request and returned decisions. Failed requests are errors; tentative and rejected candidates are not reported as successful updates. Ordinary messages and questions remain read-only. The identity selector remains a development identity marker, not authentication.

Verified locally on October 17, 2026: chat ingestion created m75, superseded m74, and a separate fresh session cited m75. Evidence is in `docs/demo/v2-agent-chat-20261017/backend-events.json`. The side panel was used only to inspect the resulting source and history.
