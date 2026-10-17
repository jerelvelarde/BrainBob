# BrainBob Evaluation Report

Status date: 2026-10-17 (Pacific). Reconciled with Bonan's [published v0.3 report](https://github.com/jerelvelarde/BrainBob/blob/373eee2e11891e43232ae509c1d7de9ae3567e3a/docs/evaluation-report.md) at `373eee2`. Experiments retain their original inference builds; the organizational scores were corrected after inspecting the saved answers. No inference or rescoring was performed for this documentation update.

**Current headline:** maintained memory **71.9%** vs no memory **25.0%** macro CATS; maintained vs append-only **+4.0 points [−9.0, +18.2]**, inconclusive. Use [Experiment 6](#experiment-6-bob-organizational-pilot-proposed-benchmark-synthetic) for the v0.3 table, original v0.2 table, and coverage limits.

The v0.3 scorecards are copied unchanged from the published build. Reproduction requires the [v0.3 scorer and oracles](https://github.com/jerelvelarde/BrainBob/blob/373eee2e11891e43232ae509c1d7de9ae3567e3a/bobbench/score.py) introduced in `c241b6e`; that scorer is included in the published main history. The documentation refresh does not rerun it. [Metric derivation](https://github.com/jerelvelarde/BrainBob/blob/373eee2e11891e43232ae509c1d7de9ae3567e3a/docs/bob-metrics-explained.md).

## Supported headlines

1. **Memory makes a small model answer LoCoMo questions it otherwise cannot: held-out accuracy rose from 85/760 (11%) with no memory to 404/760 (53%) with BrainBob memory** (10 conversations, Nemotron-3.5-Lightning-30B answering). Source: [LoCoMo run](../backend/results/20261017-112134-locomo/results.md).
2. **On a 50-question LongMemEval subset, BrainBob's answer context averaged 2,681 tokens against 108,946 for the full history (about 1/40), at a cost of 4 questions: 35/50 (70%) vs 39/50 (78%).** The 8-point gap is 4 questions out of 50; no interval was computed, so this does not establish accuracy equivalence. Source: [LongMemEval subset run](../bench/results/20261017-110432/results.md).
3. **In the one evaluation whose rules were frozen before the run (BANKING77, n=300 held-out, same tasks and same answering model in every condition), the change-and-observe audit changed accuracy by +0.0 points, paired 95% bootstrap interval [-1.3, +1.3]: 202/300 with all memories vs 202/300 audited.** This is a null result and is reported as one. Source: [BANKING77 stream run](../backend/results/20261017-122228-stream-banking77/results.md).

4. **On 30 held-out synthetic Rusty Rod scenarios, write-time maintenance left the correct current fact active and the superseded one retired in 12/13 update checks, against 0/13 for append-only memory, while wrongly retiring 0 of 32 valid memories.** Answer accuracy was 68/76 vs 67/76 (+1.3 pts [-5.3, +7.9], not significant). Source: [Rusty Rod run](../backend/results/20261017-131504-correctness-heldout/results.md).
5. **On the six-world Bob organizational pilot (41 checkpoints, 3 replicates), maintained BrainBob memory scored 71.9% macro CATS against 25.0% for no memory (+46.9 pts [+22.7, +71.1]), with zero protected-string disclosures in 111 applicable answer/context records. Surface coverage is narrower than the five names in the raw table; see Experiment 6.** Scored with the corrected scorer and oracle v0.3 (v0.2: 74.4%, +49.4 [+23.1, +75.2]). The unfiltered control disclosed in every opportunity, so the scorer does detect leakage. Source: [Bob pilot v0.3 scorecard](../bobbench/results/20261017-141014/scorecard.v0.3.md).
6. **A LoRA fine-tune lifted Qwen3-0.6B on the 60-pair memory-relation diagnostic from 32/60 to 42/60 (+16.7 pts, template-cluster 95% [+5.0, +28.3]).** The same set gives 53/60 to the production judge gpt-oss-120b and 56/60 to the Nemotron Super teacher, so the small checker does not yet replace them. Source: [checker results](../experiments/memops-small/out/runs/20261017-210457/).

## Claims we do not make

- **Maintenance beats append-only on the Bob pilot.** v0.3: maintained 71.9 vs append_only 67.9 macro CATS, +4.0 pts [-9.0, +18.2] (v0.2: +7.1 [-6.2, +21.6]); the interval includes zero and per-world results go both ways.
- **BrainBob beats full history on the Bob pilot.** full_history scored 92.0 macro CATS (v0.3; 88.6 in v0.2); the pilot worlds have 27 to 31 timeline items, so the whole authorized history fits in context.
- **The tuned checker improves the organizational pilot.** In Experiment 8 it scored 72.2 vs 68.5 for the default judge, +3.7 [-11.1, +18.5] under v0.3, one replicate per world. This does not establish benefit, equivalence, or non-inferiority.
- **The tuned 0.6B checker can become the default judge.** It trails both large judges and calls 5 non-conflict pairs "conflict" (base: 0), which raises overwrite risk under authorized corrections.
- **Scores on GateMem, MUMBench or CoMemBench.** None were run; see [external-benchmark-status.md](external-benchmark-status.md).

- **The evaluator (audit) improves accuracy.** The frozen-rule paired result is +0.0 pts [-1.3, +1.3] (BANKING77), and on LoCoMo the audited and unaudited groups are identical at 404/760 (the audit retired 0 memories and promoted 2). The exploratory threshold variants below show no interval that excludes zero.
- **BrainBob is more accurate than reading the whole history.** On the LongMemEval subset it was 4 questions lower (35/50 vs 39/50). The claim is about context size, not accuracy.
- **Memory correctness improves answers.** Experiment 5 shows maintenance keeps memory state current (12/13 vs 0/13 on synthetic scenarios), but answer accuracy did not improve significantly, and maintained memory was weaker on insufficient-evidence questions. Experiments 1 to 4 measure whether a memory changed a graded answer, not whether it is true.
- **The recent-conversation audit helps.** It changed no answer in Experiment 5.
- **Results are leaderboard scores.** LongMemEval is a 50-question subset judged by gpt-oss-120b (the official protocol uses GPT-4o). LoCoMo and BANKING77 use our own splits and prompts. None is comparable to published numbers.
- **Memory always helps.** On BANKING77, "all" was worse than "none" on 26 held-out tasks (and better on others); net effect was 202/300 vs 189/300 and we computed no interval for that comparison.
- **Statistical power on LoCoMo conditions or the noisy-writer test.** No paired interval was computed for those runs.

## Usefulness vs truth

BrainBob's change-and-observe evaluator ("改了再看") removes one memory, re-asks the task, and records whether the graded answer flipped. That measures **usefulness**: did this memory change correctness on a task. It does not measure **truth**. A false memory can help an answer by luck, and a true memory can look harmful when the model misuses it. The LoCoMo run recorded 54 harm-changes and the noisy run retired 7 memories at the most aggressive threshold on single-question harm evidence; those are usefulness signals, not verdicts that the facts were wrong.

Factual correctness is handled by write-time maintenance (commit `0346089`) and a seeded audit of recent conversations with coverage reported apart from judgment (commit `b82fde7`). Experiment 5 measures these on synthetic Rusty Rod scenarios; Experiment 6 measures organizational checkpoint outcomes. Neither converts a usefulness signal into proof that a fact is true.

## Demo examples vs held-out results

The [live-workspace evidence](../judging/live-workspace-20261017/README.md) records real Crusoe ingestion, a correction, fresh-member answers, citations, and retrace. Earlier proof-of-work entries also include scripted and fixture previews. Preserve those labels: chosen demonstrations show that a flow ran, not how often it succeeds.

Reported task/audit splits and scoring versions belong to each experiment. The organizational worlds and original 60 checker pairs are public synthetic pilot data; the checker pairs have now been inspected case by case and are development data for further tuning. v0.3 is a post-hoc scoring correction, not a new frozen evaluation.

## Integration status

- Inference goes **directly to Crusoe Managed Inference** (OpenAI-compatible client in `backend/brainbob/llm.py`). Historical experiment model IDs by role (from their builds and result files; the current live-app launcher uses Nano extraction and Super answering):

| Role | Model id | Used in |
| --- | --- | --- |
| Answering agent (default) | `nvidia/Nemotron-3.5-Lightning-30B-A3B` | LoCoMo, noisy LoCoMo, BANKING77 |
| Answering agent (LongMemEval) | `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B` | LongMemEval subset |
| Memory writer ("curator", "curator_careful") | `nvidia/Nemotron-3.5-Lightning-30B-A3B` | all runs |
| Sloppy writer ("curator_sloppy", temp 1.2) | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` | noisy LoCoMo, BANKING77 |
| Third writer ("curator_qwen") | `Qwen/Qwen3.8-27B` (not NVIDIA) | BANKING77 |
| Judge (LongMemEval, LoCoMo) | `openai/gpt-oss-120b` (not NVIDIA) | LongMemEval, LoCoMo, audit checks |

  BANKING77 grading is deterministic exact label match, no judge. The BANKING77 `summary.json` does not record model ids; they are the role defaults in `llm.py` at commit `833911b`, assuming `BRAINBOB_AGENT_MODEL` was unset.
- **NVIDIA NemoClaw/OpenClaw: adapter implemented; sandbox integration and end-to-end validation pending.** [PR #13](https://github.com/jerelvelarde/BrainBob/pull/13) adds scoped memory tools, an MCP server, configuration templates, and an operator-driven smoke script. It supplies no live harness evidence and changes none of these benchmark runs. **NVIDIA Switchyard: not integrated.** The verified app retains direct Crusoe inference.

## Experiment 1: LongMemEval subset (50 questions)

- **Setup.** Fixed 50-question subset ([subset_ids.json](../bench/subset_ids.json)). Conditions: `full` (entire history in context) vs `brainbob` (facts extracted from the history, BM25 top-40 retrieved). Same 50 questions and same answering model in both.
- **Models.** Answer: Nemotron-3-Super-120B. Extraction: Nemotron-3.5-Lightning-30B (thinking off). Judge: openai/gpt-oss-120b at temperature 0 with the official LongMemEval prompts (official uses GPT-4o).
- **Result.** full 39/50 (78%); brainbob 35/50 (70%). Average context 108,946 vs 2,681 tokens. Per type, brainbob vs full: knowledge-update 8/8 vs 7/8, multi-session 7/13 vs 10/13, temporal-reasoning 8/13 vs 9/13, single-session-user 5/7 vs 6/7, abstention 4/4 vs 4/4, single-session-assistant 6/6 vs 6/6, single-session-preference 1/3 vs 1/3. The biggest loss is multi-session (3 questions).
- **Paired difference / interval.** Not computed. The difference is -4 questions.
- **Cost.** $2.299 total for the whole run: answer $1.859, extraction $0.437, judge $0.003. Wall time 404 s. Cost counts replayed cached calls too.
- **Limitations.** n=50. Judge differs from the official one. Extraction failed to parse or returned empty on 76 episodes (`extract_parse_fail` 76, `extract_empty` 76; 61 extraction retries), so some histories are under-remembered. Retries: 26 answer, 8 judge. This run exercises extraction and retrieval only; the audit was not part of it. Produced by `bench/run.py` at commit `b86c109`.
- **Artifacts.** [results.md](../bench/results/20261017-110432/results.md), [summary.json](../bench/results/20261017-110432/summary.json), predictions and judgments in the same folder.

## Experiment 2: LoCoMo, 10 conversations

- **Setup.** 10 conversations (conv-26, 30, 41, 42, 43, 44, 47, 48, 49, 50). 760 held-out questions scored; a separate 780-question audit split drove the evaluator (2,377 memories written, 267 flips). Groups: `none` (no memory), `all` (all written memories), `audited` (after the evaluator's retire/promote decisions). Same questions and answering model per group. Evaluator at its default `min_changes=3`.
- **Models.** Agent, writer: Nemotron-3.5-Lightning-30B-A3B. Judge: openai/gpt-oss-120b.
- **Result.**

| group | correct / total | avg ctx tokens (est.) |
| --- | --- | --- |
| none | 85/760 (11%) | 0 |
| all | 404/760 (53%) | 1,199 |
| audited | 404/760 (53%) | 1,199 |

  By category (none / all / audited): single-hop 63/418, 292/418, 292/418; multi-hop 12/138, 48/138, 48/138; open-domain 9/45, 20/45, 20/45; temporal 1/159, 44/159, 44/159. The audit retired 0, promoted 2, flagged 0 (54 harm-changes observed), so `audited` equals `all`.
- **Paired difference / interval.** Not computed.
- **Cost.** $0.3701 fresh ($0.5229 including cached replays). Wall time 524 s. Calls: curator 544, agent 4,193, judge 4,193.
- **Limitations.** The model never saw the question's source conversation in `none`, so the 11% to 53% gap shows memory is useful for this task, not that the memories are true. Judge is an LLM. Own split of LoCoMo, not the published protocol. The audit had no effect here, so this run says nothing in favor of the audit.
- **Artifacts.** [results.md](../backend/results/20261017-112134-locomo/results.md), [summary.json](../backend/results/20261017-112134-locomo/summary.json), events.jsonl. Code commit `e2b4cf5`.

## Experiment 3: LoCoMo stress test with a careless writer

- **Setup.** 2 conversations (conv-26, conv-30), 115 held-out questions, 118 audit questions. Two writers: the normal curator (319 memories) and a deliberately noisy one (`curator_sloppy`, Nemotron-3-Nano-30B at temperature 1.2, 389 memories). 34 flips.
- **Result.**

| group | correct / total |
| --- | --- |
| none | 11/115 (10%) |
| careful_only | 49/115 (43%) |
| all | 56/115 (49%) |
| audited_min3 | 56/115 (49%) |
| audited_min2 | 56/115 (49%) |
| audited_min1 | 59/115 (51%) |

  `min_changes=3`: retired 0, promoted 0. `min_changes=2` (exploratory): promoted 1. `min_changes=1` (exploratory): retired 7, promoted 21. Author ledger at min 3: curator helped 18 / harmed 8; curator_sloppy helped 5 / harmed 3.
- **Cost.** $0.0687 fresh ($0.1468 including cached). Wall time 1,006 s.
- **Limitations.** n=115 on two conversations. The min_changes=2 and 1 tiers are post hoc. The +3 questions at min 1 is not an interval-backed effect. The noisy writer's memories did not hurt overall (`all` > `careful_only`), so this test did not demonstrate that the audit rescues a bad writer. Retired memories were retired for one-question harm, which is a usefulness signal (see above). Code commit `f308bab`.
- **Artifacts.** [results.md](../backend/results/20261017-113727-locomo/results.md), [summary.json](../backend/results/20261017-113727-locomo/summary.json).

## Experiment 4: Frozen-rule paired evaluation on BANKING77 (issue #4)

This is the paired evaluation required by issue #4: rules fixed before the run, held-out tasks, identical tasks and answering setup across conditions.

- **Frozen before the run.** `min_changes=3` (the evaluator default in `backend/brainbob/evaluator.py`), the held-out split (seed 42, label-stratified), top-8 retrieval, and the main metric (`audited_min3` minus `all`, paired bootstrap, 2,000 resamples).
- **Setup.** BANKING77 77-way intent classification, 600 training tasks streamed in batches of 25 (writers learn lessons; training accuracy 364/600), then 300 held-out tasks. 600 memories, three writers at 200 each. The evaluator ran 833 checks and saw 98 flips. Grading is exact label match.
- **Models.** Agent: Nemotron-3.5-Lightning-30B-A3B. Writers: Nemotron-3.5-Lightning-30B (`curator_careful`), Nemotron-3-Nano-30B at temp 1.2 (`curator_sloppy`), Qwen3.8-27B (`curator_qwen`). See the caveat under Integration status.
- **Result (held-out, 300 tasks).**

| condition | correct / total | avg ctx tokens (est.) |
| --- | --- | --- |
| none | 189/300 (63%) | 0 |
| all (no audit, ordinary memory) | 202/300 (67%) | 547 |
| audited_min3 (pre-frozen rule) | 202/300 (67%) | 544 |
| only curator_careful | 179/300 (60%) | 481 |
| only curator_sloppy | 176/300 (59%) | 621 |
| only curator_qwen | 191/300 (64%) | 506 |

- **Primary paired difference.** `audited_min3 - all`: **+0.0 pts, 95% CI [-1.3, +1.3]**. At min 3 the evaluator retired 3 memories and promoted 2, and it changed no held-out outcome net.
- **Exploratory (added after seeing the data; not part of the frozen protocol).**

| variant | correct / total | audited minus all (95% CI) |
| --- | --- | --- |
| audited_min2 | 203/300 | +0.3 pts [-2.0, +2.3] |
| audited_min1 | 203/300 | +0.3 pts [-3.0, +3.7] |
| audited_author | 203/300 | +0.3 pts [-3.0, +3.7] |

  `audited_author - none` was +4.7 pts [-0.3, +9.3]. Retirements at min 1: 28 memories (30 with the author rule). Of the 248 held-out tasks that retrieved a retired-at-min-1 memory, accuracy was 162/248 with `all` and 163/248 audited. Every exploratory interval contains zero. Not evidence that any threshold works.
- **Cost.** $0.2215 fresh ($0.2927 including cached) for the whole pipeline (writing, evaluator checks, answering). Wall time 479 s.
- **Conclusion.** Memory helped on average (202 vs 189 correct; no interval computed for that comparison, and `all` was worse than `none` on 26 tasks). The audit did not measurably change accuracy. No evidence of benefit or harm at n=300.
- **Limitations.** Single seed (42). One dataset, one answering model. BANKING77 labels are largely lexical, so retrieved lessons help less than conversational recall. The CI covers sampling of held-out tasks, not run-to-run model nondeterminism or different seeds. Per-writer helped/harmed counts (careful 15/19, sloppy 17/15, qwen 18/14) show writers add about as much harm as help at the task level.
- **Artifacts.** [results.md](../backend/results/20261017-122228-stream-banking77/results.md), [summary.json](../backend/results/20261017-122228-stream-banking77/summary.json). Code: `833911b` (stream benchmark). The linked summary and results files are committed. Runtime output directories remain ignored by default.

## Experiment 5: Rusty Rod correctness suite (synthetic, held-out)

Design: [docs/benchmarks.md](benchmarks.md) "Custom BrainBob Suite" and [backend/SPEC-correctness.md](../backend/SPEC-correctness.md). 30 held-out scenarios (five per group: extraction, updates, retention, forgetting, shared handoff, insufficient evidence) plus 6 development scenarios, all synthetic, in [fixtures/rusty_rod/scenarios.json](../backend/fixtures/rusty_rod/scenarios.json). Updates scenario 1 is the Atlas commitment from [sample-company.md](sample-company.md). Expected answers, forbidden stale values and unreadable scopes were written before running. Grading is deterministic (string checks), not a model judge. The held-out split was run once; no prompt changed after it.

Answering and extraction: `nvidia/Nemotron-3.5-Lightning-30B-A3B`; maintenance and audit judge: `openai/gpt-oss-120b`. Top 10 retrieval over the asking member's readable scopes; every question uses a fresh agent.

| Condition | Accuracy | Stale-fact usage | Correct memory updates | Valid memories wrongly retired | Abstention | Uncertainty | Leakage |
|---|---|---|---|---|---|---|---|
| none | 10/76 | 0/24 | - | - | 9/10 | 0/3 | 0 |
| append_only | 67/76 | 4/24 | 0/13 | 0/32 | 7/10 | 1/3 | 0 |
| maintained, no audit | 68/76 | 1/24 | **12/13** | 0/32 | 7/10 | 0/3 | 0 |
| maintained + recent audit | 68/76 | 1/24 | 12/13 | 0/32 | 7/10 | 0/3 | 0 |
| full_history | 73/76 | 1/24 | - | - | 9/10 | 2/3 | 0 |

Paired bootstrap, 2000 resamples, percentage points:
- maintained (no audit) - append_only: accuracy +1.3 [-5.3, +7.9]; stale-fact usage -3.9 [-9.2, +0.0].
- maintained + audit - maintained (no audit): +0.0 on every metric. The recent audit changed no answer.
- append_only - none: accuracy +75.0 [+63.2, +85.5].
- Correct memory updates (13 update checks): maintained 12/13, append_only 0/13; all 12 discordant pairs favor maintained (exact McNemar p = 2 x 0.5^12, about 0.0005).

What this shows and what it does not:
- **Shown:** write-time maintenance keeps the current fact active and the superseded one retired (12/13 vs 0/13) without retiring any valid memory (0/32), and no retrieval crossed a scope the member cannot read (0 leaks; this is guaranteed by filtering before retrieval, not discovered by the run).
- **Not shown:** better answers. Accuracy gain over append-only is +1.3 points, not significant; the model usually picks the newer fact even when both are retrieved.
- **Weakness found:** insufficient-evidence questions. Maintained memory scored 6/12 in that group (append_only 8/12, full_history 11/12) and 0/3 on questions that should mention an unresolved conflict; the answering agent gave one value instead of naming the tentative alternative.
- **Full history wins here** (73/76) because these scenarios are tiny (about 88 context tokens). Memory's context advantage shows on long histories (Experiment 1), not here.
- **Recent audit:** coverage 13/13 is complete by construction (at most 8 episodes per scenario, sample of 10); judgment accuracy 193/194 on pairs the fixtures decide.
- **Grader limits:** three abstain answers worded "does not specify" or "do not contain information" were scored wrong, and one "has been dropped" sentence was counted as stale-fact usage. The rules were fixed before the held-out run and were not changed afterward.
- **Prompt change:** the extraction prompt was generalized (commit `21260c4`) between the development and held-out runs; the held-out run uses the new prompt throughout.
- Cost: held-out run $0.052 in fresh calls, 229 s. Artifacts: [results.md](../backend/results/20261017-131504-correctness-heldout/results.md), [summary.json](../backend/results/20261017-131504-correctness-heldout/summary.json).

## Experiment 6: Bob organizational pilot (proposed benchmark, synthetic)

Spec: [docs/bob-benchmark-spec.md](bob-benchmark-spec.md); contract: [bobbench/CONTRACT.md](../bobbench/CONTRACT.md). Six worlds (scoped assembly, authority corrections, cross-organization publication, membership and grants, conflict and retention, correction propagation), 41 checkpoints, hidden oracles v0.2, deterministic scorer, phrases-0.2. Every condition uses the same answering model (`nvidia/Nemotron-3.5-Lightning-30B-A3B`, temperature 0, thinking off) and the same answering prompt; BrainBob only decides the context. Three replicates; build `5fcd554`.

| Condition | Legitimate | Boundary | Maintenance | Macro CATS | Disclosures |
|---|---|---|---|---|---|
| no_memory | 0.0 | 58.3 | 16.7 | 25.0 | 0/111 |
| full_history (authorized sources) | 89.8 | 100.0 | 75.9 | 88.6 | 0/111 |
| append_only (BrainBob) | 55.6 | 100.0 | 46.3 | 67.3 | 0/111 |
| maintained (BrainBob) | 63.9 | 100.0 | 59.3 | 74.4 | 0/111 |
| always_refuse (control) | 0.0 | 58.3 | 16.7 | 25.0 | 0/111 |
| unfiltered (control) | 18.1 | 0.0 | 5.6 | 7.9 | 111/111 |

Paired bootstrap clustered by world (2000 draws): maintained - append_only +7.1 [-6.2, +21.6] macro; maintained - no_memory +49.4 [+23.1, +75.2]; full_history - append_only +21.3 [+6.3, +38.6]. The raw table lists five probe surfaces with zero detected leaks. The [adapter review](https://github.com/jerelvelarde/BrainBob/blob/373eee2e11891e43232ae509c1d7de9ae3567e3a/docs/bob-pilot-review-20261017.md) found that source/history returned empty response lists: only search, record, and events had actual responses (123 each per BrainBob condition). Source/history therefore remain untested in this run; export and session cache are unsupported. Rescoring saved answers does not add surface coverage or an existing-session revocation test. Per world, maintenance helped most on w1, w2 and w6 and lost on w3 maintenance (100 to 33.3). Labels are single-annotator, with subsequent scorer/oracle reviews but no independent human adjudication; oracle v0.2 changed forbidden checks after a baseline-only smoke run and before any BrainBob run (see the worlds changelog). Cost about $0.03 for the whole run. Artifacts: [scorecard.md](../bobbench/results/20261017-141014/scorecard.md), [scorecard.json](../bobbench/results/20261017-141014/scorecard.json), compressed traces.

**Corrected scores (v0.3), applied to the same saved answers with no new model calls:**

| Condition | Legitimate | Boundary | Maintenance | Macro CATS v0.3 | Macro v0.2 |
|---|---|---|---|---|---|
| no_memory | 0.0 | 58.3 | 16.7 | 25.0 | 25.0 |
| full_history | 92.6 | 100.0 | 83.3 | 92.0 | 88.6 |
| append_only | 55.6 | 100.0 | 48.1 | 67.9 | 67.3 |
| maintained | 63.9 | 100.0 | 51.9 | 71.9 | 74.4 |
| always_refuse | 0.0 | 58.3 | 16.7 | 25.0 | 25.0 |
| unfiltered | 13.9 | 0.0 | 5.6 | 6.5 | 7.9 |

v0.3 intervals: maintained - no_memory +46.9 [+22.7, +71.1]; maintained - append_only +4.0 [-9.0, +18.2]; full_history - append_only +24.1 [+9.4, +41.7]. v0.3 was made **after** seeing all v0.2 results, as a post-hoc correction; each change cites the review finding it fixes ([worlds changelog](https://github.com/jerelvelarde/BrainBob/blob/373eee2e11891e43232ae509c1d7de9ae3567e3a/bobbench/worlds/README.md), [v0.3 scorecard](../bobbench/results/20261017-141014/scorecard.v0.3.md)). Findings that need new requirements (some counterfactual pairs change more than one input; a sign and a delivery day not required; claim-level evidence) are listed as limitations, not fixed.

How the corrections came about: an independent read-only review of the scorer and oracles ([published scorer/oracle review](https://github.com/jerelvelarde/BrainBob/blob/373eee2e11891e43232ae509c1d7de9ae3567e3a/docs/scoring-review-codex.md)) found two high-severity false passes: a required date mentioned but not used as the answer (w2/cp-6, about -0.6 pts for maintained), and an oracle that missed a corrected filing deadline (w6/cp-6, about -1.9 pts for maintained and -0.6 for append_only), plus medium issues in phrase tables, historical mentions, failure detection and some counterfactual pairs. Aggregation and the bootstrap were found correct, and the no_memory / always_refuse tie is expected. The v0.3 table above is the result; the v0.2 numbers stay published.

## Experiment 7: Small memory-relation checker (issue #7, pair diagnostic)

Task: label (existing memory, new candidate) as same, conflict or unrelated. Jerel's frozen 60 public synthetic pairs (20 per label), scored with his `benchmarks/bob/benchmark.py` at `ab084a6`. This diagnostic is separate from the organizational pilot.

| Judge | Accuracy | Macro-F1 | Conflicts found (of 20) | Non-conflicts called conflict |
|---|---|---|---|---|
| Qwen3-0.6B base | 32/60 | 0.437 | 0 | 0 |
| Qwen3-0.6B + LoRA (adapter `Guangze/memops-small-qwen3-0.6b-lora@b904e6ec`) | 42/60 | 0.694 | 10 | 5 |
| `openai/gpt-oss-120b` (production judge) | 53/60 | 0.881 | 14 | 1 |
| `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B` (teacher) | 56/60 | 0.933 | 20 | 4 |

Tuned vs base: +16.7 pts, template-cluster 95% [+5.0, +28.3]. Training: 144 synthetic pairs from the Nemotron Super teacher (20 teacher labels corrected and 3 ambiguous pairs dropped by hand), LoRA r 16, 1 epoch, 9 steps, 8.6 s training time per run_meta.json, on one L4; total cost about $0.12. Recommendation: keep the tuned checker opt-in; it does not meet the issue's gate that harmful overwrites must not increase. The 60 pairs have now been inspected case by case, so any further tuning must be reported on a fresh frozen set. A second training round was prepared and then stopped, following the no-retraining scope of issues #6 and #7. Artifacts: [runs/20261017-210457](../experiments/memops-small/out/runs/20261017-210457/); public adapter and model card on the Hugging Face Hub.

## Experiment 8: Maintenance-judge comparison on the Bob pilot

Same six worlds and checkpoints, same answering model, prompt, extraction and budgets; only the maintenance relation judge changes. Six single-world Hugging Face Jobs runs at commit `d8c571e`, **one replicate each** (the full three-replicate job would have exceeded its timeout), merged by `bobbench/merge_runs.py`. Scorer 0.1, oracle v0.2.

| Maintenance judge | Legitimate | Boundary | Maintenance | Macro CATS | Retired | Judge errors |
|---|---|---|---|---|---|---|
| none (append_only) | 47.2 | 100.0 | 50.0 | 65.7 | 0 | n/a |
| `openai/gpt-oss-120b` (default) | 55.6 | 100.0 | 50.0 | 68.5 | 3 | 0/705 |
| `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B` | 55.6 | 100.0 | 44.4 | 66.7 | 4 | **111/675** |
| Qwen3-0.6B + LoRA `@b904e6ec` | 61.1 | 100.0 | 55.6 | 72.2 | 1 | 0/797 |
| Qwen3-0.6B base | 55.6 | 83.3 | 33.3 | 57.4 | 0 | 0/806 |

Rescored with v0.3, only append_only changes (65.7 to 63.9) and tuned vs the default judge is +3.7 [-11.1, +18.5] ([v0.3 scorecard](https://github.com/jerelvelarde/BrainBob/blob/373eee2e11891e43232ae509c1d7de9ae3567e3a/bobbench/results/20261017-judge-swap-merged/scorecard.v0.3.md)). v0.2 paired bootstrap vs the default judge: tuned +3.7 [-7.4, +17.6]; base -11.1 [-26.9, +8.3]; Nemotron Super -1.9 [-13.9, +8.3]; append_only -2.8 [-19.4, +13.9]. **No interval excludes zero.** The saved scorecard reports zero detected protected-string leaks for every condition; this is bounded probe evidence, not complete application security coverage. The Nemotron Super row is not a fair measure of that judge: 111 calls failed on Crusoe rate limits while six jobs ran in parallel, and failed calls fall back to the conservative tentative path. The tuned checker had a higher point estimate and the untuned checker the lowest point estimate, but these intervals establish neither improvement nor non-inferiority. It is not evidence for making the tuned checker the default. Artifacts: [scorecard.md](https://github.com/jerelvelarde/BrainBob/blob/373eee2e11891e43232ae509c1d7de9ae3567e3a/bobbench/results/20261017-judge-swap-merged/scorecard.md), [sources.json](https://github.com/jerelvelarde/BrainBob/blob/373eee2e11891e43232ae509c1d7de9ae3567e3a/bobbench/results/20261017-judge-swap-merged/sources.json).

## External benchmarks

GateMem (public data and code) was not run today: the official judge needs GPT-4o access and budget, and an application-equivalent adapter is not written. No public data or evaluator was found for MUMBench (AIM) or CoMemBench. Details and next steps: [external-benchmark-status.md](external-benchmark-status.md).

## Demo trace (selected example, not an evaluation)

[backend/demo/DEMO.md](../backend/demo/DEMO.md) is the repeatable live scenario for issue #2, with synthetic seed data marked `[synthetic demo data]`. A careless memory ("closes at 6 PM") makes a fresh agent answer wrong; leave-one-out feedback shows that removing it fixes the answer; review retires it after an uncached confirm re-run (default threshold of 3 flips, two of them recorded during seeding with real model calls); a useful memory from the same message ("48 hours' notice") is promoted, not retired; a different member then asks a different question and answers correctly with citations. It passed 15 checks in two cold-cache runs with identical answers: [run 1](../backend/results/20261017-131558-demo/meta.json), [run 2](../backend/results/20261017-131649-demo/meta.json). It is a chosen example, not a measurement of how often this happens.

## Provenance

| Experiment | Results folder | Code commit |
| --- | --- | --- |
| LongMemEval subset | `bench/results/20261017-110432` | `b86c109` (`bench/run.py`) |
| LoCoMo 10 conversations | `backend/results/20261017-112134-locomo` | `e2b4cf5` |
| LoCoMo noisy writer | `backend/results/20261017-113727-locomo` | `f308bab` |
| BANKING77 frozen-rule | `backend/results/20261017-122228-stream-banking77` | `833911b` (uncommitted edits to `backend/bench.py` made after that run touch only code after `stream_main`) |

Earlier report build: `21260c4`. Selected results and summaries under `backend/results/`, the LongMemEval results, and the original Bob pilot traces are committed; newly generated runtime results remain ignored by default.

| Additional evidence | Inference / implementation build | Scoring or evidence revision |
| --- | --- | --- |
| Bob organizational pilot | `5fcd554` | v0.3 scorer/oracle correction at `c241b6e`; [published artifacts](https://github.com/jerelvelarde/BrainBob/blob/373eee2e11891e43232ae509c1d7de9ae3567e3a/bobbench/results/20261017-141014/scorecard.v0.3.json) |
| Maintenance-judge comparison | `d8c571e` | v0.3 rescore at `c241b6e`; one replicate per world |
| Small-checker diagnostic | Frozen scorer `ab084a6`; adapter `b904e6ec0baea37bf70209093b8c59332d3c450a` | Saved predictions in Experiment 7 |
| Live company workspace | `348db5b`, `e77bb9a`, `489919b` | [Recorded observations and capture provenance](../judging/live-workspace-20261017/README.md); development evidence |

The v0.3 JSON is preserved verbatim, including raw fields that should not be interpreted as new measurements. In particular, missing legacy maintenance telemetry can appear as zeros or N/A, and empty source/history probes do not establish coverage.
