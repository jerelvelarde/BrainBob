# Data review: synthetic memory pairs (issue #7)

Reviewer: Claude (coding agent), 2026-10-17, reading rows in the terminal. This is **not an independent human annotation**. Teacher labels (`nvidia/NVIDIA-Nemotron-3-Super-120B-A12B`) are provisional.

## What was generated

- 76 stories (63 train, 13 dev) × 3 candidates = 228 pairs. Story, template, entity, people, dates and the phenomenon for each label were frozen in `stories.json` before any wording existed.
- Split by template: 6 of the 42 templates appear only in dev (`dev_templates` in `manifest.json`). Dev uses its own company, entity and person pools, so no sibling that only differs by a name crosses the split.
- Each pair was labeled a second time, blind, by the same teacher at temperature 0 using the production judge prompt (`maintain.PROMPT`). 24 of 228 disagreed with the label the teacher had been asked to write. They are listed in `review_queue.jsonl`.
- The model input is Jerel's Bob benchmark format (`bob_format.py`), with ids `train-NNN` / `syn-NNN`, `m-NNN` and `s-NNN`. No Bob eval or dev input, and no `bobbench/` world or oracle, was read before the stories were written, or used for them. The test `test_training_rows_use_bob_format_and_never_bob_inputs` checks that no Bob text appears in the training data.

## Manual decisions (`label_overrides.json`, 23 entries)

| Change | Rows | Why |
| --- | --- | --- |
| `conflict` → `unrelated` | 20 (every `hedged_new_value` row, e.g. "X mentioned the price might move to $45") | A hedge does not assert a different current value. Both statements can be true at the same time, which is Bob's "same applicable time" rule. On these 20 rows the blind check said `unrelated` 15 times, `conflict` 4 times and gave unparseable output once. Labeling hedges `conflict` would also let an *approved* hedge supersede a valid memory. |
| dropped | `tr033-unrelated` | Scope is unclear: a Chicago office courier vs the company-wide courier. |
| dropped | `tr055-conflict` | An email launch and later social ads can coexist, so this is not a clean conflict. |
| dropped | `de007-conflict` | Both rows place the offsite at Redwood. The candidate only adds history. |

For the other unreviewed disagreements I judged the intended label right and the blind label wrong: `tr016` (Orchid vs the Orion project: different entities), `tr002`/`tr038` (last year's value is historical, not a conflict), `tr050`/`tr062` (no value stated). Balancing ranks agreed and reviewed rows first, so none of these made the final sets. Every final row either has teacher agreement (`label_source: teacher`) or a manual decision (`manual_review`: 10 train, 2 dev).

## Final sets

| Split | same | conflict | unrelated | total |
| --- | --- | --- | --- | --- |
| train | 50 | 44 | 50 | 144 |
| syn dev | 10 | 10 | 10 | 30 |

Conflict is 6 rows short of 50 because the hedges were moved to `unrelated`. I did not top it up: adding stories would change the seeded sequence for every later story.

## Spot check: 6 random training rows per label (seed 42)

- **same** (train-122, 018, 005, 045, 037, 035): all 6 labels are correct. Paraphrases and unit/format changes ("$1.2 million" vs "1.2 million dollars") are equivalent. train-035 cites a different person for the same value, which is still `same`. **Phenomenon tag mismatch:** train-037 is tagged `restated_negation` but neither sentence is negative.
- **conflict** (train-040, 031, 103, 029, 114, 089): all 6 are correct. Covered: explicit reversal ("will no longer serve as signatory"), date moved, owner changed, "as of this week updated to". train-089 is tagged `negation_reversal` but is a plain value change (2 h → 4 h).
- **unrelated** (train-004, 003, 013, 038, 039, 093): all 6 are correct. Covered: a different entity with near-identical wording (Harbor vs the Summit branch, minimum OS), a different attribute of the same entity, vague statements with no value, and the relabeled hedge train-003.

Result: 0 label errors in 18 sampled rows. 2 phenomenon tags are wrong. The tags come from the generation plan and the teacher did not always follow it, so use them only as rough strata, not as ground truth.

## Known weaknesses

- One teacher model wrote and checked the data, so its blind spots are shared. Sentences are 8–35 words and fairly templated ("X confirmed ... as of ...").
- Date order is randomized (about 15% of candidates are older than the existing memory). The semantic label ignores date order; staleness is decided in code.
- Hedge policy is our call. Bob dev contains no hedges, so it does not confirm or refute the policy.
