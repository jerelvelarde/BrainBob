# Chat experience iteration — October 17, 2026

Unmodified screenshots from the local app connected to the Python backend, using fictional Rusty Rod company data. JSON sidecars preserve original capture times and local commit references. These precede the [live side panel](../chat-memory-panel-20261017/README.md).

- `welcome-desktop.png` and `welcome-mobile.png`: personal welcome and action-oriented suggestions.
- `working-desktop.png`: expandable elapsed-time activity while a real request ran.
- `sources-desktop.png`: completed answer, retrieval receipt and inline memory sources.
- `retrieval-desktop.png`: earlier capture with the activity header partly clipped.
- `memory-mobile.png`: source/session-file inspection on mobile.

The local UI commit 8f2f986 corresponds to published draft commit [0a7844d](https://github.com/jerelvelarde/BrainBob/commit/0a7844d). The local proxy fix 09c2c0f corresponds to [69d0885](https://github.com/jerelvelarde/BrainBob/commit/69d0885), and the mobile fix 60c10bf corresponds to [4433bc7](https://github.com/jerelvelarde/BrainBob/commit/4433bc7). Cherry-picking isolated this work from unrelated shared-checkout changes; original capture metadata is retained.

At this stage TypeScript, 37 frontend tests and the production build passed. A 32-second local proxy fixture verified the extended inference timeout. Real backend chat requests and source/history inspection were exercised. These are functional checks and visual evidence, not a measured memory-correctness improvement. Final validation for the side-panel version is recorded in the linked milestone.
