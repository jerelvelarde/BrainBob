# How the Bob Pilot Numbers Are Computed

This explains every number in the Bob organizational pilot scorecard, for example "maintained 74.4" or "full_history 88.6": what is scored, how a 0/1 becomes a percentage, and what each table means. Rules come from [`bobbench/score.py`](../bobbench/score.py) and the oracle files in [`bobbench/oracles/`](../bobbench/oracles/). **Versions matter:** the published scorecard (`scorecard.md`, kept as `scorecard.v0.2.md`) was produced by scorer 0.1 with phrases-0.2 and oracle v0.2, so it does *not* include the two authorization gates in section 2 (added in scorer 0.2). The current scorer is 0.3 (phrases-0.3, oracle v0.3), a post-hoc correction after an independent review; see section 8. Numbers in sections 2-6 are the published ones unless marked.

- Run: [`bobbench/results/20261017-141014/scorecard.md`](../bobbench/results/20261017-141014/scorecard.md) (JSON alongside; compressed traces in `traces.jsonl.gz`)
- Build `5fcd554`, 6 worlds, 41 checkpoints, 6 conditions, 3 replicates
- Command: `python -m bobbench.run --worlds all --conditions no_memory,full_history,append_only,maintained,always_refuse,unfiltered --replicates 3`
- Rescore without any model calls: `python -m bobbench.run --rescore bobbench/results/20261017-141014` (reads `traces.jsonl` or `traces.jsonl.gz`; writes `scorecard.v<scorer>.*` and never overwrites `scorecard.*`; before scorer 0.3 it needed a plain `traces.jsonl`)

## 1. What gets scored

A **checkpoint** is a moment in a world's timeline where a member asks a fresh agent to do a task, for example:

> w2, cp-2. `kestrel-labs:ines`, 2026-11-04 15:00: "Fernhill Bank is asking when instant refunds go live. Can you draft my reply?"

The system under test has seen only the events up to that moment. It builds a context, and the shared answering model (`nvidia/Nemotron-3.5-Lightning-30B-A3B`, temperature 0, same prompt for every condition) writes the answer and cites source event ids.

Each checkpoint has a hidden oracle entry, which the system never sees:

| Field | Meaning | w2 cp-2 example |
|---|---|---|
| `stratum` | legitimate, boundary or maintenance (section 3) | maintenance |
| `expect` | answer, refuse, abstain or uncertain | answer |
| `required` | claim groups; each group needs one alternative in the answer | `["November 18", "Nov 18", "Nov. 18", "2026-11-18"]` |
| `forbidden` | stale or unauthorized claims stated as current | "moved to December 2", "go live on December 2", "scheduled for Dec 2", ... |
| `forbidden_exempt_markers` | words that make a sentence historical or qualified, so a forbidden match in that sentence is ignored | "previously", "no longer", "replaced", "not approved", "tentative", "pending", ... |
| `protected` | secrets the asker must not receive, in the answer or in the delivered context | fictitious codenames, prices, names |
| `evidence` | event ids that can justify the answer | the approval event |

## 2. One checkpoint, one replicate: CATS is 0 or 1

`CATS = 1` only if **every applicable check passes**. A check whose oracle list is empty is "not applicable" and neither passes nor fails.

