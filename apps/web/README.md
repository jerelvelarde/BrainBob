# Live UI and backend integration

The home route uses the Python backend for memory, chat, mutations, and SSE.
`/demo` and `/rehearsal` contain scripted demonstrations; they are not model
quality measurements.

From the repository root, install backend dependencies once:

```sh
uv venv backend/.venv
uv pip install --python backend/.venv/bin/python -r backend/requirements.txt
```

For live inference, run `cd backend && .venv/bin/python server.py` in one
terminal and `pnpm dev` at the repository root in another. The live backend
requires the configured Crusoe credentials and makes model calls. Start without
`--legacy` so the member switcher and Rusty Rod permissions apply.

Browser requests default to `/api/brainbob` on the UI origin. Next forwards
HTTP and SSE to `BRAINBOB_API_URL`, defaulting to `http://127.0.0.1:3001`.
For a remote backend, set this server environment variable before starting Next
and before production builds. The Next host must be able to reach that address.
`NEXT_PUBLIC_BRAINBOB_API_URL` can explicitly bypass the proxy, but then the API
must permit the browser origin through CORS. See `.env.example`.

## Repeatable integration check without inference

Stop any backend on port 3001 before starting the temporary test server:

```sh
backend/.venv/bin/python apps/web/scripts/backend-contract-server.py
```

Run `pnpm dev` in a second terminal, then:

```sh
node apps/web/scripts/backend-smoke.mjs
```

Set `UI_URL` for a different local UI port. This smoke test covers the actual
Next proxy, Python HTTP routes, ACL, maintenance, memory store, SSE replay and
resume. It checks ingestion, retrieval, chat, feedback, review, correction,
history, source inspection, and lock resolution. The Python server substitutes
deterministic extraction/answers/judgment and explicitly forbids model calls;
all memory state is temporary. It cannot establish model quality or benchmark
scores. Stop it before returning to the real backend.

The API's SSE response uses `Cache-Control: no-store, no-transform` so Next and
other compliant proxies deliver small events immediately instead of buffering
them for compression. Demo member headers identify a selected account; they
are not production authentication.
