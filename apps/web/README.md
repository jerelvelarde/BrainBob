# Live UI and backend integration

The home route uses the Python backend for memory, chat, mutations, and SSE.
`/demo`, `/rehearsal`, and `/character-study` redirect to the live workspace.
There are no scripted answers or generated fixture events in the app.

From the repository root, install backend dependencies once:

```sh
uv venv backend/.venv
uv pip install --python backend/.venv/bin/python -r backend/requirements.txt
```

For live inference, save the key to `~/.config/crusoe/api.key` (mode 0600) or set
`BRAINBOB_API_KEY` for the backend, then run `pnpm backend` from the repository
root. In another terminal run `pnpm seed:company`, then `pnpm dev`. The launcher
checks actual provider access and keeps persistent data in ignored `data/workspace/`.
See [the live workspace guide](../../docs/live-workspace.md) for the synthetic
source dataset, rerun behavior, and current limitations.

Browser requests default to `/api/brainbob` on the UI origin. A Node Route Handler
forwards HTTP and streams SSE to runtime `BRAINBOB_API_URL` (local default:
`http://127.0.0.1:3001`). It allows 280 seconds inside a 300-second function budget.
This avoids Vercel's 120-second external rewrite limit. Keep
`NEXT_PUBLIC_BRAINBOB_API_URL` unset for hosted use.

For the hosted demo, set the same strong `BRAINBOB_DEMO_PASSWORD` on Next and the
backend. Username is `brainbob`; selected members remain fictional personas.
See [the deployment guide](../../docs/deployment.md) for the Vercel settings,
Render persistent-disk Blueprint, credentials, seed commands and release checks.

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
