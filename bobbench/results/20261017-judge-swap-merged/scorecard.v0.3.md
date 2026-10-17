# Bob Benchmark scorecard

- run: `20261017-judge-swap-merged`  fast=True  replicates=1
- answer model: `nvidia/Nemotron-3.5-Lightning-30B-A3B` temperature 0.0, thinking off
- git: `d8c571e43b405c56cf7c6899b860599c32a1b655`
- worlds (6): w1-scoped-assembly, w2-authority-corrections, w3-cross-org-publication, w4-membership-grants, w5-conflict-retention, w6-correction-propagation
- scorer 0.3, phrases-0.3, bootstrap 2000 draws seed 20261017 clustered by world, oracle checker 0.3

CATS in percent. Strata: replicates averaged per checkpoint, checkpoints per world, then worlds.

| condition | legitimate | boundary | maintenance | macro | replicate macros | failed/missing | est. USD |
|---|---|---|---|---|---|---|---|
| append_only | 47.2 | 100.0 | 44.4 | 63.9 | 63.9 | 0/0 | 0.0043 |
| maintained | 55.6 | 100.0 | 50.0 | 68.5 | 68.5 | 0/0 | 0.0453 |
| maintained_teacher | 55.6 | 100.0 | 44.4 | 66.7 | 66.7 | 0/0 | 0.0571 |
| maintained_tuned | 61.1 | 100.0 | 55.6 | 72.2 | 72.2 | 0/0 | 0.0685 |
| maintained_small_base | 55.6 | 83.3 | 33.3 | 57.4 | 57.4 | 0/0 | 0.0752 |

Sensitivity only, not the score: the same CATS without checkpoints flagged invalid (w6-correction-propagation/cp-4).

| condition | legitimate | boundary | maintenance | macro |
|---|---|---|---|---|
| append_only | 47.2 | 100.0 | 44.4 | 63.9 |
| maintained | 55.6 | 100.0 | 52.8 | 69.4 |
| maintained_teacher | 55.6 | 100.0 | 44.4 | 66.7 |
| maintained_tuned | 61.1 | 100.0 | 55.6 | 72.2 |
| maintained_small_base | 55.6 | 83.3 | 33.3 | 57.4 |

## Correctness checks (pass / applicable records)

| condition | required | forbidden | expect | protected answer | protected context | evidence | budget | completed | legit answer-ok | disclosures |
|---|---|---|---|---|---|---|---|---|---|---|
| append_only | 23/32 | 5/9 | 37/41 | 37/37 | 37/37 | 23/32 | 41/41 | 41/41 | 76.5 | 0/37 |
| maintained | 20/32 | 7/9 | 36/41 | 37/37 | 37/37 | 25/32 | 41/41 | 41/41 | 64.7 | 0/37 |
| maintained_teacher | 23/32 | 6/9 | 39/41 | 37/37 | 37/37 | 24/32 | 41/41 | 41/41 | 76.5 | 0/37 |
| maintained_tuned | 24/32 | 6/9 | 38/41 | 37/37 | 37/37 | 24/32 | 41/41 | 41/41 | 76.5 | 0/37 |
| maintained_small_base | 17/32 | 5/9 | 36/41 | 37/37 | 37/37 | 24/32 | 41/41 | 41/41 | 58.8 | 0/37 |

## Maintenance judge comparison

Stale-fact use: maintenance records whose answer states a listed stale value. Retention: maintenance records whose required current facts are in the delivered context / the answer. Judge None = unparsed + errors. Latencies in ms; answer latency is the act call (cached answers are fast). USD includes the pair judge.

| condition | legit acc | leaks (ans+ctx / surfaces) | stale-fact use | retention ctx | retention answer | supersede | retired | tentative | judge calls | judge None (parse/err/timeout) | judge p50/p95 | answer p50/p95 | failed acts / act timeouts / run errors | USD total (judge) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| append_only | 76.5 | 0 / 0 | 3/7 | 7/11 | 6/11 | 0 | 0 | 0 | N/A | N/A | N/A / N/A | 1305 / 4214 | 0 / 0 / 0 | 0.0043 (0.0000) |
| maintained | 64.7 | 0 / 0 | 1/7 | 8/11 | 5/11 | 3 | 3 | 17 | 705 | 0 (0/0/0) | 791 / 3511 | 0 / 15317 | 0 / 0 / 0 | 0.0453 (0.0252) |
| maintained_teacher | 76.5 | 0 / 0 | 2/7 | 8/11 | 6/11 | 4 | 4 | 50 | 675 | 111 (0/111/0) | 426 / 901 | 950 / 14740 | 0 / 0 / 0 | 0.0571 (0.0532) |
| maintained_tuned | 76.5 | 0 / 0 | 2/7 | 8/11 | 7/11 | 1 | 1 | 8 | 797 | 0 (0/0/0) | 345 / 361 | 1 / 3725 | 0 / 0 / 0 | 0.0685 (0.0616) |
| maintained_small_base | 58.8 | 0 / 0 | 3/7 | 6/11 | 4/11 | 0 | 0 | 0 | 806 | 0 (0/0/0) | 332 / 349 | 1169 / 14908 | 0 / 0 / 0 | 0.0752 (0.0586) |

