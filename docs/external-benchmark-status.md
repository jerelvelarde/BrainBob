# External Benchmark Status: GateMem, MUMBench, CoMemBench

Status date and verification date: 2026-10-17 (Pacific). Every source below was fetched on 2026-10-17. Nothing was downloaded, installed, or run.

## 1. Scope

- Bob's own results (the Bob benchmark and the LoCoMo / LongMemEval / BANKING77 / Rusty Rod runs) are in [evaluation-report.md](evaluation-report.md) and in `bobbench/` (see [bobbench/CONTRACT.md](../bobbench/CONTRACT.md); proposal in [bob-benchmark-spec.md](bob-benchmark-spec.md), section 2 covers how these three relate to Bob).
- This document covers only the three external benchmarks: GateMem, MUMBench (from the AIM paper), and CoMemBench.
- Decision today: GateMem is not run. MUMBench and CoMemBench have no runnable official data that we could find. **No external benchmark was run today and no score from any of them is reported here.**

Access status vocabulary: **Available** (public data and scoring code found), **Not found** (no public data or code found at the cited sources), **Restricted** (exists but gated).

## 2. GateMem

**Sources (verified 2026-10-17)**
- Paper: https://arxiv.org/abs/2606.18829 (HTML: https://arxiv.org/html/2606.18829), submitted 2026-06-17.
- Code: https://github.com/rzhub/GateMem
- Data: https://huggingface.co/datasets/Ray368/GateMem

**What it measures.** Memory governance for shared assistants with several principals: utility on long-horizon requests with state updates, access control across authorization boundaries, and active forgetting after deletion requests. Domains: medical, office, education, household.

**Official data, scripts, scoring**
- Data: 91 episodes, 2,218 checkpoints (education 30 / 540, household 23 / 552, medical 21 / 579, office 17 / 547), per paper Table 2 and the HF dataset card. HF reports 2,309 rows and 7.14 MB; the row count differs from the checkpoint count and we have not inspected why. License on the dataset card: CC BY 4.0. Code license: MIT (GitHub). No gating mentioned on HF.
- Scripts: `bench/scripts/run_eval.py`; scoring and packaging commands are documented in `docs/prediction_format.md` (not yet read). Data is also in the repo under `bench/data/<domain>/`.
- Scoring: primary results are computed from GPT-4o judge labels (paper section 4.1); the README example uses gpt-4o as judge and gpt-4o-mini as answerer. Metrics: effective utility U, access-control violation rate A, forgetting failure rate F, and MGS = U x (1 - A) x (1 - F) (paper section 3.3). Human validation in the paper: max absolute difference 1.04 points, at least 97.7% field-level agreement. Submissions must use the "official LLM judge configuration" (details in `docs/prediction_format.md`, not yet read).
- Rules: methods must not use the hidden fields `query_type`, `expected_action`, `judge_spec`, `leak_targets`.
- Leaderboard: upload `submission.zip` to the GateMem-Submit HF Space; results are listed as Community, or Verified after maintainers re-score.

**Access status: Available.**

**Adapter BrainBob would need.** A full-application adapter, not a prompt wrapper. Each GateMem episode must be replayed through the real BrainBob pipeline: principals map to BrainBob users, writes go through the normal memory-write and maintenance path, deletion requests must trigger real forgetting (including derived summaries), and every checkpoint query must be answered with retrieval filtered by the requesting principal's permissions. The system must not read the hidden fields. An append-only memory plus a "do not reveal other users' data" prompt would measure the prompt, not BrainBob, and is not acceptable as our entry. Open design item: GateMem's official agent interface is not yet read, so how a principal and the authorization boundary are passed to a custom agent is unconfirmed.

**Cost and time to run once (estimate, not measured).** The paper reports tokens and wall-clock only, no dollars: Long-Context about 4.04k tokens and 4.22 s per checkpoint (GPT-4o-mini, Medical). Rough scale for one full pass over 2,218 checkpoints: answering on our own Crusoe-hosted model, plus roughly 2,200 GPT-4o judge calls. Our estimate for the judge portion is about $5 to $15 (assuming roughly 1k to 3k judge tokens per checkpoint at current GPT-4o list prices; prices and token counts not verified). Wall time is not estimated: ingestion through the real BrainBob write path is the unknown, and the paper notes memory-system baselines reaching 100 to 260 s per checkpoint.

**Exact blocker.** Not data access. Two things: (1) no OpenAI API key with GPT-4o access and no budget approval, so the official judge cannot be run; (2) the BrainBob adapter above is not written. Switching to a different judge would make the number non-comparable and not eligible for the leaderboard.

**Next step needed.** A key that can call GPT-4o and approval of a $5 to $15 budget; then read `docs/prediction_format.md`, write the full-application adapter, and do a one-domain (Medical, 579 checkpoints) trial before any full run.

## 3. MUMBench (AIM paper)

