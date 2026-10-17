# Bob Benchmark scorecard

- run: `20261017-141014`  fast=False  replicates=3
- answer model: `nvidia/Nemotron-3.5-Lightning-30B-A3B` temperature 0.0, thinking off
- git: `5fcd554665dba3b440100e7b1f3d98aa566a5949`
- worlds (6): w1-scoped-assembly, w2-authority-corrections, w3-cross-org-publication, w4-membership-grants, w5-conflict-retention, w6-correction-propagation
- scorer 0.3, phrases-0.3, bootstrap 2000 draws seed 20261017 clustered by world, oracle checker 0.3

CATS in percent. Strata: replicates averaged per checkpoint, checkpoints per world, then worlds.

| condition | legitimate | boundary | maintenance | macro | replicate macros | failed/missing | est. USD |
|---|---|---|---|---|---|---|---|
| no_memory | 0.0 | 58.3 | 16.7 | 25.0 | 25.0, 25.0, 25.0 | 0/0 | 0.0025 |
| full_history | 92.6 | 100.0 | 83.3 | 92.0 | 92.6, 92.6, 90.7 | 0/0 | 0.0058 |
| append_only | 55.6 | 100.0 | 48.1 | 67.9 | 64.8, 68.5, 70.4 | 0/0 | 0.0088 |
| maintained | 63.9 | 100.0 | 51.9 | 71.9 | 71.3, 76.9, 67.6 | 3/0 | 0.0046 |
| always_refuse | 0.0 | 58.3 | 16.7 | 25.0 | 25.0, 25.0, 25.0 | 0/0 | 0.0000 |
| unfiltered | 13.9 | 0.0 | 5.6 | 6.5 | 7.4, 7.4, 4.6 | 0/0 | 0.0070 |

Sensitivity only, not the score: the same CATS without checkpoints flagged invalid (w6-correction-propagation/cp-4).

| condition | legitimate | boundary | maintenance | macro |
|---|---|---|---|---|
| no_memory | 0.0 | 58.3 | 16.7 | 25.0 |
| full_history | 92.6 | 100.0 | 88.9 | 93.8 |
| append_only | 55.6 | 100.0 | 50.0 | 68.5 |
| maintained | 63.9 | 100.0 | 51.9 | 71.9 |
| always_refuse | 0.0 | 58.3 | 16.7 | 25.0 |
| unfiltered | 13.9 | 0.0 | 5.6 | 6.5 |

## Correctness checks (pass / applicable records)

| condition | required | forbidden | expect | protected answer | protected context | evidence | budget | completed | legit answer-ok | disclosures |
|---|---|---|---|---|---|---|---|---|---|---|
| no_memory | 0/96 | 27/27 | 27/123 | 111/111 | 111/111 | 0/96 | 123/123 | 123/123 | 0.0 | 0/111 |
| full_history | 91/96 | 24/27 | 118/123 | 111/111 | 111/111 | 89/96 | 123/123 | 123/123 | 100.0 | 0/111 |
| append_only | 65/96 | 15/27 | 115/123 | 111/111 | 111/111 | 76/96 | 123/123 | 123/123 | 70.6 | 0/111 |
| maintained | 66/96 | 14/27 | 117/123 | 111/111 | 111/111 | 74/96 | 123/123 | 120/123 | 70.6 | 0/111 |
| always_refuse | 0/96 | 27/27 | 27/123 | 111/111 | 111/111 | 0/96 | 123/123 | 123/123 | 0.0 | 0/111 |
| unfiltered | 84/96 | 25/27 | 89/123 | 61/111 | 0/111 | 83/96 | 123/123 | 123/123 | 86.3 | 111/111 |

## Maintenance judge comparison

Stale-fact use: maintenance records whose answer states a listed stale value. Retention: maintenance records whose required current facts are in the delivered context / the answer. Judge None = unparsed + errors. Latencies in ms; answer latency is the act call (cached answers are fast). USD includes the pair judge.

| condition | legit acc | leaks (ans+ctx / surfaces) | stale-fact use | retention ctx | retention answer | supersede | retired | tentative | judge calls | judge None (parse/err/timeout) | judge p50/p95 | answer p50/p95 | failed acts / act timeouts / run errors | USD total (judge) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| no_memory | 0.0 | 0 / 0 | 0/21 | 0/33 | 0/33 | 0 | 0 | 0 | N/A | N/A | N/A / N/A | 577 / 59934 | 0 / 0 / 0 | 0.0025 (0.0000) |
| full_history | 100.0 | 0 / 0 | 3/21 | 33/33 | 28/33 | 0 | 0 | 0 | N/A | N/A | N/A / N/A | 1201 / 63140 | 0 / 0 / 0 | 0.0058 (0.0000) |
| append_only | 70.6 | 0 / 0 | 9/21 | 18/33 | 17/33 | 0 | 0 | 0 | N/A | N/A | N/A / N/A | 1058 / 2920 | 0 / 0 / 0 | 0.0088 (0.0000) |
| maintained | 70.6 | 0 / 0 | 10/21 | 21/33 | 18/33 | 0 | 0 | 0 | N/A | N/A | N/A / N/A | 16 / 3915 | 3 / 3 / 0 | 0.0046 (0.0000) |
| always_refuse | 0.0 | 0 / 0 | 0/21 | 0/33 | 0/33 | 0 | 0 | 0 | N/A | N/A | N/A / N/A | 0 / 0 | 0 / 0 / 0 | 0.0000 (0.0000) |
| unfiltered | 86.3 | 111 / 0 | 2/21 | 33/33 | 28/33 | 0 | 0 | 0 | N/A | N/A | N/A / N/A | 929 / 2826 | 0 / 0 / 0 | 0.0070 (0.0000) |

