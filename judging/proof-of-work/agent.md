# Maintaining BrainBob's Proof-of-Work Changelog

## Purpose

Two teammates and their agents are building BrainBob. Keep a shared, judge-readable record of the platform's evolution during the day.

The record is [index.html](index.html): a minimal black-and-white changelog with newest entries first, expandable visual evidence, and a sticky side timeline. It is one self-contained HTML file that opens offline.

## When to Add an Entry

Add an entry after a meaningful completed milestone, such as a new interface, a working integration, a memory-management capability, or measured evaluation results. Routine edits can be grouped into one milestone. Do not turn every small code change into an entry.

Describe unfinished integrations as planned or in progress. Distinguish live execution, scripted previews, fixtures, and recorded replay. Screenshots show appearance; they do not by themselves prove model inference, persistence, evaluation accuracy, or a working integration.

## Required Evidence

Each new entry should include:

- A short title and concise bullets explaining what changed.
- The actual milestone time, displayed in `America/Los_Angeles`, with an ISO timestamp including the correct UTC offset in `<time datetime="...">`.
- The contributor's name when known. Do not guess who created work from unrelated Git configuration.
- A real commit link when a commit exists. For uncommitted work, say so; do not attach an unrelated commit or invent a SHA.
- A screenshot for a visual change, or an appropriate run/test/result artifact for nonvisual work.
- A brief status note describing what is connected and any relevant limitation.

Use Git author timestamps when documenting a commit, labeled as commit times. Label screenshot capture, attachment receipt, and reconstructed-document render times separately. Do not use a file's modification time as proof of its original capture time or assume an image exactly matches a commit.

## Atomic Commit Workflow

Git commits are the primary proof of how the project evolved. Keep one coherent intent per commit: a feature, a fix, or a documentation change, together with the tests and configuration necessary for that intent. Avoid bundling unrelated work into one large checkpoint.

1. Finish and verify the scoped implementation change.
2. Inspect the working tree and shared staging area. Stage only the files or hunks belonging to this change, preserving teammates' work.
3. Commit with a concrete message, such as `feat(memory): persist evidence-linked revisions` or `fix(memory): reject stale revision updates`.
4. Read the resulting SHA and timestamp from Git; capture evidence from that committed build where practical. Disclose any local modifications present when capturing a screenshot.
5. Add the changelog entry referencing that implementation commit. Commit the proof-of-work update separately, for example `docs(judging): record memory revision milestone`.

The evidence commit points to an existing implementation commit; it does not need to contain its own hash. This avoids inventing a self-reference or repeatedly amending the evidence commit.

One readable milestone entry can cover several related atomic commits, but list each relevant commit and explain its contribution. Keep commit granularity separate from presentation granularity: judges can scan milestones while inspecting the individual changes underneath.

Preserve published milestone SHAs and real timestamps. Add follow-up commits for corrections instead of rewriting shared history for presentation. Push only within the active request's authorized scope.

## Editing the Changelog

1. Re-read the current file immediately before editing so a teammate's latest additions are included.
2. Add the new `<article class="entry">` at the top of `.log-entries`, after the date heading, preserving older entries. “Append” means add to the historical record; the page displays newest first.
3. Give the entry a unique descriptive ID, preferably including date/time and a short milestone name. Avoid renumbering existing entries or relying on a shared incrementing counter.
4. Add a matching timestamp/title link to `.timeline-nav` in the same order. The active-section script derives its sections from those links; every anchor must resolve.
5. Put screenshots or larger evidence inside native `<details>` sections so the default view remains easy to scan.
6. Preserve existing screenshots, timestamps, commit links, and provenance notes. Correct a factual mistake transparently rather than silently changing the record.

Follow the existing entry structure:

```html
<article class="entry" id="unique-milestone-id">
  <div class="time">
    <time datetime="ACTUAL_ISO_TIMESTAMP_WITH_OFFSET">LOCAL_TIME</time>
    <span>Commit time or another accurately labeled time source</span>
  </div>
  <div>
    <h2>Short milestone title</h2>
    <ul>
      <li><span class="label">Added</span> a concrete completed capability.</li>
    </ul>
    <p class="note">Contributor, execution mode, and relevant implementation limits.</p>
    <!-- Add a real commit/artifact link and expandable evidence when available. -->
  </div>
</article>
```

The values above are placeholders for authoring, not evidence. Replace them before saving a new entry.

## Screenshots and Artifacts

- Embed screenshot bytes using a `data:image/...;base64,...` URL so the HTML remains portable. Use meaningful alt text and accurate dimensions.
- Preserve the original screenshot content. Restyling the page must not alter evidence images.
- Caption what the image proves and identify its source or capture time when known.
- A README reconstructed from a historical commit must be labeled as a reconstruction, not a contemporaneous screenshot.
- Link actual benchmark artifacts and report sample sizes and observed results. Internal targets are not achieved scores.
- Keep secrets and unauthorized private conversation content out of this public judging record.

## Team Collaboration

- Edit only the new entry, its navigation link, and necessary supporting markup. Avoid whole-file reformatting, especially embedded image data.
- Preserve a teammate's unrelated uncommitted work. Never reset, discard, or overwrite it to update the changelog.
- If both teammates add entries, retain both with unique IDs, accurate ordering, and working navigation.
- Do not resolve contradictory evidence by guessing; keep the uncertainty explicit.
- Follow the current user's authorized commit/push scope. Maintaining the log alone does not require publishing unrelated changes.

## Verify Before Finishing

- Confirm new timestamps and commit references against their sources.
- Check that every timeline link targets an existing unique ID.
- Verify local links and embedded images remain intact.
- Check expandable evidence and active-section navigation when browser preview is available; preserve mobile and reduced-motion behavior.
- Run `git diff --check` and inspect the scoped diff for accidental changes to previous entries or unrelated files.
- Report what was added and whether it is local or pushed. Do not claim browser verification or a successful integration without evidence.
