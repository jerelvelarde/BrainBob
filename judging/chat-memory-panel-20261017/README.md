# Live chat memory panel — October 17, 2026

Implemented for Jerel. The chat keeps its conversation alongside one live 3D scene, an accessible cabinet file browser, and source/history inspection. One operator handles memory actions; three session Bobs stay seated. The evaluator enters, checks, and exits quietly.

## Published implementation commits

| Commit | Change | Author time (PDT) |
| --- | --- | --- |
| [820b12d](https://github.com/jerelvelarde/BrainBob/commit/820b12d4f34cde26a595893d3ed0c9851cee85d7) | Live side panel, context-file delivery, cabinet browsing | 15:51:51 |
| [032d087](https://github.com/jerelvelarde/BrainBob/commit/032d0878a529e033893964fbf38a3298fdd49caa) | One idle operator, seated sessions | 15:55:21 |
| [c9004ae](https://github.com/jerelvelarde/BrainBob/commit/c9004ae0aa02beedb9efbc397b8a907a7d3aa842) | Quiet evaluator entry/check/exit | 15:57:12 |
| [b4daf18](https://github.com/jerelvelarde/BrainBob/commit/b4daf18393b94292fa3eabf95e26c2746d3042a6) | Accessible folders and breadcrumbs | 16:04:31 |
| [bc7fc35](https://github.com/jerelvelarde/BrainBob/commit/bc7fc35eeca827fde08b0d9d96d3f4559c311e40) | Native Escape dismissal | 16:05:24 |

## Verification

- Final isolated draft branch: 40 tests in 8 files pass; Next.js webpack production build and its TypeScript check pass. The branch merges latest main through 373eee2; that merge changes benchmark/report files, not this frontend.
- Browser used the running localhost app, local Python backend, and synthetic Rusty Rod data. Real inference had already ingested the company records and answered chat requests. This is functional integration evidence, not a correctness benchmark.
- Clicked a 3D cabinet; browsed Team → Sales → files; opened all two Leo individual records; inaccessible Executive/Engineering folders were absent. Opened source/history inspection. Verified desktop and narrow mobile layouts and Escape returning from the mobile panel to chat.
- Switched Maya → Leo and started a fresh Leo session. The actual authorized context load triggered file delivery. That animation is presentation-only, not a fabricated persisted retrieval event or a new inference call.
- Created disposable QA memory m72 via /episodes (episode ep-57a23e8a, Nemotron Nano extraction attribution in the event). Corrected it via the UI to m73, then retired m73. Original m72 was superseded. The saved event excerpt proves both records are now retired; history remains intact. Update and retirement choreography ran from real events.
- Quiet evaluator entry/check/exit and neutral cinematics are covered by deterministic animation tests. No live evaluator call was made in these browser checks.

## Screenshot provenance

PNG bytes are unmodified browser captures. Each JSON sidecar records its capture time, local source commit and equivalent cherry-picked draft commit. Captures came from the shared development checkout, where unrelated teammate documentation and generated Next type paths were also present. They are not screenshots of a deployed production build.

Current views:
- `team-files-desktop.png`: six Sales files and breadcrumbs beside chat.
- `accessible-teams-desktop.png`: only the active reader’s Sales folder.
- `accessible-files-mobile.png`: current person’s individual files, mobile layout.
- `retirement-live.png`: real m73 retirement animation in progress. Fire/shredding represents retirement, not hard deletion or confirmed evaluator judgment.
- `new-session-file.png`: real fresh-session context load, with file-delivery animation in progress.

Retained iterations:
- `cabinet-browser.png` shows the older locked-folder layout and extra idle workers, superseded by the current design.
- `mobile-panel.png` predates breadcrumbs; `individual-mobile.png` predates the Escape-handler refinement.
- `new-person-session.png` is after context was ready; `new-session-start.png` is the connection/loading phase.
- `correction.png` is after the rewrite animation completed. It shows the corrected record, not animation in progress.

See [live-operation-events.json](live-operation-events.json) for the synthetic operation trace and [verification.json](verification.json) for the final check summary.
