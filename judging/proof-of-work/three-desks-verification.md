# Three independent desk sessions

Implementation: `9d7e78a09b19974d518bf169bd912e1c54d2ce7d`, October 17, 2026, 2:19:10 PM PDT. Local commit at capture time.

- Iris, Maya, and Mara occupy the left, center, and right desks. All desks/Bobs face the initial viewer direction; computer screens and keyboards point toward the seated operator. Monitor rear vents make the orientation visible.
- Each desk resumes its own chat and file. Account-menu desk shortcuts provide the same keyboard-accessible action. New session or replacing a person resets only the selected desk; stale callbacks from its old revision are ignored.
- Browser `/demo`: clicked Mara’s Bob, submitted an Executive prompt, opened Iris’s physical folder, and resumed Mara through the account menu. Mara’s transcript persisted; Iris’s file showed her Individual, Engineering, and Organization records.
- Browser `/`: separate Maya/Iris composer drafts persisted across desk switches. Exactly one canvas and one visible workspace were present in the DOM. The backend connection was offline, so no live HTTP answer or concurrent inference claim is made for this verification.
- Only the selected workspace subscribes to SSE; other desk agents retain local request/chat state. Re-selecting resumes that desk’s cursor. This subscription lifecycle was code-reviewed; successful live reconnect remains to be verified against the backend.
- All 52 frontend tests across 10 files passed, plus TypeScript and production build. New tests cover independent simultaneous request states, resetting one desk without affecting others, and rejecting callbacks from replaced revisions.

These are three browser-local sessions, not discovery of backend-wide running agents. Reloading clears their conversations. `/demo` remains scripted; a walkthrough step change refreshes that step’s context. No backend or benchmark source was edited for this milestone.

The native [scene screenshot](screenshots/32-three-active-sessions.jpg) was captured at 2:19:30 PM PDT from the committed frontend. [Metadata](screenshots/three-desk-capture.json) records the exact timestamp. Unrelated teammate documentation edits were present in the shared workspace and were not included in this feature commit.
