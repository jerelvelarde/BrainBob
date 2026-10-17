stream banking77  train=600 heldout=300 seed=42 memories=600 batch=25 train_acc=364/600

heldout accuracy (top-8 memories per question)
  none                     189/300 (63%)  ctx~0tok
  all                      202/300 (67%)  ctx~547tok
  only_curator_careful     179/300 (60%)  ctx~481tok
  only_curator_sloppy      176/300 (59%)  ctx~621tok
  only_curator_qwen        191/300 (64%)  ctx~506tok
  audited_min3             202/300 (67%)  ctx~544tok
  audited_min2             203/300 (68%)  ctx~543tok
  audited_min1             203/300 (68%)  ctx~542tok
  audited_author           203/300 (68%)  ctx~543tok

MAIN METRIC: audited minus all (paired bootstrap 95% CI, 2000 resamples, same heldout tasks)
  audited_min3 - all : +0.0 pts  [-1.3, +1.3]
  audited_min2 - all : +0.3 pts  [-2.0, +2.3]
  audited_min1 - all : +0.3 pts  [-3.0, +3.7]
  audited_author - all : +0.3 pts  [-3.0, +3.7]
  audited_author - none: +4.7 pts  [-0.3, +9.3]  (probation retired 0: {})
  diagnosis (memories retired at min=1: 28): heldout tasks retrieving one: 248, citing one: 68; accuracy on retrieving tasks all 162/248 vs audited 163/248; on citing tasks all 41/68 vs audited 41/68
  all worse than none on 26 heldout tasks (memory hurt overall if > better)

FLIPS total=98 | checks total=833 | memories=600 (checked at least once: 236)
  per memory: checks 1.39, flips 0.16 | per checked memory: checks 3.53, flips 0.42 | flip rate per check 11.8%

threshold   retired promoted
  min=3            3        2
  min=2            6        5
  min=1           28       38
  min=1+prob      30       38

author ledger (min_changes=3 / 1 for retired)
  author             written helped harmed retired@3 retired@1
  curator_careful        200     15     19         1        12
  curator_sloppy         200     17     15         0         9
  curator_qwen           200     18     14         2         7

cost fresh $0.2215 (incl cached $0.2927); wall 479s; C:\Users\16382\OneDrive\Desktop\BrainBob\backend\results\20261017-122228-stream-banking77