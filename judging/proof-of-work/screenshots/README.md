# UI and character iteration screenshots

All entries are from October 17, 2026. Times below use America/Los_Angeles (PDT).
The changelog embeds these images so it still opens as one offline HTML file.

| Image | Evidence type | Provenance |
| --- | --- | --- |
| [Floating workspace](01-floating-workspace.jpg) | Historical screenshot | Recovered unchanged from commit fccd1cb; original capture time unknown. Commit time: 10:58:37 AM PDT. |
| [BrainBob identity](02-brainbob-identity-reconstructed.jpg) | Reconstruction | Captured 11:19:36 AM PDT. Character rebuilt from the earlier development edits, using the current room/UI. |
| [Round BrainBobs](03-round-brainbobs-reconstructed.jpg) | Reconstruction | Captured 11:19:44 AM PDT. Character rebuilt from the earlier development edits, using the current room/UI. |
| [Plush BrainBobs](04-plush-brainbobs.jpg) | Current implementation screenshot | Captured 11:19:29 AM PDT after implementation commit 172d1b3. |

The intermediate screenshots were overwritten by the rolling preview file.
Their replacements are explicitly labeled reconstructions, including an on-image label.
They do not establish exact original capture times, original character positions, or separate historical commits.
The reconstruction character sources are retained in [sources](../sources/).

The current capture was made while isolated reconstruction-preview files existed locally.
They were not used by the current app page and were removed after capture.
No temporary reconstruction route was shipped with that milestone.

These images document appearance and iteration. Memory activity is scripted, movement is ambient,
and no image establishes live model inference or measured memory accuracy.

## Rounded rectangle selection

| Image | Evidence type | Provenance |
| --- | --- | --- |
| [Character comparison](05-rounded-rectangle-study.jpg) | Current implementation screenshot | Captured 11:34:08 AM PDT after implementation commit 801a04b. Shows three silhouettes and the chosen rounded rectangle. |
| [Rounded rectangle workspace](06-rounded-rectangle-workspace.jpg) | Current implementation screenshot | Captured 11:34:09 AM PDT after implementation commit 801a04b. Shows the chosen design in the paused room. |

App sources were committed and unchanged during these captures; only new evidence files were present.
The character study is now a retained design page at `/character-study`, including a movement toggle.
Neither screenshot establishes the planned filing, writing, burning-paper, or teaching animations.

The approved version 1 appearance, palette, proportions, and animation requirements are documented in the [final character specification](../../../docs/character-design.md). It embeds the same original captures above; no new screenshot or later capture time is implied.

## Memory event rehearsals

Captured from committed frontend `37fcade` on October 17, 2026. Sources were unchanged; only evidence files were uncommitted. These images show paused animation fixtures, not live model calls or memory-quality results. Original UTC timestamps and descriptions are in [event-captures.json](event-captures.json).

- [07-memory-writing-rehearsal.jpg](07-memory-writing-rehearsal.jpg): 11:58:35 AM PDT. Rewrite fixture at 45%, with event selector and Sales Team scope.
- [08-evaluator-bob.jpg](08-evaluator-bob.jpg): 11:58:40 AM PDT. Evaluator fixture at 83%: inspector and workers delivering records.
- [09-office-fire-and-shredder.jpg](09-office-fire-and-shredder.jpg): 11:58:49 AM PDT. Deletion fixture at 62%: office-wide cartoon fire, panicking crew, flying sheets and shredded paper.
- [10-john-memory-retrieval.jpg](10-john-memory-retrieval.jpg): 11:59:07 AM PDT. Individual retrieval fixture at 43%, John selected in the event panel.

## Dramatic scene direction

Captured from committed frontend `bc9765d` on October 17, 2026. App sources were unchanged; only new evidence files were present. These are animation fixtures. Original UTC timestamps are in [dramatic-captures.json](dramatic-captures.json).

- [11-dramatic-office-fire.jpg](11-dramatic-office-fire.jpg): 12:07:59 PM PDT. Delete rehearsal at 62%, Sales Team. Night lighting, camera framing, tall flames, smoke, embers, flying paper, shredding, and worried BrainBobs. Paused with panels closed.
- [12-evaluator-spotlight.jpg](12-evaluator-spotlight.jpg): 12:08:11 PM PDT. Evaluate rehearsal at 83%, Sales Team. Violet surroundings, spotlight on Evaluator Bob, evidence papers and waiting workers. Paused with panels closed.

## HTTP/SSE frontend integration

Captured from committed frontend `9b36d2c` on October 17, 2026. App sources were unchanged; only new evidence files were present. The local server was an explicitly labeled, in-memory contract fixture, with no Crusoe inference. Original timestamps and descriptions are in [integration-captures.json](integration-captures.json).

