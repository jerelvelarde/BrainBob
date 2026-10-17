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