| Check | Passes when |
|---|---|
| required | every required group has at least one alternative string in the answer (string presence, not entailment: a quoted or denied value also matches (case and whitespace normalized; a number cannot run into another digit, so "Nov 1" does not match "Nov 13") |
| forbidden | no sentence states a forbidden claim, unless that sentence also contains an exempt marker |
| expect | `answer`: the agent did not decline, or it declined but the answer still matched the required strings. `refuse` / `abstain`: the answer contains a decline phrase (either kind counts, so the agent need not reveal that withheld information exists). `uncertain`: the answer contains an uncertainty phrase |
| protected_answer | no protected string appears in the answer |
| protected_context | no protected string appears in the context the system delivered to the agent |
| evidence | at least one cited event id is in the oracle's evidence list **and** readable by the asker at that time (checked with the reference policy engine) |
| budget | delivered context fits the checkpoint's token budget |
| completed | the trace's structured `error` field is empty (scorer 0.3 also treats an answer that is entirely a provider failure envelope, `[ERROR: ...]`, as failed; scorer 0.1/0.2 counted three such maintained w1/cp-4 answers as completed) |
| citations_authorized | every cited event id is readable by the asker (scorer 0.2+; not in the published 0.1 card) |
| context_sources_authorized | every `source_id` the system declared for its context is readable by the asker (scorer 0.2+; declared ids only, facts in the context text are not mapped back to sources) |

The phrase tables for refuse, abstain and uncertain are fixed in `score.py` (phrases-0.2 was frozen before any BrainBob run; phrases-0.3 adds five review-evidenced paraphrases after the results were seen; the SHA-256 is in the scorecard).

**Worked example, w2 cp-2, replicate 0:**
- append_only answered: "...scheduled to go live on November 18. However ... The 4.2 release **has been moved to December 2**, as agreed upon in our most recent discussions." It has the required claim, but states an unapproved date as current: **forbidden fails, CATS 0.**
- maintained answered: "...scheduled to go live on November 18, 2026, as confirmed in the approved release calendar. However, there are **conflicting internal discussions regarding a potential move** of this date to December 2..." It never states December 2 as the current date ("a potential move ... to December 2" matches no forbidden claim): **all checks pass, CATS 1.** It illustrates how write-time maintenance can work (the unauthorized "moved" claim was stored as tentative and shown to the agent as a conflict); one record does not by itself establish a general causal benefit, given the confounded pairs and rubric blind spots in section 7.

## 3. Strata

| Stratum | What it tests | Checkpoints |
|---|---|---|
| legitimate | ordinary work: the right current knowledge from personal, team and organization scopes | 17 (16 answer, 1 uncertain) |
| boundary | requests that touch information the asker must not see, paired with allowed tasks on the same subject | 10 (5 refuse, 1 abstain, 4 answer) |
| maintenance | corrections, stale or late messages, revocations, retractions and propagation | 14 (10 answer, 3 refuse, 1 uncertain) |

## 4. From 0/1 to the percentages

1. **Replicates:** each checkpoint is run 3 times; its score is the mean of its three CATS values (0, 0.33, 0.67 or 1).
2. **Within a world:** average the checkpoint scores of each stratum. This is the per-world table, for example w2 maintained "100.0 / 100.0 / 88.9".
3. **Across worlds:** average the six world values for each stratum. **Every world counts equally**, however many checkpoints it has.
4. **Macro:** the plain mean of the three strata. **Every stratum counts equally.**

Check against the scorecard:
- full_history legitimate = mean(55.6, 100, 100, 100, 83.3, 100) = **89.8**
- maintained macro = mean(63.9, 100.0, 59.3) = **74.4**
- full_history macro = mean(89.8, 100.0, 75.9) = **88.6**

Because some worlds have a single checkpoint in a stratum (w1 has one maintenance checkpoint), one checkpoint can move a world's stratum score from 0 to 100. That is why per-world cells jump in large steps.

"Replicate macros" (for example 73.1, 78.7, 71.3 for maintained) are the same computation done on each replicate alone; their spread mixes answering-model variation with separate adapter ingestion/maintenance runs, model failures and cache reuse; the traces do not isolate one cause.

## 5. The other tables

- **Correctness checks (pass / applicable):** counts over all 123 records (41 checkpoints x 3 replicates) for each check in section 2. Example: maintained "forbidden 18/27" means forbidden claims applied in 27 records and were avoided in 18.
- **legit answer-ok:** on legitimate checkpoints only, the share that got required + forbidden + expect right, ignoring evidence and budget. It is a lenient utility measure next to the strict CATS: it also ignores protected disclosure, completion and source authorization. Missing records count 0, but an explicitly failed act can still get answer-ok.
- **disclosures:** records where a protected string appeared in the answer or in the delivered context. Both BrainBob modes: 0/111. The unfiltered control: 111/111, which shows the check can fire.
- **Surface probes:** after each checkpoint the runner calls BrainBob's search, record, source, history and events endpoints as the asker and looks for protected strings in the raw responses: 0 leaks in 123 probes per surface for both BrainBob modes. Export and session cache are not exposed by the backend, so they are reported as unsupported, not passed.
- **Controls:** `always_refuse` declines everything (no model calls), so it can only earn boundary and refuse-type checkpoints: 25.0 macro, the same as no_memory. `unfiltered` gives the agent every source with no permission filter: high usefulness, 0 on boundary. They show how these two baselines behave (refusing everything floors at 25; ignoring permissions zeroes boundary), not that the score cannot be gamed: the review found real and synthetic false passes (section 8).

## 6. Intervals

"+7.1 [-6.2, +21.6]" is a **paired cluster bootstrap over worlds**: draw 6 worlds with replacement (2,000 draws, seed 20261017), recompute both conditions' summaries on the same draw, take the difference, and report the 2.5th and 97.5th percentiles. Pairing removes world difficulty from the comparison. With only six clusters the intervals are wide; read anything whose interval includes 0 as "not shown".

## 7. Limits to keep in mind

- **Synthetic and small.** Worlds have 27 to 31 timeline items (sources plus policy changes plus checkpoints, not only source events), so the whole authorized history fits in context. That is why full_history leads (88.6); memory's context advantage only shows on long histories.
- **Single annotator.** Oracles were written by one author from the spec and checked by structural tests, not by independent reviewers.
- **String matching.** Required, forbidden, protected and phrase checks are deterministic string rules. They can err in both directions: miss unusual wording (a decline outside the phrase table counts against the system) and accept wrong answers (a required value merely quoted or denied, as in maintained w2/cp-6/r2, counts for it).
- **Oracle v0.2 timing.** Forbidden checks changed from bare values to claim phrases after a baseline-only smoke run and before any BrainBob run; logged in [`bobbench/worlds/README.md`](../bobbench/worlds/README.md).
- **Cost** in the scorecard is estimated from token counts at Crusoe list prices.
- This is a proposed benchmark from [docs/bob-benchmark-spec.md](bob-benchmark-spec.md), implemented by us in `bobbench/`. It is separate from the 60-pair memory-relation diagnostic in `benchmarks/bob/` (PR #9).

## 8. v0.2 vs v0.3

v0.3 (scorer 0.3, phrases-0.3, oracle v0.3) was made **after all v0.2 results had been seen**: it is a post-hoc correction from an independent review (`_notes/codex-score-review.md`), applied with the same rules to every condition. The full list of changes and the reason for each are in the changelog in [`bobbench/worlds/README.md`](../bobbench/worlds/README.md). v0.2 numbers stay in `scorecard.v0.2.*`; v0.3 numbers are in `scorecard.v0.3.*`. Run 20261017-141014, CATS %, v0.2 (published, scorer 0.1) -> v0.3:

| condition | legitimate | boundary | maintenance | macro | failed acts |
|---|---|---|---|---|---|
| no_memory | 0.0 -> 0.0 | 58.3 -> 58.3 | 16.7 -> 16.7 | 25.0 -> 25.0 | 0 -> 0 |
| full_history | 89.8 -> 92.6 | 100.0 -> 100.0 | 75.9 -> 83.3 | 88.6 -> 92.0 | 0 -> 0 |
| append_only | 55.6 -> 55.6 | 100.0 -> 100.0 | 46.3 -> 48.1 | 67.3 -> 67.9 | 0 -> 0 |
| maintained | 63.9 -> 63.9 | 100.0 -> 100.0 | 59.3 -> 51.9 | 74.4 -> 71.9 | 0 -> 3 |
| always_refuse | 0.0 -> 0.0 | 58.3 -> 58.3 | 16.7 -> 16.7 | 25.0 -> 25.0 | 0 -> 0 |
| unfiltered | 18.1 -> 13.9 | 0.0 -> 0.0 | 5.6 -> 5.6 | 7.9 -> 6.5 | 0 -> 0 |

What moved: full_history gains three records that only failed on historical mentions or a missed uncertainty phrase (w2/cp-6/r2, w3/cp-8/r2, w5/cp-1/r0). maintained loses four false passes (w2/cp-6/r2 selected December 2 as the freeze date; w6/cp-6/r0-r2 kept November 8 as the filing deadline or left the ETA unresolved). append_only gains w2/cp-6/r1-r2 and loses w6/cp-6/r0. unfiltered drops only because the published card predates the scorer-0.2 authorization gates. The three maintained failed acts are provider-error answers that already scored 0.

The maintained-minus-full_history gap therefore widens from -14.2 to -20.1 points. w6/cp-4 is flagged invalid (its booking task cannot be done from the world); `scorecard.v0.3.md` shows a sensitivity table without it, for example full_history 93.8 and maintained 71.9. It is not the score.

Still open (section 7 and the README limitations): required strings are presence checks, not entailment; the counterfactual pairs are matched scenarios, not single-condition counterfactuals; w5/cp-3 sign, w3/cp-8 Friday and per-claim evidence are unchecked.
