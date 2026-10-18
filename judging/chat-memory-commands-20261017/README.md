# Conversational memory verification

Implementation: `03d1cff` (explicit commands) and `d7471d7` (Nemotron routing and current-memory context).

Live verification on October 17, 2026:

- An ordinary statement saved notebook Sunbeam as m79.
- “Actually, it is called Moonbeam now” produced m80, superseding m79 through the backend.
- A separate fresh browser chat retrieved Moonbeam and cited m80.
- Earlier, “add that to memory” followed by “delete that from memory” created and retired the benign Lemon Ledger note, m76. Its history remains available.
- The Atlas brief follow-up passed three live planning calls and produced a brief in the browser rather than another topic-selection question.
- 76 frontend tests and TypeScript checks passed, including malformed/truncated model output, bounded recovery, stale context, permissions, ambiguous deletion and rejection handling.

`verification.json` contains a narrow record snapshot and limitations. The images are unaltered browser captures. `save-and-retire.png` and `retired-history.png` were captured earlier during the explicit-command verification; `nemotron-correction-recall.png` was captured after d7471d7. Unrelated README, storyboard and existing proof changes were present in the shared checkout. No claim is made that a screenshot alone proves inference or persistence.

The old generic catch discarded the original red-banner cause; it cannot be retroactively identified. The repaired route constrains output, retries invalid plans once, fails closed and returns specific error categories. This is direct Nemotron inference alongside the memory backend. The NemoClaw sandbox has not been live-verified here.

Publication alignment: original local commits `03d1cff` and `d7471d7` were ported to `0fd412f` and `ceffbfa` on main `2b0aed7`. Chat source files are byte-identical. The isolated PR branch passes the same 76 tests and type checks; original screenshot provenance is retained.
