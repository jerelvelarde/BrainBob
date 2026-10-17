# Final readiness verification

October 17, 2026, America/Los_Angeles. Final Python regression ran after checkpoint pin commit `5bcb3bb33b7efa27c0679b9101122c8207d8fc36`.

| Check | Observed result |
| --- | --- |
| `backend/.venv/bin/python -m pytest backend/tests bobbench/tests bench/tests benchmarks/bob -q` | 471 passed in 3.26 seconds |
| `pnpm test` | 52 tests in 10 files passed |
| `pnpm typecheck` | Passed |
| `pnpm build` | Passed during integration-agent verification of the proxy change |
| `node apps/web/scripts/backend-smoke.mjs` against the temporary Python contract server | Passed after the merges and API isolation fix: real Next proxy, ingestion, ask, feedback, review, correction, history/source, lock/resolve, member filtering, SSE replay/resume |
| Frozen 60-pair rescore | Base 32/60, tuned 42/60, +16.7 points; 17 improvements, seven regressions; 0 invalid outputs |
| Saved-response maintenance replay | Five false-conflict retirements in approved/authorized/newer/unlocked context; none under lock, tentative authority, or no approval |
| GateMem data preflight | 91 episodes / 2,218 checkpoints validated; no predictions or score produced |
| Organizational Bob refusal control | Six worlds / 41 checkpoints, zero model calls; 0% legitimate / 25% macro CATS |

Frontend verification ran on the shared working tree, including concurrent three-desk work, before the final checkpoint-only Python change. No new browser screenshot or live-provider run was produced. The HTTP smoke replaces model responses with deterministic doubles and leaves no persistent application data. Temporary servers were stopped. Current backend demo identities are not authenticated user identities.

Implementation history (local commits unless already published by their owners):

- `0f92517`: configurable model roles/endpoints and endpoint/checkpoint-aware caches.
- `46114e4`, `52427de`: same-origin HTTP/SSE integration, repeatable smoke, pinned Python dependencies.
- `51058a1`: GateMem incremental prediction adapter, source validation, run manifests and external readiness report.
- `cd469fb`: Bob scorer rejects inaccessible citations/context and failed operation receipts.
- `3efd8f6`: mutation member binding and private answer/event isolation.
- `1ba3dda`: immutable run-directory guard **and** custom-judge provenance plus saved-response maintenance replay. A shared-index commit race included both agents' related evaluation changes under the guard-oriented commit title; history was preserved, and this entry records its actual contents.
- `76b1bf2`, `dece5dd`: real BrainBob component adapter and opt-in local judge callback.
- `5bcb3bb`: canonical private adapter revision passed to PEFT and preserved in provenance; six offline pinning tests.
- `cb3e297`: readiness scorecard, independent rescore, and refusal-control evidence.

The remote and benchmark branches were merged in `af77dc0` and `0b678d9`, preserving Bonan's model work, the existing organizational pilot, the frozen pair scorer, and both proof-of-work histories. Teammates' unrelated changes were preserved. This assessment did not push, deploy, start GPU jobs, activate the tuned model in production, or submit benchmark scores.

Remaining gates are in [readiness.md](../../docs/readiness.md). MUM means MUMBench. Private weights were not downloaded here; the canonical identity was confirmed by Bonan via Jerel and matches committed run metadata.
