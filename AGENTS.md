# BrainBob Agent Instructions

This repository is shared by teammates and their agents. Preserve work you did not create and keep edits scoped to the active request.

## Atomic Commits Are Proof of Work

This is a hackathon: the Git history must make the day's progress independently reviewable. Commit each coherent feature, fix, or documentation change separately rather than collecting unrelated work into an end-of-day commit. Include the supporting tests and configuration needed for that change to work.

- Stage explicit files or hunks and inspect the staged diff before committing. The shared Git index may contain a teammate's work; do not include or unstage their changes without coordination.
- Keep each commit focused, with a message describing the resulting behavior. Separate unrelated refactors, styling changes, and infrastructure work.
- Preserve published milestone commits. Do not amend, squash, rebase, or rewrite shared proof-of-work history merely to tidy it; record corrections in follow-up commits.
- Link changelog entries to the actual implementation commits. Record evidence after those commits exist, using a separate documentation commit when the entry needs their SHAs. Never guess a commit hash or imply that an uncommitted screenshot is a verified committed build.
- Follow the active request's publishing scope; atomic local commits do not imply permission to push unrelated work.

After a meaningful completed project milestone, add its proof of work to `judging/proof-of-work/index.html`. Follow [the changelog maintenance instructions](judging/proof-of-work/agent.md) before editing that file. Keep incomplete work clearly labeled; do not invent screenshots, timestamps, commits, or results.

Follow any additional `AGENTS.md` instructions in the directories you work in.