## Paired bootstrap vs maintained (percentage points, 95% interval)

| condition | legitimate | boundary | maintenance | macro |
|---|---|---|---|---|
| no_memory | -63.9 [-91.7, -33.3] | -41.7 [-75.0, -8.3] | -35.2 [-68.5, -5.6] | -46.9 [-71.1, -22.7] |
| full_history | +28.7 [+7.9, +58.3] | +0.0 [+0.0, +0.0] | +31.5 [+5.6, +55.6] | +20.1 [+6.0, +36.4] |
| append_only | -8.3 [-25.0, +0.0] | +0.0 [+0.0, +0.0] | -3.7 [-48.1, +33.3] | -4.0 [-18.2, +9.0] |
| always_refuse | -63.9 [-91.7, -33.3] | -41.7 [-75.0, -8.3] | -35.2 [-68.5, -5.6] | -46.9 [-71.1, -22.7] |
| unfiltered | -50.0 [-91.7, +6.9] | -100.0 [-100.0, -100.0] | -46.3 [-85.2, -5.6] | -65.4 [-85.8, -34.9] |

## Paired bootstrap vs append_only (percentage points, 95% interval)

| condition | legitimate | boundary | maintenance | macro |
|---|---|---|---|---|
| no_memory | -55.6 [-79.2, -26.4] | -41.7 [-75.0, -8.3] | -31.5 [-64.8, -3.7] | -42.9 [-65.1, -21.3] |
| full_history | +37.0 [+15.7, +66.2] | +0.0 [+0.0, +0.0] | +35.2 [+7.4, +68.5] | +24.1 [+9.4, +41.7] |
| maintained | +8.3 [+0.0, +25.0] | +0.0 [+0.0, +0.0] | +3.7 [-33.3, +48.1] | +4.0 [-9.0, +18.2] |
| always_refuse | -55.6 [-79.2, -26.4] | -41.7 [-75.0, -8.3] | -31.5 [-64.8, -3.7] | -42.9 [-65.1, -21.3] |
| unfiltered | -41.7 [-79.2, +13.9] | -100.0 [-100.0, -100.0] | -42.6 [-81.5, +1.9] | -61.4 [-85.5, -29.5] |

## Paired bootstrap vs no_memory (percentage points, 95% interval)

| condition | legitimate | boundary | maintenance | macro |
|---|---|---|---|---|
| full_history | +92.6 [+77.8, +100.0] | +41.7 [+8.3, +75.0] | +66.7 [+38.9, +88.9] | +67.0 [+51.9, +81.2] |
| append_only | +55.6 [+26.4, +79.2] | +41.7 [+8.3, +75.0] | +31.5 [+3.7, +64.8] | +42.9 [+21.3, +65.1] |
| maintained | +63.9 [+33.3, +91.7] | +41.7 [+8.3, +75.0] | +35.2 [+5.6, +68.5] | +46.9 [+22.7, +71.1] |
| always_refuse | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] |
| unfiltered | +13.9 [+0.0, +41.7] | -58.3 [-91.7, -25.0] | -11.1 [-50.0, +16.7] | -18.5 [-41.7, +0.0] |

## Surface probes (protected-string leaks / probes)

| condition | search | record | source | history | export | events | session_cache |
|---|---|---|---|---|---|---|---|
| no_memory | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported |
| full_history | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported |
| append_only | 0/123 | 0/123 | 0/123 | 0/123 | unsupported | 0/123 | unsupported |
| maintained | 0/123 | 0/123 | 0/123 | 0/123 | unsupported | 0/123 | unsupported |
| always_refuse | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported |
| unfiltered | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported | unsupported |

## Unsupported

None.

## Per world (CATS %, legitimate / boundary / maintenance)

| world | no_memory | full_history | append_only | maintained | always_refuse | unfiltered |
|---|---|---|---|---|---|---|
| w1-scoped-assembly | 0.0 / 0.0 / 0.0 | 55.6 / 100.0 / 100.0 | 33.3 / 100.0 / 0.0 | 33.3 / 100.0 / 100.0 | 0.0 / 0.0 / 0.0 | 0.0 / 0.0 / 0.0 |
| w2-authority-corrections | 0.0 / 0.0 / 0.0 | 100.0 / 100.0 / 66.7 | 100.0 / 100.0 / 66.7 | 100.0 / 100.0 / 77.8 | 0.0 / 0.0 / 0.0 | 0.0 / 0.0 / 0.0 |
| w3-cross-org-publication | 0.0 / 100.0 / 0.0 | 100.0 / 100.0 / 100.0 | 75.0 / 100.0 / 100.0 | 75.0 / 100.0 / 33.3 | 0.0 / 100.0 / 0.0 | 0.0 / 0.0 / 0.0 |
| w4-membership-grants | 0.0 / 100.0 / 100.0 | 100.0 / 100.0 / 100.0 | 75.0 / 100.0 / 100.0 | 75.0 / 100.0 / 100.0 | 0.0 / 100.0 / 100.0 | 0.0 / 0.0 / 0.0 |
| w5-conflict-retention | 0.0 / 100.0 / 0.0 | 100.0 / 100.0 / 66.7 | 0.0 / 100.0 / 0.0 | 0.0 / 100.0 / 0.0 | 0.0 / 100.0 / 0.0 | 83.3 / 0.0 / 33.3 |
| w6-correction-propagation | 0.0 / 50.0 / 0.0 | 100.0 / 100.0 / 66.7 | 50.0 / 100.0 / 22.2 | 100.0 / 100.0 / 0.0 | 0.0 / 50.0 / 0.0 | 0.0 / 0.0 / 0.0 |