**Sources (verified 2026-10-17)**
- Paper: AIM, https://arxiv.org/abs/2609.12320 (HTML: https://arxiv.org/html/2609.12320v1), 2026-09-11. Paper license CC BY 4.0.

**What it measures.** Multi-user memory operations (CREATE / READ / UPDATE / DELETE / NOOP) with private versus public visibility, over four domains (coding, customer support, education, travel planning). Per the prior notes (`_notes/related-benchmarks.md`, read from the paper): 672 time-ordered interactions, 93 users, 205 unique memories, 60 adversarial queries; synthesized with GPT-4o then human-checked. Metrics: visibility match, strict operation accuracy, state-aware operation accuracy, with an LLM judge (gpt-4.1-mini) as fallback. These details come from the paper text and were not re-fetched in full today.

**Official data, scripts, scoring.** The arXiv page offers only PDF, HTML, TeX source and DOI. It contains no link to code, a repository, or the MUMBench dataset. The abstract calls MUMBench "the first public dataset" but gives no location. The earlier survey also found no repository or dataset. No evaluation script was found.

**Access status: Not found.** (We have not asked the authors; that is the first untried route.)

**Adapter BrainBob would need.** One that replays the interaction stream through the real application with per-user identity, emits CRUD/NOOP operations from the actual memory pipeline (not from a prompt that merely asks the model to output an operation label), and enforces private/public visibility at retrieval. Note MUMBench has only two visibility levels, so it would exercise a small part of BrainBob's permissions, and has no forgetting-propagation or revision-authority semantics.

**Cost and time.** Cannot be estimated reliably without the official evaluation protocol. The set is small (672 interactions), so it would likely be cheap, but this is unverified.

**Exact blocker.** No public dataset or evaluation script exists at any location we could find. Re-creating "MUMBench-like" data from the paper's description would be a synthetic imitation, not the benchmark.

**Next step needed.** Email the AIM authors (corresponding authors listed on the arXiv page) asking whether the data and scripts will be released. Re-check arXiv versions and GitHub for a release before the final submission. Until then, status stays "Not found".

## 4. CoMemBench

**Sources (verified 2026-10-17)**
- Paper: https://arxiv.org/abs/2609.32192 (v2 per our earlier survey), cs.AI. Paper license CC BY 4.0, which covers the paper and not necessarily any code or data.

**What it measures.** How multi-agent workflows share information between agents while isolating stale, unverified, or irrelevant information. 800 composite workflows across four domains, built from source-grounded dependency graphs; metrics are workflow completion, verified node progress, handoff reliability, isolation robustness, and token cost.

**Official data, scripts, scoring.** The arXiv page links no code, data, or evaluator. The abstract mentions "native evaluators" but not where to get them. We found no oracle, no repository, and no dataset. Whether scoring is deterministic or LLM-based is not stated on the page we read.

**Access status: Not found.**

**Adapter BrainBob would need.** A multi-agent workflow adapter: each workflow node is an agent step reading and writing BrainBob memory, with the real permission and revision mechanisms deciding what crosses a node boundary and what is isolated as stale. A shared append-only store plus a "do not use stale info" instruction would be only a baseline. This benchmark tests workflow topologies, which BrainBob does not currently model as a first-class concept; an adapter would need design work before it is even specified.

**Cost and time.** Cannot be estimated: 800 multi-agent workflows with unknown size, and no evaluator to inspect.

**Exact blocker.** No released data, code, or evaluator found. The paper is two to three weeks old as of today.

**Next step needed.** Email the authors asking for the benchmark and evaluators; re-check arXiv and GitHub periodically. Do not start adapter work before there is something to run it against.

## 5. Summary

| Benchmark | Access status | Run today? | Blocker | Next step |
| --- | --- | --- | --- | --- |
| GateMem | Available (data CC BY 4.0, code MIT) | No | No GPT-4o key or budget approval for the official judge; full-application adapter not written | Get a GPT-4o key and approval for an estimated $5 to $15; read `docs/prediction_format.md`; build adapter; trial on Medical first |
| MUMBench (AIM) | Not found | No | No public dataset or evaluation script linked from the paper | Email AIM authors; re-check for a release |
| CoMemBench | Not found | No | No public code, data, or evaluators linked from the paper | Email authors; re-check for a release; no adapter work until data exists |

## 6. What we do not claim

- We report no score on GateMem, MUMBench, or CoMemBench. None was run.
- We do not use synthetic imitations (for example, data written by us "in the style of" MUMBench or CoMemBench, or a hand-built subset of GateMem) as a stand-in, and we do not present Bob results as if they were results on these benchmarks.
- We do not claim any comparison with the published numbers of these benchmarks. Bob's LongMemEval run already uses a non-official judge and subset (see evaluation-report.md); the same caution applies to anything we might run later.
- "Available" for GateMem means the data and scripts are public; it does not mean BrainBob has been tested on it, and the cost figure above is an estimate.
- Details taken from earlier notes rather than re-fetched today (MUMBench dataset size and metrics, GateMem baseline tables) should be rechecked against the papers before being quoted.
