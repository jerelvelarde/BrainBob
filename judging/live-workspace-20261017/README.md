# Live company workspace — October 17, 2026

Implementation commits:
- `348db5b377b0743770bcea2c4d1b0da99007fe24` — real Crusoe startup checks, isolated persistent runtime, and resumable source ingestion. Commit time: 15:10:09 PDT.
- `e77bb9a9792db4e3ad1aab9e13a2a7783e2170df` — scripted app removal, context-aware action cards, and independent live desk conversations. Commit time: 15:11:27 PDT.
- `489919bbbaa0e7b83d0b7844e368ac23747fa03a` — live-tested instruction fix: produce the requested draft instead of summarizing stored facts. Commit time: 15:15:54 PDT.

## Publication provenance

The implementation hashes and capture metadata above identify the original local source commits. PR #12 published their equivalents as `660c851` (company ingestion), `1352c77` (live sessions), and `33d343e` (draft instructions). The evidence files are copied from the existing local record without rerunning inference or altering screenshots. Later UI behavior and its published commit mapping are documented in the [chat-memory-panel evidence](../chat-memory-panel-20261017/README.md).

## What ran

Bonan's unmodified Python server is running on loopback port 3001, using ignored `data/workspace/` for persistent records and events. Next proxies it at `/api/brainbob`. The company input is `fixtures/company/rusty-rod.json`: 29 fictional source conversations, 18 people, and 22 scopes. The importer sends source text to `/episodes`; it does not seed answers, extracted memories, evaluation judgments, or scene events.

Crusoe access was verified with actual provider calls. The local application launcher now selects NVIDIA Nemotron Nano for extraction and Nemotron Super for answering; GPT-OSS-120B remains the judge. Early source imports used Lightning before the model change. Their original model attribution is preserved. The existing backend can cache model calls, so reruns must not be counted as fresh inference or new evaluation evidence.

One initial Lightning answer incorrectly named Maya as the Atlas sponsor while citing a record that correctly named Elena. A fresh standalone Super check and a subsequent live browser answer named Elena correctly and returned the pilot scope with matching citations. This is a development observation on one question, not a controlled model comparison or accuracy benchmark. The generated follow-up used Maya's saved style, but its prose still needs normal human review.

## Observed memory outcome

The completed import produced 71 records across all 22 scopes: 69 trial, one tentative, and one retired. The November 6 record (`m8`) was retired as superseded by the authorized November 13 record (`m64`). The Engineering estimate (`m63`) remains tentative; it was not published as the organization commitment. Unrelated records remain stored. [Recorded results](live-results.json) preserve the records and correction events.

A fresh Sales member returned November 13 and Elena's acceptance, citing `m64` and `m65`, without private Engineering records. A final suggested draft wrote a message beginning “Hi Elena” with the approved date, next checkpoint work, and a useful question. The earlier draft attempt had merely summarized facts; the follow-up instruction fix and actual resulting answer are retained as development findings.

[Repeat import verification](import-rerun.json) skipped all 29 sources and left persisted episode and memory file hashes unchanged.

## Verification

- TypeScript passed; all 36 tests in 7 files passed; production build passed.
- Suggestions use current accessible records, exclude retired and flagged records, distinguish unresolved context, and do not repeat displayed facts as authoritative model input.
- Follow-up tests exclude evaluation gold and other desk conversations. Empty provider responses fail visibly instead of producing a successful session file.
- Browser checks exercised a real answer, follow-up drafting, clickable citations, original source/model inspection, returned session files, a suggested action, and read-only retracing of actual correction event #103 followed by return to live. Mobile layout checked at 390 × 844; override restored.
- `/demo`, `/rehearsal`, and `/character-study` each resolve to `/`; their scripted agents and event generation were removed.
- [Access check results](access-checks.json): 18 member memory views and SSE replays contained only accessible memory references. Sales received 404 for an Executive source and history, and 403 for cross-team/impersonated-author writes. Run `python3 judging/live-workspace-20261017/verify-access.py` against the seeded local backend to repeat these checks.
- [Fresh Sales answer](fresh-sales-answer.json): a separate Sales member asks for the approved delivery date. The response and returned memory set are preserved verbatim.

Screenshots are from the committed frontend with the real local backend. Capture times and import state are recorded in [captures.json](captures.json). Unrelated teammates' `docs/demo/` and judging work was present in the checkout; it was not included in these implementation commits.

## Limits

The selected-member header is development identity selection, not production authentication. The access checks are bounded checks of those identities, not a complete security audit. Live-stream isolation beyond replay and fresh retirement confirmation still need separate verification.

An approved correction and a successful answer do not establish a held-out maintenance gain. Usefulness, source correctness, and coverage remain separate evaluation signals. The source dataset is development input and must not count as a held-out benchmark.

Backend answer events do not currently include per-answer model/token metadata. The configured model is recorded separately; original memory records retain their writer model. Provider 429s occurred during repeated startup probes; the running service was started with `--skip-preflight` only after independent successful model calls. No fake fallback was added.

Conversations and returned desk files remain browser-local; memory and source/event records persist server-side. No backend or benchmark source was changed by this milestone. The local key is outside the repository and expires October 18, 2026; no credential is included in this evidence.
