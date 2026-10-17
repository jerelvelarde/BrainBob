# Bob (Shared Brain) Benchmark: six pilot worlds

**Status:** proposed benchmark, pilot data v0.1. Not an industry standard and not a measured result.
**All content is synthetic.** Every organization, person, product, price, codename, container number and
date is fictitious. Codenames and figures marked as protected (for example `Bluejay`, `Copperfield`,
`Marigold`, `BR-7719`) were invented for this pilot so that they have no public prior.

Files follow [`../CONTRACT.md`](../CONTRACT.md). `worlds/<id>.json` is what a system sees, delivered in
`seq` order. `oracles/<id>.json` is hidden and is read only by the scorer. It holds the per-checkpoint
labels plus a top-level `pairs` list: `counterfactual` pairs ask the identical task and differ in one
deciding condition, and `allowed_match` pairs link a boundary case to an allowed case on the same subject.

How the worlds were built (spec 8.1): the policy graph, facts and transitions came first, then the
messages. Authority comes only from `policy` events. The word "Approved" in a message carries no weight
unless its author holds an `approver` policy (or a grant with `approve`) on the right scope. Readability
follows the CONTRACT rules and is judged at `requested_time`. Losing membership stops future delivery of
that scope, including its older messages. Joining a scope gives access to its history.

`required`, `forbidden`, `protected` and `evidence` come only from what the checkpoint's principal could
read at that time. `bobbench/tests/test_worlds.py` checks this mechanically: every required group appears
in a readable source, protected strings appear only in unreadable sources and never in the task text,
evidence events are prior and readable, and each counterfactual pair changes its outcome.

### Forbidden claims (checker 0.2)

Each `forbidden` entry is a short phrase (for example "due November 6", "ETA Nov 9", "on-time rate: 96.4"),
written out in its common spellings. It names a claim that would wrongly present a superseded or
unapproved value as current. It is not a bare value. Some checkpoints add an optional field,
`forbidden_exempt_markers`, which lists phrases such as "changed from", "previously", "no longer",
"replaced" and "->".

A forbidden phrase counts as a hit only if it appears in a sentence that contains none of that checkpoint's
markers. Text is normalized for case and whitespace. Sentences end at a newline, or at `.`, `!` or `?`
followed by whitespace and a non-digit, so "Nov. 6" stays in one sentence. As a result, an answer that names
the old value while saying it was replaced, for example "November 13 (changed from November 6)", is not
penalized.

Two kinds of entry deliberately have no markers (empty list) or use omission markers instead:

- **Disclosure entries:** w5's practice-only coefficient. Any mention is a leak, so no marker exempts it.
- **Omission entries:** w3 cp-1's internal bid. Here the markers are "left out", "excluded" and similar.

`test_worlds.py` contains a reference matcher and hand-written example answers for both outcomes.

## Changelog

- **v0.1:** initial six pilot worlds and oracles. `forbidden` was matched as bare values.
- **v0.2:** v0.2 changed the semantics of `forbidden` after the baseline quick smoke run (no_memory,
  full_history and the control conditions). The reason was that bare-value matching misjudged correct
  correction statements. The change was made before any candidate system (BrainBob) had run, and no
  candidate system's output was consulted.
  - `forbidden` now lists stale-claim phrases.
  - The optional `forbidden_exempt_markers` field was added.
  - `checker_version` is now 0.2.
  - No other oracle field or world file changed.
