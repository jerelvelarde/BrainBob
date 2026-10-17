# BrainBob Backend Design

Owner: Bonan (backend and benchmarks). Frontend: Jerel. Written during the event on 2026-10-17.
Interfaces: [backend/CONTRACT.md](../backend/CONTRACT.md). Frontend integration: [backend/FRONTEND.md](../backend/FRONTEND.md).

## Decisions (11:30 PT)

| Topic | Decision |
| --- | --- |
| Language | Python 3.12. The frontend talks to it only over HTTP and SSE (port 3001). |
| Evaluator | **Change and observe** replaces the random 10-of-50 audit with LLM evidence judging. One mechanism, explained in one sentence. |
| Scope | Planner, HTML alignment, NemoClaw sandboxes and Switchyard routing are out of the scored loop for now. Model choice stays behind `llm.complete(role, ...)`, so routing can be added there later without touching other modules. |
| Inference | Crusoe Managed Inference only. Curator and agent: `nvidia/Nemotron-3.5-Lightning-30B-A3B`. Judge: `openai/gpt-oss-120b` (a different model family from the agent). |
| Shape | Task-agnostic core, deep modules, shallow interfaces. A task brings only its episodes and a `grade(answer) -> bool`. |

## The Loop

```
write:  Episode --curator--> memory.add            (dedupe and tombstones in code)
read:   Task --memory.search--> agent.answer --> answer + cited memory ids
audit:  evaluator drops each cited memory, re-answers, grades both answers.
        If correctness flips, the memory and its author get the credit or the blame.
        review: promote / retire (locked memories are only flagged for their owner)
```

## Evaluator: Change and Observe

We do not ask a model whether a memory is good. We change the input and watch the result.

- Every memory has an id, an author (role or model that wrote it), an origin episode, and a status: `trial`, `promoted`, `retired` or `locked`.
- **Default strategy, leave-one-out:** answer with all retrieved memories, then answer again without one cited memory. If the two answers differ in correctness, record evidence.
- Other strategies behind the same interface: paired runs on a sample of tasks, or hiding a random half of trial memories (no extra calls, needs more tasks).
- All evidence uses one format: `(memory_id, shown, correct, task_id)`. The ledger reads only this format.
- **Decision rule:** after at least 3 flips, more harmful flips than helpful ones retires the memory; more helpful flips promotes it. Before retiring, the memory is removed and the task re-run once to confirm.
- **Author ledger:** memories written, promoted and retired per author.
- **Tombstones:** new memories too similar to a retired one are rejected in code, not by prompt.
- Only flips count. "Cited but the answer did not change" is too noisy to use.
- **Known limit:** a wrong memory that matches what the model would have said anyway never flips an answer, so this method cannot see it.

Motivation: a pre-event prototype on a synthetic help desk (not a hackathon result; none of its code is reused) scored 61.3% with no memory, 63.8% keeping every memory, and 70.8% with audited memory on 240 held-out tickets. Shared memory alone barely helped; auditing it did.

## Why Multiple Models

A shared brain has many writers. In a real team, agents run on different models: cheap, fast models for bulk work that make more mistakes, and stronger models for hard work, often from more than one vendor. They all write to the same memory, so the question is whose memories to trust.

- **Author ledger:** every memory records its author (role or model). The ledger shows, by measured results, which writer's memories get promoted and which get retired.
- **Write cheap, verify by results:** cheap models can write memories because harmful ones are caught and retired.
- **Independent judge:** grading uses a model from a different family than the answering agent.

Roles today: curator (writes memories) and agent (answers) use Lightning; the judge uses gpt-oss. A careless teammate (Nano, thinking off, high temperature) is being added as a second writer for the stress test below.

Demo line: *Anyone on the team can write to the shared brain. BrainBob checks every memory by its results and tells you which agent's and which model's memories you can trust.*

## Avoiding Leakage

- Gold answers are used only inside `Task.grade` as a right or wrong signal. Nothing derived from a gold answer is written to memory.
- Auditing must happen on tasks that share memory with the tasks we score, and the scored tasks must be held out.
- **LongMemEval** gives every question its own history, so auditing there would grade a question with its own answer. We use it only to compare full history against extracted memory.
- **LoCoMo** has 10 long conversations with about 200 questions each that share one memory. We split each conversation's questions by category (seed 42): 780 audit, 760 held out, adversarial category excluded.

## Benchmarks

| Experiment | Conditions | Status |
| --- | --- | --- |
| LongMemEval subset (50 stratified questions, `longmemeval_s_cleaned`) | full history vs extracted memory | **Measured.** See below. |
| LoCoMo, held-out half | no memory / all memories / audited memories | **Measured.** Audit had no effect yet; see below. |

LongMemEval subset, answered by `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B`, judged by `openai/gpt-oss-120b` with the official per-type judge prompts (the official setup uses GPT-4o):

| Condition | Accuracy | Context tokens per question |
| --- | --- | --- |
| Full history | 39/50 (78%) | 108,946 |
| Extracted memory, no audit | 35/50 (70%) | 2,681 |

About 1/40 of the context for 8 points lower accuracy. With 50 questions this gap is within noise. Total cost $2.30. Raw outputs: [bench/results/20261017-110432](../bench/results/20261017-110432/results.md). This is a LongMemEval subset, not a leaderboard score.

LoCoMo, all 10 conversations, 760 held-out questions, agent `nvidia/Nemotron-3.5-Lightning-30B-A3B` (thinking off), judge `openai/gpt-oss-120b`:

| Condition | Accuracy | Context tokens per question (estimated) |
| --- | --- | --- |
| No memory | 85/760 (11%) | 0 |
| All memories | 404/760 (53%) | 1,199 |
| Audited memories | 404/760 (53%) | 1,199 |

The audit saw 267 correctness flips on 780 audit questions: 213 helpful, 54 harmful, spread over 2,377 memories. No memory reached the 3-flip threshold, so nothing was retired and the audited condition equals the all-memories condition. LoCoMo has one clean writer, so its extracted memories are mostly correct. Cost $0.37, 524 s. Raw outputs: [backend/results/20261017-112134-locomo](../backend/results/20261017-112134-locomo/results.md).

### Findings So Far

1. **Memory is far cheaper than full history.** On the LongMemEval subset, extracted memory used about 1/40 of the context for 8 points lower accuracy (within noise at n=50).
2. **Memory is far better than none.** On LoCoMo, retrieved memories lifted held-out accuracy from 11% to 53%.
3. **On clean data the audit has nothing to remove.** With one careful writer, 213 of 267 flips were helpful. The 54 harmful flips were spread about one per memory, below the 3-flip threshold.
4. **So the audit's value depends on bad writers**, which is the Shared Brain setting. Next: the noisy-writer stress test.
5. **Known issue:** the confirm re-run before retiring hit the response cache, so it confirmed nothing. No memory reached that step in the run above; the fix (`fresh=True`) is in progress.

### Next: Noisy-Writer Stress Test (in progress)

Each LoCoMo session is written twice: by the careful curator, and by a careless teammate (Nano, high temperature) whose errors come from the model itself rather than hand-written injections. Conditions: no memory / careful writer only (reference ceiling) / both writers / both writers audited, with retire thresholds of 3, 2 and 1. Reported as "LoCoMo + noisy writer (stress test)", not as a LoCoMo score. Expected if the audit works: both writers < careful only, audited recovers toward careful only, and the ledger blames the careless writer.

`python bench.py locomo --fast` runs one conversation with 30 audit and 30 held-out questions in about 20 s for about $0.01, and about 1 s from cache. Full runs are only for reported numbers.
