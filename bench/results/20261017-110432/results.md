# LongMemEval_S results (20261017-110432)

Judge: official LongMemEval prompts, but official uses GPT-4o; here judge is openai/gpt-oss-120b (temp 0). Answer model Nemotron-3-Super-120B; extraction Nemotron-3.5-Lightning-30B (thinking off); retrieval BM25 top-40.
Requested n=50 per condition; unfinished tasks at report time: 0. Wall total 404s.

| condition | n | overall | abstention | knowledge-update | multi-session | single-session-assistant | single-session-preference | single-session-user | temporal-reasoning | avg ctx tokens | wall s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 50 | 39/50 (78%) | 4/4 (100%) | 7/8 (88%) | 10/13 (77%) | 6/6 (100%) | 1/3 (33%) | 6/7 (86%) | 9/13 (69%) | 108946 | 335 |
| brainbob | 50 | 35/50 (70%) | 4/4 (100%) | 8/8 (100%) | 7/13 (54%) | 6/6 (100%) | 1/3 (33%) | 5/7 (71%) | 8/13 (62%) | 2681 | 404 |

| stage | prompt tok | completion tok | USD |
|---|---|---|---|
| answer | 5581356 | 76877 | 1.859 |
| judge | 22727 | 7062 | 0.003 |
| extract | 5666532 | 768212 | 0.437 |
| total | | | 2.299 |

Stats: {'extract_parse_fail': 76, 'extract_empty': 76, 'retry_extract': 61, 'retry_answer': 26, 'facts_total': 22940, 'retry_judge': 8}