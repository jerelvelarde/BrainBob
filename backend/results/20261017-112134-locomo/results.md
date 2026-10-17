# BrainBob on LoCoMo (20261017-112134-locomo)

Convs: ['conv-26', 'conv-30', 'conv-41', 'conv-42', 'conv-43', 'conv-44', 'conv-47', 'conv-48', 'conv-49', 'conv-50']; agent model nvidia/Nemotron-3.5-Lightning-30B-A3B; heldout n=760, audit n=780, memories=2377, flips=267.

| group | accuracy | avg ctx tokens (est.) | multi-hop | open-domain | single-hop | temporal |
|---|---|---|---|---|---|---|
| none | 85/760 (11%) | 0 | 12/138 (9%) | 9/45 (20%) | 63/418 (15%) | 1/159 (1%) |
| all | 404/760 (53%) | 1199 | 48/138 (35%) | 20/45 (44%) | 292/418 (70%) | 44/159 (28%) |
| audited | 404/760 (53%) | 1199 | 48/138 (35%) | 20/45 (44%) | 292/418 (70%) | 44/159 (28%) |

Retired 0, promoted 2, flagged 0. Author ledger: {'curator.written': 2377, 'curator.promoted': 2, 'curator.retired': 0, 'curator.flagged': 0, 'curator.harm_changes': 54}

Cost fresh $0.3701 (incl. cached $0.5229); wall 524s.

| role | calls | cached | prompt tok | completion tok | USD fresh |
|---|---|---|---|---|---|
| curator | 544 | 310 | 504298 | 94098 | 0.0189 |
| agent | 4193 | 934 | 5819423 | 145938 | 0.2445 |
| judge | 4193 | 1410 | 999475 | 434961 | 0.1067 |

## Retired memories