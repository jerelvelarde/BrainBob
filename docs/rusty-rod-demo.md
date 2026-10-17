# Rusty Rod: memory correctness demo

The central problem is **memory correctness**: preventing wrong or stale shared knowledge from spreading across agents. Self-improvement is the outcome. The room makes the evidence, decisions, and revisions visible.

This guide follows [the company specification](sample-company.md) and supplements the earlier demo runbook. The frontend now uses Rusty Rod rather than the Krusty Krab/John fixtures. Historical screenshots retain their original names and appearance.

## Run the walkthrough

Run `pnpm dev`, then open `http://127.0.0.1:3000/demo`. No backend or API key is needed. This route is an explicitly **scripted fixture**, not an inference run or benchmark. The homepage's Demo link and the animation playground's Atlas demo link open it.

The three fixed cabinets represent Individual, Team, and Organization. Drawers represent people, teams (Executive, Sales, Engineering), and organizations. Only the selected member’s own, team, and Rusty Rod drawers are accessible. Rusty Rod is the office organization; Atlas Harbor is its fictional logistics client. The selector shows 18 synthetic names while preserving their stable IDs and 22 internal memory scopes. Six BrainBobs represent worker roles, not headcount.

Use Next, Previous, or the step selector to retrace; Replay repeats the current animation. Each step chooses a suggested viewer, and the viewer can be changed independently to inspect the intended scope policy. Session file opens the selected person’s task-specific dossier, including individual, team, and organization sections with accessible sources. Download session .md exports that assembled context. The desk folder also opens it. Cabinets open a tier inspector with available memory and closed drawers. Choosing a cabinet does not switch identity or grant access. Evidence opens the separate floating inspector. A record or citation opens its source; Export this view downloads only that member's synthetic records, sources, decision details, and audit metadata.

| Step | Suggested viewer | What to show |
| --- | --- | --- |
| Approved commitment | Maya Flores (`sales-01`) | Organization revision 1 says November 6, 2026, citing `atlas-approval-01`. The reporting goal is a separate valid record. |
| Tentative estimate | Iris Tan (`eng-01`) | Engineering estimates November 13; the organization commitment stays November 6. Integration readiness remains unresolved. |
| Scoped Sales answer | Maya Flores (`sales-01`) | The approved November 6 fact is used; Engineering records and evidence are absent from this view. |
| Authorized correction | Mara Ellis (`exec-01`) | Later organization approval creates revision 2 for November 13. The old record is retired as superseded, with both public sources retained. |
| Fresh-agent handoff | Leo Park (`sales-02`) | A scripted fresh-agent answer cites revision 2 and the unchanged reporting goal, without Engineering's private estimate or sales-01's personal note. |
| Stale source resurfaces | Maya Flores (`sales-01`) | The older November 6 source cannot undo the later approval. Revision 2 stays active. |
| Incomplete audit sample | Maya Flores (`sales-01`) | Seed 17 selects 10 of the latest 50 eligible fixture conversations, excluding the decisive approval in this view. Coverage is No; judgment is insufficient evidence; valid records stay active. |

Switch to Mara Ellis (exec-01) during the Engineering step: private records, sources, and the decision disappear. This demonstrates the intended presentation policy. **All fixture data is synthetic and shipped in the client bundle; this is not a security test or server authorization.**

The old animation playground remains at `/rehearsal`, with Rusty Rod labels and Atlas rehearsal records. Its manual retirement effect can still burn the office and shred paper. The correctness walkthrough does not retire unrelated valid knowledge just to show that effect. It does not conflate supersession with wholesale deletion.

## Keep the two evaluation signals separate

**Evidence correctness** checks source support, authority, time, conflicts, and uncertainty. The walkthrough's decisions are authored examples of these policies. They are not judgments made by a model.

**Leave-one-out usefulness** removes a cited memory and observes whether the answer's correctness changes. The live chat now calls this mode Usefulness. A helpful result does not certify a fact. The demo inspector displays this signal as Not run; no backend usefulness verdict is fabricated for a source check.

