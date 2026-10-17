# Publish the full BrainBob demo

Deployment follow-up to PR #12: **Next.js on Vercel + the complete Python API on one Render web service with a persistent disk**. Extraction, maintenance, chat, judgment, scoped memory, source history and SSE all run in the backend. Crusoe still serves inference; no GPU is needed on Render. No database migration is required for this small shared demo.

This is a password-protected demonstration using fictional personas. Anyone with the shared password can select any demo member. It is not individual authentication or a production multi-tenant service. Do not import private company data.

## 1. Create the backend when ready to incur hosting charges

Import this repository as a Render Blueprint, selecting `codex/vercel-deployment`. Review `render.yaml`: it provisions a **paid Starter service and 1 GB persistent disk**, in Oregon, with one instance and automatic deployment disabled. Confirm current prices in Render before creating it. After merging, change the service branch to `main`.

Set these secrets in Render, never in Git or chat:

- `BRAINBOB_API_KEY`: Crusoe API key with credit and access to the configured models.
- `BRAINBOB_DEMO_PASSWORD`: a strong random ASCII password, at least 16 characters. Use the identical value on Vercel. Login username is `brainbob`.

The Docker image configures `HOST=0.0.0.0`, `PORT=10000`, required authentication, `/var/data/workspace` for memory/episodes/events, `/var/data/cache` for inference cache, and 240-second SSE sessions. The app respects the platform's `PORT`. Keep **one instance and one worker**: the current store and event bus are process-local. A disk-backed restart preserves committed memory, episodes and event sequence; in-flight requests and transient feedback tasks do not survive it. Disk-backed deploys can briefly interrupt service.

The public `/healthz` endpoint returns only process readiness, with no model call or private state. Other API endpoints, including docs and SSE, require the password. Startup fails if hosted credentials are absent. The container skips inference preflight for fast startup; health alone does **not** prove provider access.

Once running, use the Render shell to verify models and seed the persistent workspace:

```sh
python scripts/run-live-backend.py --check
python scripts/seed-company.py --base http://127.0.0.1:10000 --receipt /var/data/workspace/company-import.json
```

These commands inherit the configured secrets. The seed makes real, billable inference calls. It imports 29 fictional conversations through the API and checks receipts on reruns. Do not run it in a build or pre-deploy step: the persistent disk is available only at runtime. Keep the resulting API HTTPS origin for the next step.

The same Dockerfile works on another container host with a volume at `/var/data`, the same variables, and one instance. Render is the prepared path, not a backend dependency.

## 2. Create the Vercel frontend project

Import the repository and configure:

| Setting | Value |
| --- | --- |
| Root Directory | `apps/web` |
| Framework | Next.js |
| Node.js | 22.x |
| Package manager | pnpm 10.32.1 (root `packageManager`) |
| Install | `pnpm install --frozen-lockfile` |
| Build | `pnpm build` |
| Output | Next.js default |
| Include source files outside Root Directory | Enabled for the workspace/lockfile |

For the PR preview, deploy branch `codex/vercel-deployment`. Keep the normal production branch `main`; publish production after the PR is merged and the preview checks pass.

Set these **server-only** variables in the intended Preview/Production environments:

| Variable | Value |
| --- | --- |
| `BRAINBOB_API_URL` | Backend HTTPS origin, e.g. `https://brainbob-api-xxxx.onrender.com`, with no path/query/credentials |
| `BRAINBOB_DEMO_PASSWORD` | Same password as Render |

Leave `NEXT_PUBLIC_BRAINBOB_API_URL` **unset**. Do not give Vercel the Crusoe key. The browser talks only to `/api/brainbob` on its UI origin, so backend CORS changes are unnecessary. Vercel deployments fail closed with 503 if the demo password is missing/short; the API route also rejects absent or non-HTTPS backend configuration. Runtime environment changes still require a redeployment on Vercel.

Open the preview and enter username `brainbob` and the demo password. The shared gate protects the UI and API independently; the backend also checks credentials when reached directly. Credentials are carried over HTTPS. Cross-origin browser writes are rejected, and proxied responses are never cached.

## 3. Verify before sharing

- `/healthz` on the backend returns 200; unauthenticated `/memories`, `/events`, and `/docs` return 401.
- Opening the Vercel URL prompts for the password. Bad credentials cannot reach UI data or API routes.
- Ask a real question, open its cited memory/source/history, and exercise a correction in a synthetic scope.
- Leave the UI open past four minutes: SSE reconnects and resumes from its last event sequence without duplicate animation.
- Restart the backend and confirm memory, source history, and retrace still load. An in-flight request can be interrupted; inspect state before repeating a mutation.
- Test another fictional member's scope. This verifies selected-persona permissions, not user authentication.

Run the read-only hosting check with `UI_URL`, `BRAINBOB_API_URL`, and
`BRAINBOB_DEMO_PASSWORD` already set in the shell:

```sh
node apps/web/scripts/deployment-smoke.mjs
```

For a local fixture with a short SSE lifetime, set `EXPECT_STREAM_CLOSE_SECONDS`
to that lifetime to also verify stream expiry and reconnection. This check expects
the app's Basic login challenge; if Vercel Deployment Protection is also enabled,
use an approved bypass mechanism or test manually through its login first.

For repeatable integration testing, use a temporary backend and the existing `apps/web/scripts/backend-smoke.mjs`. It writes test memories, so use it only against a disposable workspace. It supports `UI_URL` and `BRAINBOB_DEMO_PASSWORD` from the environment. This test substitutes deterministic model functions and does not establish inference quality.

## Timeouts and current limits

The previous external Next rewrite is replaced by a Node Route Handler. Vercel external rewrites have a 120-second proxy limit; a local `experimental.proxyTimeout` cannot change that. The route uses `maxDuration=300` and an upstream deadline of 280 seconds, compatible with the current Fluid Compute Hobby maximum. SSE closes at 240 seconds and the existing client reconnects after three seconds. Test this on the actual preview before sharing; local tests do not prove hosted platform behavior.

If inference exceeds the deadline, the UI receives an error, with **no automatic mutation retry**. The synchronous backend operation may still finish after disconnection. Inspect its result before retrying. Sustained long-running work needs asynchronous jobs, and horizontal scaling needs shared transactional storage/event delivery; neither is part of this deployment preparation.

The backend image contains runtime code and the fictional seed sources, not local data, cache, credentials, benchmark output or the developer virtual environment. Back up the persistent disk before destructive data operations. Do not reset it as part of deploy.

Sources: [Render disks](https://render.com/docs/disks), [Blueprint reference](https://render.com/docs/blueprint-spec), [Vercel proxy limits](https://vercel.com/docs/limits#proxied-request-timeout), [function limits](https://vercel.com/docs/functions/limitations).
