# Org-mode frontend alignment verification

October 17, 2026. Implementation `80c8c79b9cc744cd028e2ef0b72423ffd79b9117`; merge `e0888aa` incorporates GitHub main through `6c6e3e9`. Bonan’s backend source was not edited.

## Automated checks

- `pnpm --filter @brainbob/web typecheck`: pass.
- `pnpm --filter @brainbob/web test`: 42 tests across 7 files pass.
- `pnpm --filter @brainbob/web build`: pass, all routes generated.
- `uv run --no-project --with pytest --with fastapi --with httpx --with sse-starlette --with openai --with rank-bm25 --with pyarrow python -m pytest backend/tests -q`: 69 pass. Initial run lacked PyArrow; rerun with the adapter dependency passed.
- New tests cover every API operation’s selected-member header, member-specific SSE URL and resume sequence, tentative metadata, org-mode maintenance decisions, and conflict/audit events distinct from usefulness.

## Browser observations

A temporary loopback server used the merged `create_app`, `Org`, `MemoryStore`, and event bus. It seeded in-memory organization, Sales, Maya, Executive, and tentative Engineering records. Model calls were replaced with explicitly labeled canned answers and a tentative maintenance decision. Source episodes were temporary files outside the repository. This was not a Crusoe run.

- Maya’s view loaded organization, Sales, and her own record; Executive and Engineering records were absent.
- Switching to Iris closed the prior view and opened a fresh Engineering stream. Sales and Maya records were absent; organization and tentative Engineering records were shown.
- The tentative inspector displayed authority, fixture model attribution, and original source. It explicitly said this was not an approved commitment.
- Remember accepted the org-mode decision response and rendered a tentative receipt; SSE supplied the resulting record.
- Ask returned the canned backend answer and citations, which opened the original source.
- Conflict and audit events in replay did not disconnect the stream or produce a usefulness verdict.

The fixture was stopped after QA. Real inference, authenticated identity, full access-isolation assurance, and live session-file assembly remain separate validation/integration work. The legacy Node fixture remains available and accepts the member header through CORS, but it is not an authorization test.