The sample preview records its seed, eligible and selected IDs, cutoff, and decisive-evidence coverage. It is a selected demonstration seed, not a scored sample or measured judgment accuracy. Missing a fact in the sample is never a deletion condition.

## Live status and Bonan's remaining handoff

The main route retains the existing HTTP/SSE integration documented in [frontend-integration.md](frontend-integration.md). Member reads now send Rusty Rod paths, and events retain their logical scopes while the animation visits the matching Individual, Team, or Organization cabinet. Both routes have a seated session Bob and clickable desk file. The main route snapshots and exports records returned by Ask; the full dossier with source bodies remains a scripted walkthrough feature. Server session assembly and exact model-input tracing are still pending. The default Remember request writes to the selected member's individual path. Reading organization memory does not confer approval or write authority.

The merged backend supports immutable corrections, source episodes, history, locks, leave-one-out events, scope filtering with a demo member marker, write-time maintenance, and recent-conversation audit code. The frontend accepts the new tentative records and conflict/audit events. The walkthrough remains scripted; it does not establish a live correctness result. The following are **requirements for a live correctness demonstration**, not claims about the current implementation:

| Requirement | Frontend expectation / remaining backend work |
| --- | --- |
| Server-side permissions | Authenticate the represented member and check reads, evidence, history, replay/live events, exports, and mutations. An arbitrary `reader` or `owner` string is not authentication. Executive is not a superuser. Bonan’s merged org mode now filters server reads and streams using a demo member marker; it is not authentication, and full access-isolation validation remains pending. |
| Correctness decisions | Provide source IDs, source timing and authority, checked memory ID/revision, decision, reason, unresolved conflicts, and committed resulting revision. Keep this distinct from existing `memory.checked` usefulness events; agree an additive contract before integrating new event types. |
| Authorized publication | Publish approved November 13 evidence to organization memory independently of the private Engineering conversation. Do not expose the private source through citations or supersession history. |
| Recent audit provenance | Emit cutoff, latest-50 eligible IDs, seed, selected IDs, evidence coverage, checked revisions, and omissions. Missing evidence should lead to retention/uncertainty rather than retirement. |
| Attribution and cost | Emit the actual model per extraction, retrieval, audit, and answering call, with tokens/cost when available. The fixture reports `model: null`, `cost: null`; it never labels synthetic decisions as NVIDIA or Crusoe output. |
| Live replay | Keep `seq`, memory IDs, sources, revisions, and decisions linked. Apply permission filtering before SSE replay and live delivery; continue to use `replay.done` to prevent old animations from bursting on reconnect. |

Bonan owns `backend/` and `bench/`; neither is modified by this frontend milestone. NemoClaw and Switchyard are not integrated in this frontend demonstration. The existing backend uses its configured Crusoe/NVIDIA roles; this milestone does not run or verify those calls.

## Measurement and allowed claims

Use no memory, append-only memory, and maintained memory with identical answering models, task splits, and retrieval budgets where applicable. Keep audit and held-out questions separate. Gold answers must not enter extracted memories or agent context. The scripted walkthrough is development material and must not be counted as held-out evaluation evidence.

Report correct updates; unsupported/stale overwrites; unsupported writes; unjustified forgetting; conflicts and abstentions; leakage through every surface; fresh-agent accuracy and stale-fact use; and total extraction, retrieval, audit, and answering cost. Evidence coverage and judgment accuracy are separate measures. See [benchmarks.md](benchmarks.md) for the broader plan.

The [760-question LoCoMo result](../backend/results/20261017-112134-locomo/results.md) reports 404/760 before and after auditing and zero retirements. That result does not establish a maintenance gain. A separate exploratory threshold stress test is not a replacement for a held-out maintenance comparison. The walkthrough displays no accuracy gain, cost saving, or security success score.

To turn this into a live demo, run the same sources and sequence through the authorized backend, capture the emitted trace and actual model attribution, then verify the fresh-agent response and denied access cases. A production-looking animation is not evidence that those checks passed.

The [session-file specification](session-files.md) defines the file assembly and the distinction between tier drawers, access, and task relevance.
