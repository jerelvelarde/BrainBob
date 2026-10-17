# Active session desk verification

Implementation: `2e80be444317f8fd3fc91256f096afc47d9907a9`, October 17, 2026, 1:35:20 PM PDT. Local commit at capture time.

- 46 frontend tests across 8 files passed. New coverage exercises selected-scope filtering, deep snapshots, stale response suppression, empty answers, cancellation, and request failure lifecycle.
- TypeScript and production build passed. The final follow-up adjusted only the desk label position and canvas accessibility description.
- Browser: clicking the seated Bob opened the live file before a request; its empty state offered chat and disabled download.
- Browser with the existing local Node HTTP/SSE contract fixture: Ask returned three memories, displayed in the correct Individual / Team / Organization sections. A source/history link opened the existing memory inspector. Selecting Iris cleared Maya’s chat and file.
- Browser: clicking the physical folder in `/demo` opened the existing synthetic dossier with five task-relevant memories.
- Screenshots were captured after the implementation commit. Exact capture times and modes are in `screenshots/session-bob-capture.json`. The fixture was stopped after testing.

This is a view of the selected local chat, not a backend-wide list of active sessions. Returned retrieval records are not a full model-input trace. Files remain in browser state until the next Ask, identity change, or reload; server persistence remains pending. No inference call or authorization assurance is claimed from the fixture. No backend or benchmark source was changed.
