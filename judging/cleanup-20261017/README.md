# Judging package cleanup

October 17, 2026. Documentation and repository triage only; no new application behavior, inference, training, deployment, benchmark measurement or submission.

- Rebuilt the [judging guide](../README.md) around the narrated live video, corrected scorecard, original team contributions and evidence boundaries.
- Added an [artifact index](../artifacts.md), updated the [presenter runbook](../demo-runbook.md), linked the completed video in the [evidence sheet](../evidence.md), and separated the [remaining submission gates](../submission-status.md).
- Preserved historical artifact paths, screenshots, raw results, commit history and original issue plans. Marked the Remotion package as historical presentation source; no evidence was deleted or regenerated.
- Reconciled issues #1–#8; closed five delivered work items and the separately scoped in-app scorecard as not planned. Retained final submission #5 and optional sandbox verification #8. Closed redundant diagram PR #11; retained deployment PR #14 as draft.

## Verification

- [GitHub disposition](github-disposition.json): actual update timestamps, states, reasons and URLs returned by GitHub.
- [Public-link checks](public-links.json): unauthenticated HTTP HEAD returned 200 for the repository, committed narrated MP4, corrected scorecard and public benchmark dataset. This checks reachability, not video playback or submission-form acceptance.
- [Local validation](validation.json): judging Markdown links, proof-of-work anchors and embedded-image preservation checked against the recorded base; whitespace checked with `git diff --check`.

The original shared checkout had active teammate edits and diverged from published main. All cleanup work used a separate checkout based on current published main; unrelated files and the original shared index were untouched. Historical tests/results remain tied to their original builds; this documentation-only change did not rerun the application test suites.
