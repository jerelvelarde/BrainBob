# BrainBob correctness suite: Rusty Rod (heldout, 20261017-131504-correctness-heldout)

30 scenarios, 76 questions per condition. Answering nvidia/Nemotron-3.5-Lightning-30B-A3B; extraction nvidia/Nemotron-3.5-Lightning-30B-A3B; judge openai/gpt-oss-120b. Retrieval top 10 over the asking member's readable scopes; full_history gets every readable raw episode in date order, no retrieval. Audit seed 7.

| condition | accuracy | stale_usage | correct_update | unjustified_forgetting | abstention | uncertainty | leakage | avg_ctx_tokens |
|---|---|---|---|---|---|---|---|---|
| none | 10/76 | 0/24 | - | - | 9/10 | 0/3 | 0 | 0 |
| append_only | 67/76 | 4/24 | 0/13 | 0/32 | 7/10 | 1/3 | 0 | 117 |
| maintained_no_audit | 68/76 | 1/24 | 12/13 | 0/32 | 7/10 | 0/3 | 0 | 106 |
| maintained | 68/76 | 1/24 | 12/13 | 0/32 | 7/10 | 0/3 | 0 | 106 |
| full_history | 73/76 | 1/24 | - | - | 9/10 | 2/3 | 0 | 88 |

| condition | Extraction | Updates | Retention | Forgetting | Shared handoff | Insufficient evidence |
|---|---|---|---|---|---|---|
| none | 3/14 | 1/12 | 0/13 | 1/11 | 3/14 | 2/12 |
| append_only | 13/14 | 11/12 | 12/13 | 11/11 | 12/14 | 8/12 |
| maintained_no_audit | 13/14 | 12/12 | 13/13 | 11/11 | 13/14 | 6/12 |
| maintained | 13/14 | 12/12 | 13/13 | 11/11 | 13/14 | 6/12 |
| full_history | 13/14 | 12/12 | 13/13 | 11/11 | 13/14 | 11/12 |

## Paired bootstrap (2000 resamples over the same questions), percentage points
- maintained_no_audit - append_only: accuracy +1.3 [-5.3, +7.9]; stale-fact usage -3.9 [-9.2, +0.0]
- maintained - maintained_no_audit: accuracy +0.0 [+0.0, +0.0]; stale-fact usage +0.0 [+0.0, +0.0]
- append_only - none: accuracy +75.0 [+63.2, +85.5]; stale-fact usage +5.3 [+1.3, +10.5]

## Recent-conversation audit (maintained condition, run before answering)
- seed 7; sampled 97 episodes, 464 memory checks, 25 corrections proposed through maintain.
- Evidence coverage (decisive episode sampled): 13/13. Each scenario has at most 8 episodes, so a sample of 10 takes all of them; coverage is complete by construction here.
- Judgment accuracy (verdict matches fixture gold, only pairs the fixture decides): 193/194; {'supported->supported': 192, 'contradicted->contradicted': 1, 'supported->contradicted': 1}

## Cost and latency by stage

| stage | role | calls | cached | prompt tok | completion tok | USD fresh | wall s |
|---|---|---|---|---|---|---|---|
| extraction | curator | 97 | 0 | 17318 | 4503 | 0.0018 | 10.7 |
| ingest_append_only | curator | 97 | 97 | 17318 | 4503 | 0.0000 | 0.2 |
| ingest_maintained | curator | 97 | 97 | 17318 | 4503 | 0.0000 | 24.0 |
| ingest_maintained | judge | 391 | 0 | 101424 | 51733 | 0.0180 | 24.0 |
| audit | curator | 25 | 25 | 4358 | 941 | 0.0000 | 42.4 |
| audit | judge | 625 | 65 | 142654 | 88268 | 0.0261 | 42.4 |
| answer_none | agent | 76 | 0 | 19081 | 942 | 0.0011 | 25.8 |
| answer_append_only | agent | 76 | 3 | 39705 | 1771 | 0.0023 | 98.2 |
| answer_maintained_no_audit | agent | 76 | 39 | 37820 | 1790 | 0.0011 | 4.6 |
| answer_maintained | agent | 76 | 76 | 37820 | 1790 | 0.0000 | 0.2 |
| answer_full_history | agent | 76 | 3 | 31259 | 1700 | 0.0019 | 21.8 |

Total fresh $0.0523 (incl. cached $0.0826); wall 228.9s. Prompt hashes {'agent': '93e213d5b877', 'maintain': 'e0343d98fecd', 'audit': 'd213a3f72ae7', 'curator': 'a64d5eefed57'}.

## Grading rules (deterministic, fixed before running)
- Text is lowercased to alphanumerics; a phrase matches with a word boundary on the left and no digit on the right.
- Fact question: correct if any accepted string appears. Stale-fact usage: a forbid value appears (counted separately even when the right value is also present; abstain questions excluded).
- abstain: an 'I don't know'-type phrase and no forbid value. uncertain: every listed value appears, or a conflict/unresolved phrase appears.
- Access leakage: retrieved memories whose scope is in must_not_retrieve or outside the member's readable scopes (must be 0).
- Correct update: an active non-tentative memory has the new value and no active memory states the old value without the new one. Unjustified forgetting: a keep value survives only in retired memories.

## Failures (maintained)
- ex-5-q3 [abstain] sales-01: Are we proposing an analytics retainer to Orchid, and for how much? -> 'No, we are not proposing an analytics retainer to Orchid. The available memories do not contain any information about an analytics retainer proposal or pricing.'
- fo-4-q1 [fact, stale] eng-02: How do we access Willow Schools systems? -> 'Okta is used for all access to Willow Schools systems, as the VPN requirement has been dropped and zero-trust SSO is now in place.'
- sh-1-q3 [abstain] sales-05: Do we know which vendor Zephyr's buyer currently favors? -> "No, the memories do not contain information about which vendor Zephyr's buyer currently favors. The available records only cover Zephyr Air's compliance requirements, internal handoffs, and a delayed decision date."
- in-1-q1 [uncertain] eng-10: Which cloud will Helix Bio's genomics pipeline run on? -> "Helix Bio's genomics pipeline runs on AWS Batch."
- in-1-q2 [fact] eng-10: What kind of pipeline are we building for Helix Bio? -> "We are building an AWS Batch pipeline for Helix Bio. This is supported by the active memory that AWS Batch is the platform already used by Helix Bio's data team (m3), and the active memory confirming the pipeline is plan"
- in-2-q1 [abstain] sales-02: What renewal amount are we expecting from Ivory Retail? -> 'The conversation history does not specify a renewal amount for Ivory Retail. The only related memory is [m1], which mentions that renewal conversations start next month, but it does not state the expected amount.'
- in-2-q2 [fact] sales-02: Who is leading the Ivory Retail renewal? -> "I don't know."
- in-3-q1 [uncertain] eng-02: How long will the Kite Energy billing migration take? -> 'The Kite Energy billing migration is estimated to take 6 weeks.'
- in-5-q1 [uncertain] eng-03: When is the Opal Insurance portal launching? -> 'December 8'