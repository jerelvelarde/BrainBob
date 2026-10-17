stream banking77  train=200 heldout=60 seed=42 memories=200 train_acc=119/200

heldout accuracy (top-8 memories per question)
  none                     39/60 (65%)  ctx~0tok
  all                      33/60 (55%)  ctx~586tok
  only_curator_careful     36/60 (60%)  ctx~440tok
  only_curator_sloppy      38/60 (63%)  ctx~712tok
  only_curator_qwen        36/60 (60%)  ctx~527tok
  audited_min3             33/60 (55%)  ctx~586tok
  audited_min2             33/60 (55%)  ctx~586tok
  audited_min1             35/60 (58%)  ctx~572tok

FLIPS total=26 | checks total=265 | memories=200 (checked at least once: 93)
  per memory: checks 1.32, flips 0.13 | per checked memory: checks 2.85, flips 0.28 | flip rate per check 9.8%

threshold   retired promoted
  min=3            0        0
  min=2            0        1
  min=1            8       11

author ledger (min_changes=3 / 1 for retired)
  author             written helped harmed retired@3 retired@1
  curator_careful         67      8      2         0         1
  curator_sloppy          67      3      8         0         6
  curator_qwen            66      3      2         0         1

cost fresh $0.0543 (incl cached $0.0735); wall 441s; C:\Users\16382\OneDrive\Desktop\BrainBob\backend\results\20261017-121234-stream-banking77