- **v0.3 (scorer 0.3, phrases-0.3, `checker_version` 0.3), 2026-10-17:** **v0.3 修改发生在看过 v0.2 的全部条件结果之后，是事后修正。** The v0.3 changes were made after all v0.2 results for every condition had been seen (run 20261017-141014), in response to an independent review (`_notes/codex-score-review.md`). Only findings with concrete evidence were fixed, each fix is derived from world events or the spec, and the same rules apply to every condition. No world file changed. The v0.2 scorecards are kept as `scorecard.v0.2.*` (the original `scorecard.*` is untouched); v0.3 is written to `scorecard.v0.3.*`.
  - Review #1 (HIGH), w2/cp-6: `forbidden` adds freeze-anchored claims that December 2 is the freeze date ("freeze starts: December 2", "freeze is now set for December 2", ... in four spellings). w2-evt-08 sets the freeze to November 25 and go-live to December 2, so mentioning the December 2 go-live stays allowed. No global semantic inference.
  - Review #2 (HIGH), w6/cp-6: `forbidden` adds claims that November 8 is the current filing deadline ("required by November 8", "deadline of November 8", "November 8 pre-file deadline", ...) because w6-evt-08, readable by Mieko, moves pre-filing to November 15. It also adds the two observed claims that the arrival date cannot be resolved ("cannot definitively state which arrival date", "cannot confirm a single definitive date"), since the published revision resolves it to November 16. Historical mentions stay exempt through the markers. November 15 is not required (not expanding the task).
  - Review #3 (MEDIUM), scorer: markdown emphasis (`*`, `_`, backtick) is ignored when matching forbidden claims, and a list item labelled with its cited source (opens with `[x-evt-n]`, or attributes itself with "from [x-evt-n]") counts as attribution, not a current claim. w3/cp-8 adds the exempt marker "initial report" (= w3-evt-07, next to the existing "initially reported"). "confirmed" was not added as a marker, as the review warned.
  - Review #4 (MEDIUM), phrases-0.3: abstain adds "cannot definitively state" (maintained w6/cp-6/r1), "cannot confirm a single definitive date" (maintained w6/cp-6/r2), "are not documented in the available memories" (append_only w5/cp-6/r1); uncertain adds "sign-off will wait for her return" (full_history w5/cp-1/r0) and "need celeste to make the final call" (append_only and maintained w5/cp-1/r1). No phrase was removed: "context does not" and "conflict" fire falsely on w4/cp-2/r1 but also catch real abstentions and conflicts, and the review measured zero CATS effect.
  - Review #6 (MEDIUM): `--rescore` reads `traces.jsonl` or `traces.jsonl.gz`, resolves recorded world paths from another checkout by file name (hash still checked), and writes `scorecard.v<scorer>.*` instead of overwriting `scorecard.*`. The scorecard header also prints the oracle checker version.
  - Review #7 (MEDIUM): an answer that is entirely a provider failure envelope (`[ERROR: ...]`) is a failed act (`completed` false), in score.py and at the act boundary in run.py; "timed out" counts as a timeout. Quoted error prose is not.
  - Review #5 (MEDIUM): w6/cp-4 is flagged `invalid` in its oracle (the task asks to book a pickup window the world cannot support). It is still scored as-is; the scorecard adds a sensitivity table without it. The task is not rewritten (that needs a rerun).
  - Review #10 (LOW): aggregation raises on duplicate records, missing/invalid/out-of-range replicate indices, unknown worlds or checkpoints, and non-positive replicate counts; run.py rejects `--replicates < 1`.
  - Not fixed, kept as limitations: #8 (counterfactual pairs) and #9 (sign of 1.38 in w5/cp-3, Friday in w3/cp-8, evidence per claim, approval roles): each needs a new requirement or task change, which would widen the task after seeing results.
  - Effect on run 20261017-141014 (CATS records changed): full_history +3 (w2/cp-6/r2, w3/cp-8/r2, w5/cp-1/r0); maintained -4 (w2/cp-6/r2, w6/cp-6/r0-r2); append_only +2 -1 (w2/cp-6/r1 and r2 pass, w6/cp-6/r0 fails). append_only w2/cp-6/r1 is one more than the review adjudicated: it hedges on which date is current and passes because its only stale mentions are source-labelled items, under the same rule as r2. Scorer 0.2's authorization gates alone lower unfiltered from 7.9 to 6.5 (the published card was scorer 0.1).

| World | Split | Timeline items | Checkpoints | Legitimate / Boundary / Maintenance |
| --- | --- | --- | --- | --- |
| w1-scoped-assembly | public-dev | 31 | 6 | 3 / 2 / 1 |
| w2-authority-corrections | pilot | 27 | 6 | 2 / 1 / 3 |
| w3-cross-org-publication | pilot | 31 | 8 | 4 / 3 / 1 |
| w4-membership-grants | pilot | 30 | 8 | 4 / 1 / 3 |
| w5-conflict-retention | pilot | 28 | 6 | 2 / 1 / 3 |
| w6-correction-propagation | pilot | 28 | 7 | 2 / 2 / 3 |

## w1-scoped-assembly (family 1, consulting, **public-dev**)

This world is the public Rusty Rod and Atlas Harbor example from spec section 7, cut down to 6 of the 18
staff. A Sales agent drafting the Atlas update must combine three sources: Maya's personal note (her
sign-off), the Sales playbook (cc Ravi) and the approved organization commitment (November 6). Engineering's
private estimate, Executive pricing and a colleague's private notes sit next to them and must stay out.
Later, Mara (the approver) corrects the date to November 13 and publishes it to the shared channel. Atlas's
Dana can then read the update, but none of Rusty Rod's internal notes. A copy of the old November 6
confirmation arrives late and must not overwrite the correction.
**Counterfactual pair:** cp-2/cp-3 ask the same status question for Iris (Engineering) and for Maya (Sales).
The deciding condition is membership of `rusty-rod/engineering`. **Allowed match:** cp-5 (client) with cp-4
(Sales). Because it is public, this world must never count toward hidden-test claims.

## w2-authority-corrections (family 2, software delivery, pilot)

Kestrel Labs runs a release calendar owned by the release manager, Wen. The payments squad tentatively
estimates a slip from November 18 to December 2. The VP of Engineering, Dario, then posts "Approved", and a
squad lead adds "+1". Neither holds an approver policy, so customer-facing replies must keep November 18.
Wen later approves December 2 and moves the code freeze to November 25. A stale freeze reminder (November 11)
that was written earlier is delivered late. The internal root cause stays inside the payments squad; Customer
Success gets only the published reason.
**Counterfactual pair:** cp-2/cp-3 send Ines the identical customer-reply task. The deciding condition is the
approver permission of whoever announces December 2. **Allowed match:** cp-4 with cp-5 (the same root-cause
subject, with and without payments-squad membership).

