# Organizational Bob pilot review — 2026-10-17

Reviewed Bonan's `bobbench/` at `13df1c0`, against
[the specification](bob-benchmark-spec.md) and [adapter contract](../bobbench/CONTRACT.md).
The recorded model run is build `5fcd554`; later code and tests do not retroactively
verify that run. This review is separate from the 60-pair `benchmarks/bob/` diagnostic.

## Standards

**[P1] Source/history probes are empty but counted as successful checks.**
`AGENTS.md` requires incomplete work to remain clearly labeled and forbids invented
results. `bobbench/run.py:173–176` supplies query/time/purpose, but
`bobbench/adapters/brainbob.py:340–351` calls source/history routes only for explicit
event/episode/memory IDs. It returns `supported: true, responses: []` without a
request. `bobbench/score.py:175–189` treats these empty objects as clean.

The original compressed traces confirm 123 source and 123 history probe objects
**with zero HTTP responses** in each BrainBob condition. Search, record and events
each have 123 actual responses. Thus five surface names were recorded, but only
three surfaces were exercised. Answer/context leakage results are a separate
measurement; this finding alone does not alter their CATS values.

Correction: mark unexercised probes untested; provide delivered IDs for targeted
source/history requests and test the runner-to-adapter path. Preserve historical
artifacts and narrow the coverage claim until that run exists.

## Spec

**[P1] Sentence-wide exemptions accept a wrong current date.** The specification
requires “No contradictory, unsupported material claim changes the result” (§12.1)
and checking deliberately wrong dates (§13). `bobbench/score.py:109–111` exempts the
whole sentence when it contains `previously`. Against actual W2 checkpoint cp-2,
“Previously due November 18, the release is now scheduled for December 2.” with
citation `w2-evt-01` receives **CATS=1** even though November 18 remains approved.
The historical matcher has the same behavior. Attach exceptions to the specific
claim/value, add reversed old/current-date controls, then rescore every condition
consistently under a new scorer version. The impact on the published aggregate has
not been quantified by this review.

**[P2] Revocation checks cover fresh sessions, not an already-open session.** The
specification requires stopping future delivery “including through existing session
caches” (§4.4), while the worlds README says the paired checks prevent stale caches
carrying access forward. `bobbench/run.py:140–182` opens and closes every checkpoint
session before delivering subsequent policy changes. Add an open → revoke/expire →
act schedule, or narrow the claim to fresh-session retrieval. Adapter unit tests
are not evidence that the recorded model run exercised session-cache revocation.

One Standards finding (worst: unexercised probes counted clean); two Spec findings
(worst: a demonstrably wrong current-date answer passes CATS). No blocking style
refactors were identified. Keep fixes scoped to score validity and accurate claims.

## Reproduce and use the results

[Offline findings](../judging/benchmark-review-20261017/findings.json) record the
counterexample and trace counts. From the repository root:

```sh
backend/.venv/bin/python judging/benchmark-review-20261017/reproduce.py
```

No model calls, training, or historical aggregate rescoring were performed.
Published macro CATS (74.4 maintained / 67.3 append-only / 88.6 full history) remains
a historical score under the original scorer, with these validity caveats. Keep
the nonsignificant maintained-minus-append-only interval [-6.2, +21.6]. Do not claim
five exercised surfaces or complete session-cache conformance. Bonan owns the
bounded follow-up in issue #4; the in-progress judge-swap should use one declared,
consistent scorer and retain raw outputs for any later rescore.

## Round-two checker handoff and publication status

The [fresh frozen 60](../benchmarks/bob/round2/README.md) exports label-free inputs
and hashes; the answer key remains evaluator-local. The old 60 are development
for further tuning. Freeze all comparison checkpoints/predictions before feedback.

The requested earlier changes were already on public `main` when checked:
`51058a1` adds external readiness; `cb3e297` and `c4e9b7a` record readiness;
`dece5dd` adds the local judge callback; `efbaef0` reconciles Bonan's adapter and
audit changes; `5bcb3bb` pins the adapter revision. `BrainBobAdapter(judge=...)`
retains write-time injection and the existing audit path. No duplicate hook was
introduced by this review. GateMem, MUMBench and CoMemBench still have no BrainBob
scores; see [Bonan's access report](external-benchmark-status.md).
