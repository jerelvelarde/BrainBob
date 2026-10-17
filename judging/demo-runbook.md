# BrainBob — three-minute judging runbook

**Team:** Jerel Velarde and Bonan Kou. **Track:** Shared Brain.

Use the [judge's guide](README.md) as the starting page. The fallback is the [finished narrated live recording](../docs/demo/live-one-minute-20261017/output/brainbob-live-60s-vo.mp4), with its [exact script and provenance](../docs/demo/live-one-minute-20261017/SCRIPT.md).

## Before presenting

- Open the video, [corrected scorecard](../bobbench/results/20261017-141014/scorecard.v0.3.md), and [evidence sheet](evidence.md) in advance.
- For a live walkthrough, follow [local setup](../docs/live-workspace.md) and confirm the actual provider connection. Use fictional data in an isolated store; do not reset a teammate's workspace.
- Check the selected person's current memory before choosing a correction. The recorded fixture already contains the approved November 13 Atlas date.
- Confirm the build being shown and distinguish it from each historical evaluation build. Final submission fields remain in [submission status](submission-status.md).

## Presentation sequence

| Time | Show or say | Evidence |
| --- | --- | --- |
| 0:00–0:20 | “One stale fact can spread across an agent team. BrainBob checks shared memory and lets the next agent inspect the current source.” Introduce both teammates. | [Solution and architecture](../README.md#the-solution) |
| 0:20–1:20 | Play the narrated live recording. It follows Maya through scoped retrieval, a source citation, a personal-preference correction, and a fresh session. Introduce it as recorded live footage. | [60-second video](../docs/demo/live-one-minute-20261017/output/brainbob-live-60s-vo.mp4) |
| 1:20–1:50 | Open the source/history evidence. Explain that authorized corrections supersede older facts, private tentative estimates do not become public commitments, and retirement preserves history. | [Workspace outcome and access checks](live-workspace-20261017/README.md) |
| 1:50–2:25 | “On six synthetic worlds, maintained memory scored 71.9% versus 25.0% without memory. Against append-only, the difference is inconclusive; full authorized history scored 92.0%.” | [Corrected v0.3 scorecard](../bobbench/results/20261017-141014/scorecard.v0.3.md) |
| 2:25–2:45 | Explain the team’s app/backend and evaluation contributions. The optional 0.6B checker improved 32/60 to 42/60 but made five false conflicts; the default judge is unchanged. | [Model handoff](../docs/finetune-handoff.md), [proof of work](proof-of-work/index.html) |
| 2:45–3:00 | Close with inspectable shared knowledge and the repository. State current hosting/harness limits if asked; do not claim a completed public deployment or submission without its receipt. | [Submission status](submission-status.md) |

## Optional live walkthrough

Select Maya and start a fresh session. Ask for the approved Atlas delivery date and approver; inspect the returned citation. Open an accessible individual preference, save a clearly described manual correction, inspect its supersession history, then start another session and ask for that preference. This follows the recorded story without pretending the manual edit is an automatic audit verdict. Use actual returned IDs and wording.

For the separate approved organization correction and denied-read story, use the [recorded company-workspace evidence](live-workspace-20261017/README.md). For a repeatable usefulness-evaluator scenario, use the [backend audit demo](../backend/demo/DEMO.md), whose synthetic seeded history and real inference are labeled separately.

If inference fails, say so and switch to the verified recording. Replay must not be described as a new successful live run.

## Q&A reference

| Question | Answer boundary |
| --- | --- |
| Does maintenance beat append-only answers? | Not established: +4.0 macro CATS points, 95% interval −9.0 to 18.2. Correct state updates improved in the separate Rusty Rod suite. |
| Does the audit improve accuracy? | No measured gain in the frozen BANKING77 comparison or the cited LoCoMo comparison. Correctness and usefulness are separate checks. |
| Is the 0.6B checker the production model? | No. It is experimental and opt-in; confirmation/observe checks use saved responses and do not establish live-provider safety. |
| Is access control production authentication? | No. Current member selection is a development identity mechanism. Pilot disclosure counts cover only recorded surfaces and strings. |
| Which integrations ran? | Direct Crusoe inference and the Next/FastAPI app. NemoClaw's adapter is merged, but a sandbox run is pending. Switchyard and SQL are not integrated. |
| Is the context reduction a total cost saving? | No. The modified LongMemEval subset measured answer-context reduction with lower accuracy; total maintenance cost is a separate question. |
