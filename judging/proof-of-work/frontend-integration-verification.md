# Frontend integration verification

Implementation: `9b36d2c043fd6ea6469674e109cd83ab2b22581c`, committed October 17, 2026 at 12:32:14 PM PDT.

## Automated checks

Final verification began at 12:31:56 PM PDT. All commands exited successfully:

```text
pnpm --filter @brainbob/web test       24 tests, 4 files passed
pnpm --filter @brainbob/web typecheck  passed
pnpm --filter @brainbob/web build      passed; /, /character-study, /rehearsal
git diff --check                      passed
```

The tests cover scope boundaries; replay without animation; duplicate/reconnect sequence handling; immutable corrections and predecessor state; locked flags and owner keep; confirmed versus unconfirmed retirement labels; cited-memory check verdicts; HTTP request payloads; AG-UI run/message lifecycle; blocked mutations during retrace; missing feedback tasks; HTTP 403 and invalid-response errors. The Node chat test uses AG-UI SDK exports instead of importing CopilotKit's CSS-bearing browser barrel; the actual CopilotKit adapter was exercised in the browser.

## Browser observations

Tested the main frontend against `apps/web/scripts/contract-fixture.mjs` on local port 3001. The fixture uses in-memory records and scripted replies/verdicts, makes no model calls, and labels its data. It was stopped after QA. No Bonan backend, Crusoe connection, quality metric, or real retirement confirmation was verified.

- John saw organization, Sales, and personal records; switching to Sales removed John's personal record.
- Ask returned the fixture answer and clickable citations through CopilotKit; SSE queued retrieval/answer scenes.
- Check submitted the last task's correct answer and displayed the fixture's two-flip receipt. Individual helpful, harmful, and no-flip events appeared in retrace.
- Remember filed a new personal memory with its supplied text and scope.
- Inspection loaded the source conversation and full correction/status history.
- Correcting the Sales launch retained the original retired record, produced a new superseding record, and selected the writing scene without office fire. Retracing the creation event restored the original October 24 state.
- Mr. Krabs locked the house rule. John saw disabled resolution controls. Review flagged the locked record without retiring it; changing the demo actor to Mr. Krabs allowed Keep and cleared the flag.
- Manual retirement preserved the record and its source, queued the fire scene, and displayed no confirmation claim.
- Reload restored event-projected state without replaying animations. No warnings/errors were recorded after the final clean connected reload.
- After stopping the fixture, the header showed Backend offline and a submitted Ask displayed a clear connection error. The expected CopilotKit development error badge appeared for that failed request.

Browser checks used the desktop in-app browser at 1280 × 720. Earlier hot-refresh errors were fixed during implementation; this report concerns the final committed sources. No mobile/device performance benchmark or OS reduced-motion setting change was performed in this milestone.

## Captures

Four original screenshots were captured after the implementation commit, with app sources unchanged. UTC timestamps, descriptions, execution mode, and SHA are recorded in [integration-captures.json](screenshots/integration-captures.json). The screenshots prove the frontend's rendering and fixture wiring, not memory correctness. In particular the chat fixture always answers October 24, even after a correction; it is deliberately not an evaluator.

The new milestone is embedded in [the offline changelog](index.html). Older entries and image bytes are preserved. The page was statically validated for unique IDs, timeline targets, local links, and embedded image integrity; no new browser preview of the offline HTML is claimed.
