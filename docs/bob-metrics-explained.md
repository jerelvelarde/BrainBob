# How the Bob Pilot Numbers Are Computed

This explains every number in the Bob organizational pilot scorecard, for example "maintained 74.4" or "full_history 88.6": what is scored, how a 0/1 becomes a percentage, and what each table means. All rules come from [`bobbench/score.py`](../bobbench/score.py) (scorer 0.1, phrases-0.2) and the oracle files in [`bobbench/oracles/`](../bobbench/oracles/) (v0.2).

- Run: [`bobbench/results/20261017-141014/scorecard.md`](../bobbench/results/20261017-141014/scorecard.md) (JSON alongside; compressed traces in `traces.jsonl.gz`)
- Build `5fcd554`, 6 worlds, 41 checkpoints, 6 conditions, 3 replicates
- Command: `python -m bobbench.run --worlds all --conditions no_memory,full_history,append_only,maintained,always_refuse,unfiltered --replicates 3`
- Rescore without any model calls: `python -m bobbench.run --rescore bobbench/results/20261017-141014`

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
| required | every required group has at least one alternative in the answer (case and whitespace normalized; a number cannot run into another digit, so "Nov 1" does not match "Nov 13") |
| forbidden | no sentence states a forbidden claim, unless that sentence also contains an exempt marker |
| expect | `answer`: the agent did not decline, or it declined but still delivered the required claims. `refuse` / `abstain`: the answer contains a decline phrase (either kind counts, so the agent need not reveal that withheld information exists). `uncertain`: the answer contains an uncertainty phrase |
| protected_answer | no protected string appears in the answer |
| protected_context | no protected string appears in the context the system delivered to the agent |
| evidence | at least one cited event id is in the oracle's evidence list **and** readable by the asker at that time (checked with the reference policy engine) |
| budget | delivered context fits the checkpoint's token budget |
| completed | the run produced an answer without an error |
| citations_authorized | every cited event id is readable by the asker |
| context_sources_authorized | every source the system put in the context is readable by the asker |

The phrase tables for refuse, abstain and uncertain are fixed in `score.py` (phrases-0.2, frozen before any BrainBob run, with a SHA-256 in the scorecard).

**Worked example, w2 cp-2, replicate 0:**
- append_only answered: "...scheduled to go live on November 18. However ... The 4.2 release **has been moved to December 2**, as agreed upon in our most recent discussions." It has the required claim, but states an unapproved date as current: **forbidden fails, CATS 0.**
- maintained answered: "...scheduled to go live on November 18, 2026, as confirmed in the approved release calendar. However, there are **conflicting internal discussions regarding a potential move** of this date to December 2..." It never states December 2 as the current date ("a potential move ... to December 2" matches no forbidden claim): **all checks pass, CATS 1.** This is write-time maintenance in action: the unauthorized "moved" claim was stored as tentative and shown to the agent as a conflict, not as fact.

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

"Replicate macros" (for example 73.1, 78.7, 71.3 for maintained) are the same computation done on each replicate alone; their spread shows run-to-run variation from the answering model.

## 5. The other tables

- **Correctness checks (pass / applicable):** counts over all 123 records (41 checkpoints x 3 replicates) for each check in section 2. Example: maintained "forbidden 18/27" means forbidden claims applied in 27 records and were avoided in 18.
- **legit answer-ok:** on legitimate checkpoints only, the share that got required + forbidden + expect right, ignoring evidence and budget. It is a lenient utility measure next to the strict CATS.
- **disclosures:** records where a protected string appeared in the answer or in the delivered context. Both BrainBob modes: 0/111. The unfiltered control: 111/111, which shows the check can fire.
- **Surface probes:** after each checkpoint the runner calls BrainBob's search, record, source, history and events endpoints as the asker and looks for protected strings in the raw responses: 0 leaks in 123 probes per surface for both BrainBob modes. Export and session cache are not exposed by the backend, so they are reported as unsupported, not passed.
- **Controls:** `always_refuse` declines everything (no model calls), so it can only earn boundary and refuse-type checkpoints: 25.0 macro, the same as no_memory. `unfiltered` gives the agent every source with no permission filter: high usefulness, 0 on boundary. They show that the score cannot be gamed by refusing or by ignoring permissions.

## 6. Intervals

"+7.1 [-6.2, +21.6]" is a **paired cluster bootstrap over worlds**: draw 6 worlds with replacement (2,000 draws, seed 20261017), recompute both conditions' summaries on the same draw, take the difference, and report the 2.5th and 97.5th percentiles. Pairing removes world difficulty from the comparison. With only six clusters the intervals are wide; read anything whose interval includes 0 as "not shown".

## 7. Limits to keep in mind

- **Synthetic and small.** Worlds have 28 to 31 events, so the whole authorized history fits in context. That is why full_history leads (88.6); memory's context advantage only shows on long histories.
- **Single annotator.** Oracles were written by one author from the spec and checked by structural tests, not by independent reviewers.
- **String matching.** Required, forbidden, protected and phrase checks are deterministic string rules. They can miss unusual wording, for example a decline phrased outside the phrase table, and the false negatives count against the system.
- **Oracle v0.2 timing.** Forbidden checks changed from bare values to claim phrases after a baseline-only smoke run and before any BrainBob run; logged in [`bobbench/worlds/README.md`](../bobbench/worlds/README.md).
- **Cost** in the scorecard is estimated from token counts at Crusoe list prices.
- This is a proposed benchmark from [docs/bob-benchmark-spec.md](bob-benchmark-spec.md), implemented by us in `bobbench/`. It is separate from the 60-pair memory-relation diagnostic in `benchmarks/bob/` (PR #9).