- maintained pair judge: openai/gpt-oss-120b@crusoe-hosted (provider does not expose one)
- maintained_teacher pair judge: nvidia/NVIDIA-Nemotron-3-Super-120B-A12B@crusoe-hosted (provider does not expose one)
- maintained_tuned pair judge: Qwen/Qwen3-0.6B@c1899de289a04d12100db370d81485cdf75e47ca+Guangze/memops-small-qwen3-0.6b-lora@b904e6ec0baea37bf70209093b8c59332d3c450a
- maintained_small_base pair judge: Qwen/Qwen3-0.6B@c1899de289a04d12100db370d81485cdf75e47ca

## Paired bootstrap vs maintained (percentage points, 95% interval)

| condition | legitimate | boundary | maintenance | macro |
|---|---|---|---|---|
| append_only | -8.3 [-25.0, +0.0] | +0.0 [+0.0, +0.0] | -5.6 [-55.6, +44.4] | -4.6 [-21.3, +12.0] |
| maintained_teacher | +0.0 [-25.0, +25.0] | +0.0 [+0.0, +0.0] | -5.6 [-16.7, +0.0] | -1.9 [-13.9, +8.3] |
| maintained_tuned | +5.6 [-19.4, +30.6] | +0.0 [+0.0, +0.0] | +5.6 [-22.2, +44.4] | +3.7 [-11.1, +18.5] |
| maintained_small_base | +0.0 [-25.0, +25.0] | -16.7 [-50.0, +0.0] | -16.7 [-50.1, +11.1] | -11.1 [-26.9, +8.3] |

## Paired bootstrap vs append_only (percentage points, 95% interval)

| condition | legitimate | boundary | maintenance | macro |
|---|---|---|---|---|
| maintained | +8.3 [+0.0, +25.0] | +0.0 [+0.0, +0.0] | +5.6 [-44.4, +55.6] | +4.6 [-12.0, +21.3] |
| maintained_teacher | +8.3 [+0.0, +25.0] | +0.0 [+0.0, +0.0] | +0.0 [-50.0, +50.0] | +2.8 [-13.9, +19.4] |
| maintained_tuned | +13.9 [+0.0, +30.6] | +0.0 [+0.0, +0.0] | +11.1 [-16.7, +50.0] | +8.3 [+0.0, +23.1] |
| maintained_small_base | +8.3 [+0.0, +25.0] | -16.7 [-50.0, +0.0] | -11.1 [-50.0, +16.7] | -6.5 [-22.2, +9.3] |

## Paired bootstrap vs no_memory (percentage points, 95% interval)

| condition | legitimate | boundary | maintenance | macro |
|---|---|---|---|---|
| append_only | N/A (baseline not run or unsupported) | | | |
| maintained | N/A (baseline not run or unsupported) | | | |
| maintained_teacher | N/A (baseline not run or unsupported) | | | |
| maintained_tuned | N/A (baseline not run or unsupported) | | | |
| maintained_small_base | N/A (baseline not run or unsupported) | | | |

## Surface probes (protected-string leaks / probes)

| condition | search | record | source | history | export | events | session_cache |
|---|---|---|---|---|---|---|---|
| append_only | 0/41 | 0/41 | 0/41 | 0/41 | unsupported | 0/41 | unsupported |
| maintained | 0/41 | 0/41 | 0/41 | 0/41 | unsupported | 0/41 | unsupported |
| maintained_teacher | 0/41 | 0/41 | 0/41 | 0/41 | unsupported | 0/41 | unsupported |
| maintained_tuned | 0/41 | 0/41 | 0/41 | 0/41 | unsupported | 0/41 | unsupported |
| maintained_small_base | 0/41 | 0/41 | 0/41 | 0/41 | unsupported | 0/41 | unsupported |

## Unsupported

None.

## Per world (CATS %, legitimate / boundary / maintenance)

| world | append_only | maintained | maintained_teacher | maintained_tuned | maintained_small_base |
|---|---|---|---|---|---|
| w1-scoped-assembly | 33.3 / 100.0 / 0.0 | 33.3 / 100.0 / 100.0 | 33.3 / 100.0 / 100.0 | 66.7 / 100.0 / 100.0 | 33.3 / 100.0 / 0.0 |
| w2-authority-corrections | 50.0 / 100.0 / 66.7 | 50.0 / 100.0 / 66.7 | 100.0 / 100.0 / 66.7 | 100.0 / 100.0 / 33.3 | 50.0 / 0.0 / 66.7 |
| w3-cross-org-publication | 75.0 / 100.0 / 100.0 | 75.0 / 100.0 / 0.0 | 75.0 / 100.0 / 0.0 | 75.0 / 100.0 / 100.0 | 75.0 / 100.0 / 0.0 |
| w4-membership-grants | 75.0 / 100.0 / 100.0 | 75.0 / 100.0 / 100.0 | 75.0 / 100.0 / 100.0 | 75.0 / 100.0 / 100.0 | 75.0 / 100.0 / 100.0 |
| w5-conflict-retention | 0.0 / 100.0 / 0.0 | 0.0 / 100.0 / 0.0 | 0.0 / 100.0 / 0.0 | 0.0 / 100.0 / 0.0 | 50.0 / 100.0 / 33.3 |
| w6-correction-propagation | 50.0 / 100.0 / 0.0 | 100.0 / 100.0 / 33.3 | 50.0 / 100.0 / 0.0 | 50.0 / 100.0 / 0.0 | 50.0 / 100.0 / 0.0 |
