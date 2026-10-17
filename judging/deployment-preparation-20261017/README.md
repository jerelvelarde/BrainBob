# Vercel + persistent backend deployment preparation

Implementation commits:

- `b794d9436de1a01fab0068489d27a9dcebffab42` — backend Docker/Render configuration, persistent paths, shared demo gate, health check, finite SSE sessions, authenticated seed requests.
- `66e93a7f8fcbad2c502272dec7ff096ef2222209` — Vercel streaming Route Handler, independent UI/API gate, deployment checks, settings and runbook.

Frontend commit time: 2026-10-17T16:08:30-07:00 (America/Los_Angeles). These results were captured locally during preparation immediately before committing those implementation files. They are not a hosted deployment or model-quality evaluation.

## Recorded validation

- Backend: `python -m pytest backend/tests -q` — **291 passed**.
- Frontend: `pnpm test` — **8 test files, 43 tests passed**.
- `pnpm build` — successful compilation, TypeScript check and page generation; dynamic `/api/brainbob/[...path]` and Proxy included.
- Authenticated `backend-smoke.mjs` through production Next on port 3200 to temporary Python on port 3101 — passed ingestion, ask, feedback, review, correction/history, sources, lock/resolve, member filtering and SSE replay/resume.
- `deployment-smoke.mjs` against the same servers — passed UI/API authentication, direct-backend protection, cross-origin write rejection, immediate SSE delivery and reconnect/resume. The fixture used a five-second SSE lifetime to exercise expiry quickly; hosted configuration uses 240 seconds.
- Tests use isolated temporary data and deterministic model doubles; no provider calls or accuracy claims.

## Integration with the latest PR work

Merged the incoming PR head `75d3816618f53f1bb6ffdc1d142890b5c61bbb7f` without rewriting either history. Both proof-of-work entries and all existing screenshot evidence were retained. The combined frontend passed **9 files / 46 tests** and the production Turbopack build with TypeScript. Backend implementation did not change during the merge; its 291-test result above remains applicable.

## Limits

Docker daemon was unavailable, so the image was not built or run. No Render service or Vercel deployment was created. Remote build, real inference, hosted streaming, provider credentials and persistent-disk restart verification remain release checks. The shared password authorizes access to fictional personas; it is not individual user authentication. Render Blueprint provisioning requires paid hosting and disk.

See [deployment instructions](../../docs/deployment.md).
