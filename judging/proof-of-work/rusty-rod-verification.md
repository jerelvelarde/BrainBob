# Rusty Rod frontend verification

Implementation: `6c84f787a24a8ed35eeaa51b1cef106e42aba470`, committed October 17, 2026 at 12:50:48 PM PDT. Checked in Jerel’s frontend session.

- 31 Vitest tests passed, including seven new correctness-fixture tests: scope structure, tentative conflicts, correction lineage and retention, filtered evidence/exports, deterministic eligible sampling, missing-evidence retention, and stale-source handling.
- TypeScript and the Next.js production build passed. The final follow-up edits were an accessible label, fixture seed text/scope, and trailing whitespace; fixture syntax and diff checks passed afterward.
- Desktop browser: Engineering's estimate leaves the approved date at November 6; Executive preview hides Engineering records and sources. The approved correction exposes its public source and supersedes chain. Fresh sales-02 cites revision 2 and the preserved reporting goal. Seed 17 misses the decisive approval and reports insufficient evidence rather than deletion.
- Main workspace: all 18 member choices are present; selecting eng-10 changes the cabinets to ENG-10, ENGINEERING, and RUSTY ROD. Main Demo and playground Atlas demo navigate to the walkthrough.
- Mobile at 390×844: evidence panel, source text, close control, next-step navigation, and room layout checked. Temporary viewport override was reset afterward.
- Capture-session browser logs contained no errors or warnings after the implementation commit. Screenshots are unmodified and linked in the changelog.

The route `/demo` is an authored fixture. No agent inference, live backend correctness evaluation, server access enforcement, model cost, or accuracy improvement was measured. JSON view filtering was unit tested; browser download behavior was not separately exercised. Reduced-motion handling was retained in code but not tested by changing OS settings. Existing backend integration remains on `/`; the backend was offline during these checks.

The [scenario guide](../../docs/rusty-rod-demo.md) lists the live handoff and evidence needed. Backend and bench were not edited. README, architecture, and the earlier demo runbook remain as previously held for review.
