# Adding and removing memory in chat

Ask directly to save a personal note from the current member's chat. For example:

> Remember: I now prefer client updates as two short paragraphs instead of three short bullets.

`Remember I prefer tea`, `Save I prefer tea to memory`, and `Add that to memory` also work. “That” uses the preceding user-authored statement, not an unrelated generated answer. If the earlier message was a question or the reference is missing, Bob asks for the exact note. A plain statement alone remains read-only until the user requests a save.

This is an explicit command route, not autonomous model tool selection. The frontend sends the note to `POST /episodes` under the represented member's own individual scope, with their explicit personal approval. The existing backend models extract candidate facts and compare them with saved memories; backend permissions, dates, authority and locks determine whether to add, supersede, retain as tentative, or reject. The client does not select a memory to overwrite or call the manual correction endpoint.

The `save_memory` AG-UI tool displays the actual request and returned decisions. Failed requests are errors; tentative and rejected candidates are not reported as successful updates.

To remove a note, say `Delete that from memory` immediately after a successful save, `Forget that`, or `Delete memory m123` using the record's actual ID. You can also quote a distinctive portion of a record: `Remove my planning day is Tuesday from memory`. The bridge reads the current member's visible records and requires one unambiguous match before calling `POST /memories/{id}/retire`. Multiple matches produce a choice of IDs; missing matches and bulk requests do not mutate anything. A rejected save does not make the conflicting record a deletion target. References reset when the member changes.

The `retire_memory` tool reports success only when the backend returns that same record with `status: retired`. The record is removed from active use; its source and history remain available. Repeating removal of a retired record makes no additional write. Backend scope permissions and locked-record ownership still apply. These operations emit the existing backend events that drive the scene and retracing; the chat does not fabricate animation events.

This is explicit command routing, not autonomous model tool selection or arbitrary semantic intent detection. Other questions, quoted commands and negations remain read-only. The identity selector remains a development identity marker, not authentication.

Verified locally on October 17, 2026: chat ingestion created m75, superseded m74, and a separate fresh session cited m75. Evidence is in `docs/demo/v2-agent-chat-20261017/backend-events.json`. The side panel was used only to inspect the resulting source and history.
