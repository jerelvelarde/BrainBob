# Safe mode for the tuned 0.6B checker (issue #6)

**Mode:** `confirm` (opt-in). `bridge.make_safe_judge(small_judge, confirm_judge, mode="confirm")`, with `confirm_judge` = the unchanged production judge (`maintain.llm_judge`). `observe` mode is also available: the small model is only logged and the production judge's answer is returned unchanged.

**Model:** `Guangze/memops-small-qwen3-0.6b-lora` @ `b904e6ec0baea37bf70209093b8c59332d3c450a`, base `Qwen/Qwen3-0.6B@c1899de289a04d12100db370d81485cdf75e47ca`. The production default judge is not changed; nothing uses the safe judge unless a caller passes it to `maintain.ingest(judge=...)`.

**Rules (confirm):** small `same`/`unrelated` is used as-is. Small `conflict` is returned only if the production judge also says `conflict`; otherwise `None` (tentative, nothing retired). Malformed output, exceptions, empty strings and unknown labels give `None`. Every call is recorded in `judge.log` as `{small, confirm, final}`.

**Evidence** (`backend/tests/test_memops_safe.py`, 23 passed; full `backend/tests` suite passes):
- `test_unsafe_baseline_retires_so_the_tests_are_meaningful`: the raw tuned judge retires an approved, unlocked memory.
- `test_five_false_conflicts_never_retire_in_confirm_mode`: the five saved tuned false conflicts (eval-007, 011, 015, 035, 048, from run 20261017-210457) through real `maintain.ingest`, approved/authorized/unlocked, with a confirm judge saying same or unrelated: 0 retirements, 0 supersedes.
- `test_malformed_output_never_replaces`, `test_bad_small_judge_return_values_never_replace`, `test_small_judge_exception_never_replaces`: garbage, empty, None and exceptions never replace, even when the confirm judge says conflict.
- `test_confirmed_conflict_still_replaces` (and `..._respects_locks`): confirmed conflicts still supersede, locks still hold.
- `test_observe_mode_equals_confirm_judge_alone`: observe mode matches the production judge exactly.

**Limitation:** this is a saved-response replay with a stand-in confirm judge, so it proves the wrapper cannot retire without confirmation, not that the real production judge confirms correctly; safety is only as good as that judge, and the tuned model's 42/60 accuracy is not a basis for unattended replacement.
