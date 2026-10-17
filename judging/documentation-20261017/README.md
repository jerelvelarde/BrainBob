# Published solution and results documentation

Documentation commit: [`eaf5dd2`](https://github.com/jerelvelarde/BrainBob/commit/eaf5dd233e429232e3779b764db44a137da1ec49); commit time **4:17:20 PM PDT**, October 17, 2026 (`2026-10-17T16:17:20-07:00`). NemoClaw attribution correction: [`cf9d0aa`](https://github.com/jerelvelarde/BrainBob/commit/cf9d0aa64323d666d9e37961efb79b008f39ddd8). Codex prepared these documentation changes for Jerel on main after PRs #12 and #13, preserving their implementation and evidence history.

The README now showcases the shared-memory solution, Bonan's diagram, the corrected v0.3 pilot (71.9% maintained vs 25.0% no memory), supporting experiments, live workspace, and current setup. The optional NemoClaw/OpenClaw adapter is implemented; sandbox integration and end-to-end validation remain pending. The production app continues to use the direct Python/Crusoe path. The original architecture proposal remains archived.

The earlier adapter attribution incorrectly pointed to `5e92439`, which only fixed the requirements encoding. Both the alignment record and changelog now identify `740beb8` as the implementation and retain the requirements fix separately with an explicit correction note.

## Verification and scope

[Checks](checks.json): **151 local documentation links/anchors** plus **6 live-evidence links** resolve; the six pilot headline scores and two intervals match saved v0.3 JSON; diagram/scorecard bytes match the published source; original live screenshots and result files remain unchanged. Scoped `git diff --check` passed. The original diagram was visually inspected in the earlier local documentation pass; no new browser render, inference, or benchmark run is claimed.

The previously recorded live-workspace evidence is now included so public README links resolve. Its original capture hashes/times remain intact, and the record identifies the equivalent published implementation from PR #12. No application/backend runtime code, inference configuration, or in-progress teammate work is included. The existing access-verification script is supporting evidence and was not executed against a live backend during this publication.