- [13-cited-memory-check.jpg](13-cited-memory-check.jpg): 12:32:27 PM PDT. Recorded fixture check; evaluator visits the cited memory's cabinet.
- [14-retirement-retrace.jpg](14-retirement-retrace.jpg): 12:32:36 PM PDT. Recorded manual retirement, fire and shredding, and the retained record with original source. No confirmation claim.
- [15-flagged-owner-lock.jpg](15-flagged-owner-lock.jpg): 12:32:48 PM PDT. Flagged house rule remains locked; only Mr. Krabs can resolve it through the demo owner controls.
- [16-contract-chat-citations.jpg](16-contract-chat-citations.jpg): 12:32:59 PM PDT. CopilotKit renders the fixture response and citations while SSE drives retrieval. The canned answer does not assess corrected facts.

See [verification observations](../frontend-integration-verification.md) for the tested flows and remaining live validation.

## Rusty Rod memory correctness

Captured from committed frontend `6c84f78` on October 17, 2026. App sources were unchanged; only new evidence files were present. These are authored browser fixtures with no inference or server authorization claim. Original timestamps are in [rusty-rod-captures.json](rusty-rod-captures.json).

- [17-rusty-rod-tentative-estimate.jpg](17-rusty-rod-tentative-estimate.jpg): 12:51:08 PM PDT. Engineering’s tentative November 13 estimate leaves the approved November 6 organization commitment unchanged.
- [18-rusty-rod-fresh-sales.jpg](18-rusty-rod-fresh-sales.jpg): 12:51:17 PM PDT. A scripted fresh Sales agent cites the corrected November 13 organization revision and the preserved reporting goal.
- [19-rusty-rod-audit-coverage.jpg](19-rusty-rod-audit-coverage.jpg): 12:51:22 PM PDT. Seed 17 misses the decisive approval in its latest-50 sample; coverage and judgment are distinct and the valid record is retained.

## Tier drawers and session files

The initial team-cabinet layout was superseded by the requested Individual / Team / Organization hierarchy. Names, client context, and the session-file assembler were retained. All captures are synthetic browser fixtures; no inference or server authorization is implied. App sources were unchanged during each capture.

- [20-team-cabinets-client.jpg](20-team-cabinets-client.jpg): 1:05:21 PM PDT, `e167cfc`. Superseded team-cabinet layout.
- [21-agent-session-file.jpg](21-agent-session-file.jpg): 1:05:43 PM PDT, `e167cfc`. First assembled session panel in that earlier layout.
- [22-tier-cabinets.jpg](22-tier-cabinets.jpg): 1:14:55 PM PDT, `95c15b3`. Final tier cabinets and scoped named drawers.
- [23-tier-session-file.jpg](23-tier-session-file.jpg): 1:15:03 PM PDT, `95c15b3`. Leo’s session combines individual, Sales, and shared Rusty Rod knowledge.
- [24-tier-access-mobile.jpg](24-tier-access-mobile.jpg): 1:14:04 PM PDT, `89edbad`. 390×844 view with Sales accessible and Executive/Engineering closed.

Original timestamps and commit references: [earlier captures](session-file-captures.json), [final captures](tier-session-captures.json).

## Personalized session chat

Captured from local frontend commit `af8cf67` on October 17, 2026. Application sources were unchanged during capture. Both images show the synthetic `/demo` welcome, not model inference. The original screenshot bytes are preserved.

- [28-personal-session-chat.jpg](28-personal-session-chat.jpg): 1:54:36 PM PDT, 1280 × 720. Maya’s full-screen greeting, composer, three memory-based starter cards, and session-file control.
- [29-personal-session-chat-mobile.jpg](29-personal-session-chat-mobile.jpg): 1:54:44 PM PDT, 390 × 844. Mobile welcome with stacked cards and compact header controls.

Original timestamps: [personal-chat-captures.json](personal-chat-captures.json). Tested behavior and limitations: [verification record](../personal-chat-verification.md).

## Scene account switcher

Captured from local frontend commit `2c7770d` on October 17, 2026, with application sources unchanged. Both native screenshots show synthetic `/demo` identities.

- [30-scene-account-switcher.jpg](30-scene-account-switcher.jpg): 2:05:03 PM PDT, 1280 × 720. Bottom-left account control, current Maya context, New session, and grouped person search.
- [31-scene-account-switcher-mobile.jpg](31-scene-account-switcher-mobile.jpg): 2:05:10 PM PDT, 390 × 844. Mobile popup above the account row.

Original timestamps: [account-switcher-captures.json](account-switcher-captures.json). Tested behavior: [verification record](../account-switcher-verification.md).

## Three desk sessions

[32-three-active-sessions.jpg](32-three-active-sessions.jpg) was captured October 17, 2026, at 2:19:30 PM PDT, 1280 × 720, from local frontend commit `9d7e78a`. It shows Iris, Maya, and Mara at three desks facing the viewer, with computer screens and keyboards directed toward each operator. This is the synthetic `/demo` route, not evidence of three inference jobs. Native screenshot bytes are preserved.

Original timestamp: [three-desk-capture.json](three-desk-capture.json). Tested behavior and limits: [verification record](../three-desks-verification.md).
