# Live company workspace

BrainBob now has one application workspace at `/`. The former `/demo`, `/rehearsal`, and `/character-study` routes redirect there. Scripted chat agents, generated fixture events, and the staged correctness walkthrough have been removed from the app. Historical screenshots and judging evidence remain in Git.

## Start

Use the existing Python environment in `backend/.venv` (see `backend/FRONTEND.md` for installation). Keep the Crusoe inference key at `~/.config/crusoe/api.key`, with file mode `0600`, or supply `BRAINBOB_API_KEY` in the backend process environment. A signed-in console browser is not an API credential. Keys never go in Next public environment variables or source control.

From the repository root, in separate terminals:

```sh
pnpm backend
pnpm seed:company
pnpm dev
```

`pnpm backend` verifies the configured model endpoints using real provider requests before starting the backend server on port 3001. It stores the running company's JSONL data in ignored `data/workspace/`, separately from benchmark runs. `backend/.venv/bin/python scripts/run-live-backend.py --check` performs only the provider checks. The application launcher defaults to NVIDIA Nemotron Nano for extraction, NVIDIA Nemotron Super for chat, and GPT-OSS-120B for judging. The backend's model environment overrides remain available; benchmark defaults are unchanged.

Next proxies `/api/brainbob` to `http://127.0.0.1:3001`. Set server-side `BRAINBOB_API_URL` to use another backend. See [deployment instructions](deployment.md) for Vercel, the persistent backend and demo access protection. There is no fallback answer or synthetic event generator if inference fails.

## Source data

[`fixtures/company/rusty-rod.json`](../fixtures/company/rusty-rod.json) contains 29 explicitly fictional source conversations: 18 individual working notes, 3 team plans, and company/client decisions and follow-ups. They cover all 22 Rusty Rod permission scopes. Atlas Harbor is a fictional client; its relationship does not grant access to its private records.

The data includes an initial November 6 commitment, a tentative Engineering estimate, and an authorized November 13 correction. These are input sources, not precomputed maintenance outcomes or gold answers. The actual curator and judge decide what to retain, reject, flag as tentative, or supersede.

The importer posts each conversation to `/episodes` with its actual member, scope, source, date, and authority. It records the returned decisions in ignored `data/workspace/company-import.json`. Repeated runs check persisted event receipts and source contents, then skip already imported sources. It never resets existing memory. Changed sources require a new source version; missing or failed extraction is reported rather than silently filled in.

Validate without model calls:

```sh
backend/.venv/bin/python scripts/seed-company.py --validate
```

## Work with the brain

Each desk has its own person, chat, draft, and returned memory file. Open a desk or use the account switcher. Suggested actions use only that person's accessible, current records; they offer drafting, preparation, and clarification without exposing memory-tier labels. They are deterministic suggestions, not model-generated claims. The backend retrieves current evidence again when the action is submitted.

Ask generates a real answer through Crusoe. Follow-up requests include up to four successful Ask turns from that desk. Feedback gold, remember commands, review receipts, and other desks' conversations are excluded from that answering context. Conversation turns themselves remain browser-local and clear on reload; the memory store and event log persist on the server.

Remember submits a source conversation. Usefulness and Review call the existing evidence evaluator. Source inspection, corrections, locks, and retirement use the backend APIs. Only actual live events animate; replayed history hydrates state first. Retrace reconstructs stored event history without making model calls or changing memory.

The member header is a local development identity selector, not production authentication. Server scope checks still protect reads, sources, histories, writes, and event streams between those selected identities. Do not expose this local server publicly without real authentication.
