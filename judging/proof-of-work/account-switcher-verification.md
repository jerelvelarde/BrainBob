# Scene account switcher verification

Implementation: `2c7770dbe3ccaafcbd852304a1dbe68e705ab872`, October 17, 2026, 2:04:50 PM PDT. Local commit at capture time.

- Replaced the top-left reader select with a bottom-left account-style control showing the current person’s initials, name, and team. The popup opens above it and searches all 18 demo identities by name or team.
- New session opens a clean chat for the same person. Selecting another person starts a fresh context and returns to the scene. Choosing the current person simply closes the menu.
- Browser checks on `/demo`: Maya → Iris updated the scene identity and personalized Engineering welcome. After a scripted conversation, New session restored the welcome with the same saved context and no prior transcript.
- Browser checks on `/` with the existing loopback HTTP fixture: Ask completed; New session cleared the transcript, citations, and answer file while reloading all three accessible fixture memories. Switching to Iris remounted the context and restored focus to the new account control. The fixture was stopped after testing.
- Keyboard Enter opened the popup and focused search. Escape closed it and restored trigger focus. Clicking Zoom dismissed it while retaining focus on Zoom. Search with no match showed clear feedback. Repeated toggles left one usable popup.
- Desktop 1280 × 720 and mobile 390 × 844 layouts were visually checked; the mobile scene controls move above the account row. The viewport override was reset. The small entrance uses a recommended 150 ms opacity/transform animation; closing unmounts immediately with no delayed callbacks. Existing reduced-motion CSS disables the entrance; this was code-reviewed, not device-profiled.
- All 50 existing frontend tests passed. TypeScript and production build passed; a final null-related-target blur guard was followed by another successful TypeScript check. No new unit tests were added for the reversible presentation change.

Screenshots are native browser captures of synthetic `/demo` data from the committed frontend, with application sources unchanged. [Capture metadata](screenshots/account-switcher-captures.json) records exact times. These controls switch demo identities; they do not implement authenticated login/logout. No inference, backend source changes, or benchmark claims are part of this milestone.
