# Live memory-audit demo (issue #2, backend script for the issue #3 demo)

The story in four beats: **wrong answer -> the bad memory it cited -> the audit decision -> a new answer, cited.**
A teammate (Patrick) posts a wrong closing time. The shared brain repeats it. One Check plus one Review
retires that single memory (after a fresh re-answer confirms it) and promotes Patrick's other, correct memory
from the same message. A different question, asked by a different reader, then gets the right answer with a citation.

## Data disclosure (say this on stage)

| what | kind |
|---|---|
| The two seed conversations (Mr. Krabs' hours, Patrick's update) and the 3 memories extracted from them | **synthetic** (invented; text starts with `[synthetic demo data]`, source `synthetic-seed`) |
| 5 asks + checks run by `seed.py` (2 closing-time questions, 3 catering questions) | **seeded history (real model calls at seed time)**: real curator, agent and judge calls, made before the demo starts |
| Steps 1-4 below | **live** (real model calls when you press send) |
| `backend/results/20261017-131649-demo/` | **recorded** (a verified run, used only as the fallback) |

## Threshold choice: (a), the default `min_changes=3`

We kept the evaluator's default (a memory needs correctness flips on 3 different tasks before Review acts)
and did not change `server.py`. Retiring on a single complaint is exactly what the audit is designed not to do, so
the demo shows the real rule: two earlier tasks already caught the bad memory (seeded history, real calls), and
the live question is the third. Review then re-answers one harmed task **without the cache** (`fresh=True`) and
retires only if that fresh answer is graded correct (`memory.retired` carries `confirmed: true`).
The cost is ~10-40 s of seeding before the demo.

## Setup (before the audience arrives)

From `backend/`. Stop whatever backend is on port 3001 first (the frontend talks to `NEXT_PUBLIC_BRAINBOB_API_URL`,
default `http://127.0.0.1:3001`).

```
.venv/Scripts/python demo/reset.py                       # wipes demo/state/ (gitignored)
.venv/Scripts/python demo/serve.py --port 3001           # terminal 1; leave running
.venv/Scripts/python demo/seed.py --base http://127.0.0.1:3001   # terminal 2; ~10-40 s, prints {"bad": "m2", "good": "m3", "hours": "m1"}
```

`serve.py` = `cd demo/state && ../../.venv/Scripts/python ../../server.py --legacy` (no permissions, no write-time
maintenance) plus two overrides server.py has no flags for: the port, and an **isolated model cache** in `demo/state/cache`
that `reset.py` wipes, so every model call in the demo is real. With `--shared-cache` (or plain `server.py`) the
shared `backend/cache` is used and an identical prompt returns the stored completion of an earlier real call;
if you present that way, say so. `seed.py` exits 2 if any seeded check did not record its expected flip: reset and seed again.

Then start the frontend (`apps/web`, port 3000) and open it. Nothing else is needed.

## Live script (3 minutes)

Use the chat in the scene. The reader switcher picks who is asking; the mode buttons are Ask / Remember / Check / Review.
Times are what the verified runs measured; allow up to ~10 s for a cold first model call.

| # | reader | mode | type exactly | expect | wait |
|---|---|---|---|---|---|
| 1 | Sales Team | Ask | `What time does the Krusty Krab close on weekdays?` | `6 PM` (wrong). The cited record is Patrick's memory **m2** "Krusty Krab changed its weekday hours, now closes at 6 PM instead of 10 PM" | ~1 s |
| 2 | Sales Team | Check | `10 PM` | "The cited-memory check recorded correctness flips for 1 memory. ..." The inspector checks m2: wrong with it, right without it (red flash) | 1-11 s (judge) |
| 3 | Sales Team | Review | `review` | `- retire: harmful on ['t-…', 't-…', 't-…']` (m2, 3 tasks) and `- promote: helpful on ['t-…', 't-…', 't-…']` (m3, "Catering orders need 48 hours' notice"). m2 goes to the archive, m3 to the trusted shelf | ~1 s |
| 4 | **John** | Ask | `How late can a customer walk in on a Thursday?` | `The Krusty Krab closes at 10 PM on Thursdays, so a customer can walk in up until 10 PM.` citing **m1** (Mr. Krabs, scope Krusty Krab) | ~1 s |

Talking points: step 1 is the bug; step 2 is the only human input (the right answer, never stored as memory);
step 3 is the audit (3 tasks of evidence + a fresh confirmation); step 4 is a question nobody asked before,
from another reader (switching reader starts a fresh chat), answered from the surviving memory. m3 came from the
**same message and author** as the bad memory and is promoted, so the audit removes one claim, not an author or a conversation.
Do steps 2 and 3 in the same reader as step 1: Check uses the last Ask of the current chat.

Events the scene receives (all frontend schema types; statuses only trial/promoted/retired): `memory.retrieved`,
`answer.produced` (cited_ids `["m2"]`), `evaluation.started`, `memory.checked` (flipped, without_correct true),
`evidence.recorded` x2, `evaluation.finished`, then on Review `memory.retired` (m2, confirmed true) and `memory.promoted` (m3).

## Scripted run and records

```
.venv/Scripts/python demo/reset.py
.venv/Scripts/python demo/serve.py --port 3002                  # terminal 1
.venv/Scripts/python demo/run_scenario.py --base http://127.0.0.1:3002
```

It seeds, runs steps 1-4 with the same request bodies the frontend sends, subscribes to `/events`, checks 15 conditions
(prints PASS/FAIL, exit 1 on any failure) and writes `backend/results/<timestamp>-demo/`: `responses.json` (every request,
response, phase label and timing), `events.jsonl` (every event, in seq order), `meta.json` (git commit, models, times,
checks) and `state/` (the server's memory/events/episodes files, for replay). `results/` is gitignored: copy the folder to the demo machine.

Verified 2026-10-17, each run on an empty isolated cache (all calls real): `results/20261017-131558-demo` and
`results/20261017-131649-demo`, 15/15 checks both times, same answers both times (`6 PM` citing m2; after review
"…walk in up until 10 PM." citing m1). Models: curator and agent `nvidia/Nemotron-3.5-Lightning-30B-A3B`, judge `openai/gpt-oss-120b`.
Honest caveat: a first wording ("the Krusty Krab now closes at 6 PM on weekdays", hours memory "9 AM to 10 PM") was
not stable (the agent sometimes kept the older 10 PM memory, and once read "9 AM to 10 PM" as 9 PM), so the seed now states
the change explicitly. Curator wording can vary slightly between runs (e.g. "Mr. Krabs (owner) stated that…");
`seed.py` finds the three memories by content (6 PM / 48 hours / 10 PM), not by fixed text.

## Fallback: recorded replay

If Crusoe is slow or down, replay the verified run and **say it is a recording** (run of 2026-10-17 13:16 PT):

```
.venv/Scripts/python demo/reset.py --restore results/20261017-131649-demo
.venv/Scripts/python demo/serve.py --port 3001
```

The server reloads `events.jsonl`, so the frontend receives the whole recorded history (52 events) as state and shows m2
retired and m3 promoted. Open **Retrace**, then "Choose a recorded event" to step through it: `#43 answer.produced` (6 PM, cites m2),
`#44-#48` the check of m2, `#49 memory.retired` (m2, confirmed), `#50 memory.promoted` (m3) and `#52 answer.produced`
(10 PM, cites m1). Events `#1-#41` are the synthetic seed and the seeded history. Asks, Checks and Reviews sent from the chat after a restore are live again (the recorded tasks are not restored,
so a Check on them is not possible). The same run is also readable as files: `responses.json` has the four live answers verbatim.