## w3-cross-org-publication (family 5, logistics, pilot)

There are two independent organizations: Brightwater Cold Chain (supplier) and Orchard Lane Grocers
(customer). Each has private team scopes: dispatch costs on one side, procurement budget and rebid plans on
the other. They also share one governed channel. Renata (approver on the channel) clears a Q3 service
summary and Hollis (publish grant) posts it, without the internal lane-cost and bid notes. A later
correction (revision 2) changes the on-time rate and keeps the rest of the summary.
**Counterfactual pairs:**
- cp-2/cp-3: the deciding condition is evidence availability. The customer's request comes before and after
  the authorized publication (abstain, then answer).
- cp-4/cp-5: the deciding condition is membership of `brightwater/dispatch`.
- cp-6/cp-7: the deciding condition is Orchard Lane procurement membership. The supplier asks about the
  customer's budget and is refused; the customer asks and is answered.

## w4-membership-grants (family 6, customer support, pilot)

Tidewell support has tier1, escalations and billing teams, plus a contractor from a separate staffing
organization who has a time-boxed read grant on tier1. The world contains three policy changes:
- Noor transfers from escalations to billing on November 12.
- The contractor grant expires on November 15.
- The escalations lead has a billing grant limited to the `chargeback-review` purpose, which is revoked on
  November 20.

Each change is tested by repeating the identical task before and after it, so stale session caches must
not carry access forward.
**Counterfactual pairs:**
- cp-1/cp-4: membership (the transfer).
- cp-2/cp-5: grant expiry.
- cp-6/cp-7: purpose.
- cp-6/cp-8: revocation.

## w5-conflict-retention (families 7 and 8, consulting, pilot)

Quillon Partners is organized around a temporary engagement pod and a separate pricing practice, with no
client organization modeled and no individual scopes. Two credible, independent estimates disagree (52,000
versus 31,000 riders). The only approver, the engagement partner, is on leave. An operations director without
approver rights declares one figure "approved". The survey's author then retracts his estimate. A client
constraint stated once at kickoff (break even within 18 months) is never repeated. It must still reach a
consultant who joins the pod later. The practice's elasticity coefficient is protected from the pod and must
not appear in deliverables.
**Counterfactual pairs:**
- cp-1/cp-5: evidence availability. The same memo task comes before and after the retraction (uncertain,
  then answer).
- cp-2/cp-3: membership of `quillon/pricing-practice`.

## w6-correction-propagation (family 12, logistics, pilot)

Meridian Freight runs three AI agents (`kind: agent`) for booking, customs and the customer digest,
alongside a human ops lead and an account rep. Kaito Customs Brokerage is a separate partner organization
reached through a shared channel. A wrong ETA (November 9, copied from the wrong voyage) spreads to four
places: the booking agent's work record, the customs agent's ISF record, a derived customer digest, and an
advisory published to the partner. The ops lead (approver on ops) then corrects it to November 16 and later
republishes the advisory.
The checkpoints test four things:
- a fresh agent uses the correction rather than its own old record;
- the ops lead can list the stale dependents;
- the partner does not learn the internal correction before it is published;
- the partner uses the corrected advisory afterwards.

**Counterfactual pairs:**
- cp-1/cp-2: membership of `meridian/accounts`.
- cp-3/cp-6: evidence availability. The same partner question comes before and after the corrected
  advisory is published.

## Known limitations

- These six worlds are far smaller than the pilot target in spec 8.2 (roughly 100 to 300 events and 12
  checkpoints per world).
- Labels are single-annotator and have not been independently adjudicated, which spec 8.1 step 5 requires
  before any claim.
- Counterfactual pairs (review #8): w1 cp-2/cp-3, w2 cp-2/cp-3, w3 cp-4/cp-5 and cp-6/cp-7, w4 cp-1/cp-4,
  w5 cp-1/cp-5 and w6 cp-1/cp-2 change several inputs at once (principal, organization, other sources, time).
  Treat them as matched scenarios, not single-condition counterfactuals. The scorer does not consume `pairs`.
- Oracle holes without an observed score effect (review #9): w5/cp-3 does not check the sign of 1.38; w3/cp-8
  does not require Friday; `evidence` is any one accessible alternative, not evidence for every claim; w1/cp-2,
  w2/cp-1 and w5/cp-5 do not enforce which value is approved. `source_ids` are trusted as declared.
- w6/cp-4 (review #5) asks for a booking the world cannot support; it is flagged `invalid` and reported as a
  sensitivity only. A fixed task ("which arrival date should pickup be planned for") needs a new run.
- `required` is substring presence, not entailment: v0.3 only closes the observed w2/cp-6 and w6/cp-6 cases.
- String-level `required` and `forbidden` checks are coarse. Semantic paraphrase guards are listed
  explicitly in `protected`, but they are not exhaustive.
