# Submission status — October 17, 2026

[Judge's guide](README.md) · [Evidence](evidence.md) · [Final submission issue #5](https://github.com/jerelvelarde/BrainBob/issues/5)

**The review package is prepared; final submission is not confirmed.** A documentation cleanup, closed issue, or merged feature is not a submission receipt.

## Ready to review

| Item | Status / destination |
| --- | --- |
| Repository | [Public BrainBob repository](https://github.com/jerelvelarde/BrainBob); anonymous HTTP check passed |
| Team / track | Jerel Velarde and Bonan Kou · Shared Brain |
| Featured extended video | [V2 — 2:50](https://github.com/user-attachments/assets/e75a7bcc-b46e-4c95-9e15-6edac63a0b38); [repository fallback and provenance](../docs/demo/v2-agent-chat-20261017/README.md). Covers the app, benchmark and fine-tuned checker; submission-form acceptance remains unverified |
| One-minute option | [V1 — 60 seconds](../docs/demo/live-one-minute-20261017/README.md); its anonymous file URL previously returned HTTP 200. V2 does not meet a one-minute duration limit |
| Main result | [Corrected v0.3 scorecard](../bobbench/results/20261017-141014/scorecard.v0.3.md), public and linked with uncertainty and historical scores |
| Demo provenance | [V2 recording](../docs/demo/v2-agent-chat-20261017/README.md) and [company workspace](live-workspace-20261017/README.md); fictional inputs and development-build limits disclosed |
| Presenter materials | [Three-minute runbook and Q&A](demo-runbook.md), with recorded fallback |
| Work history | [Commit-linked timeline](proof-of-work/index.html) and [artifact index](artifacts.md) |

## Remaining submission gates

- [ ] **Public hosted app:** record its URL and verify actual inference, streaming, access configuration and persistent memory. [Draft PR #14](https://github.com/jerelvelarde/BrainBob/pull/14) contains deployment preparation; container and hosted release checks remain pending.
- [ ] **Final video destination:** verify the chosen link plays in the submission workflow. Use V2 for the extended presentation, or V1 for a required 60-second upload. This update did not submit either video or test a submission form.
- [ ] **Exact submitted commit and receipt:** record the SHA actually submitted, destination, both teammates, and confirmation/link. No final submission is inferred from the latest Git commit.
- [ ] **Rehearsal:** complete the three-minute story and Q&A once with the recorded fallback.

No hosting resources were provisioned and no inference, training, or new benchmark run was started during this cleanup.

## Issue and PR disposition

This table is a snapshot; GitHub is authoritative for subsequent changes. Original task plans are retained in expandable sections on the issues.

| Work | Disposition |
| --- | --- |
| [#1 Live demo](https://github.com/jerelvelarde/BrainBob/issues/1) | Closed: recorded real-provider development evidence; hosted-release gate stays in #5 |
| [#2 Scoped audit/demo](https://github.com/jerelvelarde/BrainBob/issues/2) | Closed: implementation, repeatable demo and bounded access evidence delivered |
| [#3 In-app scorecard](https://github.com/jerelvelarde/BrainBob/issues/3) | Closed as not planned: separate in-app scorecard not delivered; repository scorecard/presentation consolidated into #5 |
| [#4 Organizational pilot](https://github.com/jerelvelarde/BrainBob/issues/4) | Closed: real-model pilot, corrected scores, traces and limitations published |
| [#5 Submission](https://github.com/jerelvelarde/BrainBob/issues/5) | Open: the remaining release/submission checklist above |
| [#6 Checker safeguards](https://github.com/jerelvelarde/BrainBob/issues/6) | Closed: opt-in confirmation/observe wrappers and controlled replay delivered; no live-provider safety claim |
| [#7 Small-checker experiment](https://github.com/jerelvelarde/BrainBob/issues/7) | Closed: experiment completed; production promotion failed, model stays opt-in |
| [#8 NemoClaw sandbox](https://github.com/jerelvelarde/BrainBob/issues/8) | Open, P2 optional: adapter merged, actual sandbox handoff unverified |
| [PR #11 Diagram](https://github.com/jerelvelarde/BrainBob/pull/11) | Closed as superseded: current main README already includes the diagram |
| [PR #14 Deployment](https://github.com/jerelvelarde/BrainBob/pull/14) | Draft retained with explicit container/hosted-release checks; useful unmerged work preserved |
| PRs [#9](https://github.com/jerelvelarde/BrainBob/pull/9), [#10](https://github.com/jerelvelarde/BrainBob/pull/10), [#12](https://github.com/jerelvelarde/BrainBob/pull/12), [#13](https://github.com/jerelvelarde/BrainBob/pull/13), [#15](https://github.com/jerelvelarde/BrainBob/pull/15) | Already merged; historical descriptions and implementation history preserved |

[Cleanup verification and recorded GitHub changes](cleanup-20261017/README.md). Closing the experiment issues does not convert missing measurements into successes or authorize deploying the experimental checker.
