# BrainBob correctness suite: Rusty Rod (dev, 20261017-125945-correctness-dev)

6 scenarios, 11 questions per condition. Answering nvidia/Nemotron-3.5-Lightning-30B-A3B; extraction nvidia/Nemotron-3.5-Lightning-30B-A3B; judge openai/gpt-oss-120b. Retrieval top 10 over the asking member's readable scopes; full_history gets every readable raw episode in date order, no retrieval. Audit seed 7.

| condition | accuracy | stale_usage | correct_update | unjustified_forgetting | abstention | uncertainty | leakage | avg_ctx_tokens |
|---|---|---|---|---|---|---|---|---|
| none | 1/11 | 0/4 | - | - | 1/1 | - | 0 | 0 |
| append_only | 8/11 | 0/4 | 0/3 | 0/4 | 0/1 | - | 0 | 143 |
| maintained_no_audit | 9/11 | 0/4 | 1/3 | 0/4 | 1/1 | - | 0 | 129 |
| maintained | 9/11 | 0/4 | 1/3 | 0/4 | 1/1 | - | 0 | 129 |
| full_history | 11/11 | 1/4 | - | - | 1/1 | - | 0 | 84 |

| condition | Extraction | Updates | Retention | Forgetting | Shared handoff | Insufficient evidence |
|---|---|---|---|---|---|---|
| none | 0/2 | 0/2 | 0/2 | 0/1 | 0/2 | 1/2 |
| append_only | 1/2 | 2/2 | 1/2 | 1/1 | 2/2 | 1/2 |
| maintained_no_audit | 1/2 | 1/2 | 2/2 | 1/1 | 2/2 | 2/2 |
| maintained | 1/2 | 1/2 | 2/2 | 1/1 | 2/2 | 2/2 |
| full_history | 2/2 | 2/2 | 2/2 | 1/1 | 2/2 | 2/2 |

## Paired bootstrap (2000 resamples over the same questions), percentage points
- maintained_no_audit - append_only: accuracy +9.1 [-18.2, +36.4]; stale-fact usage +0.0 [+0.0, +0.0]
- maintained - maintained_no_audit: accuracy +0.0 [+0.0, +0.0]; stale-fact usage +0.0 [+0.0, +0.0]
- append_only - none: accuracy +63.6 [+18.2, +100.0]; stale-fact usage +0.0 [+0.0, +0.0]

## Recent-conversation audit (maintained condition, run before answering)
- seed 7; sampled 19 episodes, 95 memory checks, 7 corrections proposed through maintain.
- Evidence coverage (decisive episode sampled): 3/3. Each scenario has at most 8 episodes, so a sample of 10 takes all of them; coverage is complete by construction here.
- Judgment accuracy (verdict matches fixture gold, only pairs the fixture decides): 37/40; {'supported->supported': 37, 'supported->insufficient': 3}

## Cost and latency by stage

| stage | role | calls | cached | prompt tok | completion tok | USD fresh | wall s |
|---|---|---|---|---|---|---|---|
| extraction | curator | 18 | 0 | 2573 | 7356 | 0.0016 | 282.9 |
| ingest_append_only | curator | 19 | 18 | 2713 | 7420 | 0.0000 | 22.5 |
| ingest_maintained | curator | 19 | 19 | 2713 | 7420 | 0.0000 | 25.7 |
| ingest_maintained | judge | 109 | 0 | 28123 | 13776 | 0.0049 | 25.7 |
| audit | curator | 7 | 7 | 1024 | 420 | 0.0000 | 21.4 |
| audit | judge | 152 | 36 | 35838 | 24576 | 0.0060 | 21.4 |
| answer_none | agent | 11 | 0 | 2757 | 121 | 0.0002 | 216.8 |
| answer_append_only | agent | 10 | 1 | 5622 | 237 | 0.0003 | 275.0 |
| answer_maintained_no_audit | agent | 11 | 4 | 5992 | 291 | 0.0002 | 10.3 |
| answer_maintained | agent | 11 | 11 | 5992 | 291 | 0.0000 | 0.0 |
| answer_full_history | agent | 11 | 0 | 4489 | 227 | 0.0003 | 10.1 |

Total fresh $0.0134 (incl. cached $0.0257); wall 866.8s. Prompt hashes {'agent': '93e213d5b877', 'maintain': 'e0343d98fecd', 'audit': 'd213a3f72ae7', 'curator': '17f16bc77d32'}.

## Grading rules (deterministic, fixed before running)
- Text is lowercased to alphanumerics; a phrase matches with a word boundary on the left and no digit on the right.
- Fact question: correct if any accepted string appears. Stale-fact usage: a forbid value appears (counted separately even when the right value is also present; abstain questions excluded).
- abstain: an 'I don't know'-type phrase and no forbid value. uncertain: every listed value appears, or a conflict/unresolved phrase appears.
- Access leakage: retrieved memories whose scope is in must_not_retrieve or outside the member's readable scopes (must be 0).
- Correct update: an active non-tentative memory has the new value and no active memory states the old value without the new one. Unjustified forgetting: a keep value survives only in retired memories.

## Failures (maintained)
- ex-dev-q2 [fact] eng-02: What's the phase-one fee for Jasper Freight? -> "I don't know."
- up-dev-q2 [fact] sales-03: What date is the Basalt kickoff? -> '2026-09-24'