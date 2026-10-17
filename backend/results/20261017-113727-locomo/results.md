# LoCoMo + noisy writer (stress test) (20261017-113727-locomo)

Convs: ['conv-26', 'conv-30']; writers ['curator', 'curator_sloppy'] (sloppy temp 1.2); agent nvidia/Nemotron-3.5-Lightning-30B-A3B; heldout n=115, audit n=118, memories=708, flips=34.

| group | accuracy | avg ctx tokens (est.) | multi-hop | open-domain | single-hop | temporal |
|---|---|---|---|---|---|---|
| none | 11/115 (10%) | 0 | 1/21 (5%) | 1/6 (17%) | 9/57 (16%) | 0/31 (0%) |
| careful_only | 49/115 (43%) | 1271 | 6/21 (29%) | 3/6 (50%) | 32/57 (56%) | 8/31 (26%) |
| all | 56/115 (49%) | 1245 | 5/21 (24%) | 4/6 (67%) | 36/57 (63%) | 11/31 (35%) |
| audited_min3 | 56/115 (49%) | 1245 | 5/21 (24%) | 4/6 (67%) | 36/57 (63%) | 11/31 (35%) |
| audited_min2 | 56/115 (49%) | 1245 | 5/21 (24%) | 4/6 (67%) | 36/57 (63%) | 11/31 (35%) |
| audited_min1 | 59/115 (51%) | 1246 | 6/21 (29%) | 4/6 (67%) | 37/57 (65%) | 12/31 (39%) |

## Threshold (min_changes) -> retire / promote / flag

- min_changes=3: retired 0, promoted 0, flagged 0
- min_changes=2: retired 0, promoted 1, flagged 0
- min_changes=1: retired 7, promoted 21, flagged 0

## Author ledger (min_changes=3)

| author | written | helped | harmed | promoted | retired | flagged |
|---|---|---|---|---|---|---|
| curator | 319 | 18 | 8 | 0 | 0 | 0 |
| curator_sloppy | 389 | 5 | 3 | 0 | 0 | 0 |

## Author ledger (min_changes=2)

| author | written | helped | harmed | promoted | retired | flagged |
|---|---|---|---|---|---|---|
| curator | 319 | 18 | 8 | 1 | 0 | 0 |
| curator_sloppy | 389 | 5 | 3 | 0 | 0 | 0 |

## Author ledger (min_changes=1)

| author | written | helped | harmed | promoted | retired | flagged |
|---|---|---|---|---|---|---|
| curator | 319 | 18 | 8 | 16 | 5 | 0 |
| curator_sloppy | 389 | 5 | 3 | 5 | 2 | 0 |

Cost fresh $0.0687 (incl. cached $0.1468); wall 1006s.

| role | calls | cached | prompt tok | completion tok | USD fresh |
|---|---|---|---|---|---|
| curator | 114 | 114 | 104586 | 20046 | 0.0000 |
| curator_sloppy | 76 | 57 | 69724 | 23092 | 0.0022 |
| agent | 1052 | 492 | 1613997 | 37106 | 0.0524 |
| judge | 1052 | 733 | 247895 | 115615 | 0.0141 |

## Retired memories (min_changes=3)

## Retired memories (min_changes=2)

## Retired memories (min_changes=1)
- m42 (curator): Melanie believes sharing stories helps people realize they are not alone and can be inspiring to others. -- harmful on ['conv-26:q83']
- m140 (curator): Caroline painted a piece for the art show inspired by visiting an LGBTQ center, aiming to capture unity and strength. -- harmful on ['conv-26:q43']
- m263 (curator): Caroline is a trans woman who has been creating art since she was 17 and uses it to explore her gender identity. -- harmful on ['conv-26:q43']
- m296 (curator): Melanie's son was in a road trip accident this past weekend but is okay. -- harmful on ['conv-26:q135']
- m303 (curator): Melanie's family enjoyed the Grand Canyon during their road trip. -- harmful on ['conv-26:q147']
- m304 (curator_sloppy): Melanie's son was involved in an accident on a road trip this past weekend (past weekend relative to D18:5, calendar date 20-21 Oct 2023) -- harmful on ['conv-26:q135']
- m50 (curator_sloppy): Gina runs a clothing store and recently secured a wholesaler expansion. -- harmful on ['conv-30:q23']