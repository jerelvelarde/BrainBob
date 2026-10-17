---
pretty_name: Bob (Shared Brain) Benchmark — Public Pilot
language:
- en
size_categories:
- n<1K
tags:
- benchmark
- synthetic
- agent-memory
- multi-agent
- access-control
configs:
- config_name: organizational_worlds
  default: true
  data_files:
  - split: public_dev
    path: organizational-public-dev.jsonl
  - split: pilot
    path: organizational-pilot.jsonl
- config_name: memory_pairs
  data_files:
  - split: dev
    path: memory-pairs-dev.jsonl
  - split: eval
    path: memory-pairs-eval.jsonl
- config_name: structured_pilot
  data_files:
  - split: pilot
    path: structured-pilot.jsonl
---

# Bob (Shared Brain) Benchmark

Can an agent memory system keep knowledge **correct, current and appropriately scoped** as people, evidence, permissions and organizational commitments change?

Bob evaluates shared memory within and between organizations. This release is a **public synthetic pilot**, contributed by the BrainBob project. It is not the complete proposed Bob Core suite, an independently validated benchmark, or an industry standard. No model performance or leaderboard ranking is claimed by this dataset release.

## What is included

| Configuration | Size and splits | Purpose |
| --- | --- | --- |
| `organizational_worlds` | 6 worlds, 41 checkpoints; 1 public development world and 5 public pilot worlds | Scoped session assembly, authority-aware corrections, cross-organization publication, membership changes and grants, conflict and retention, correction propagation |
| `memory_pairs` | 12 development pairs; 60 evaluation pairs, balanced 20 per class | Classify `same`, `conflict`, or `unrelated` |
| `structured_pilot` | 6 worlds, 18 checkpoints | Deterministic structured-memory scorer diagnostics; separate from the natural-language organizational worlds |

These are distinct measurements. Do not combine their scores or present the structured reference control as model performance.

All people, organizations, messages, dates, prices and protected values are synthetic. The fixtures were authored for the BrainBob project; labels have not been independently adjudicated. The pair cases are agent-authored with automated validation.

## Load the data

```python
from datasets import load_dataset
import json

repo = "JerelVelarde/bob-benchmark"
worlds = load_dataset(repo, "organizational_worlds")
world = json.loads(worlds["public_dev"][0]["world_json"])
pairs = load_dataset(repo, "memory_pairs")
structured = load_dataset(repo, "structured_pilot", split="pilot")
```

Pin `revision` to a Hugging Face commit when reporting results. World records expose their ID, checkpoint count and JSON payload. Organizational records also expose original split, domain and family. JSON strings preserve heterogeneous policy/source/checkpoint schemas without a custom dataset loader. Decode with `json.loads` and replay timeline items in order; never give an answering model the complete future timeline.

Pair rows contain `id`, `template_id`, `existing`, `candidate`, and `gold`. **Do not feed the full row to a model.** Use the runner's export command below, which strips labels and template IDs and produces fixed messages plus input hashes.

## Run and score

Download [bob-source.zip](bob-source.zip) and extract it into a new directory. It contains the original fixtures, separate organizational oracles, Python runners, tests, adapter contract and proposed specification at the source revision below. Run commands from the extracted directory. Python 3.10+ is required.

```sh
# Small diagnostic: no API keys, model calls or third-party packages required.
python3 benchmarks/bob/benchmark.py export --split eval --out /tmp/bob-eval-inputs
python3 benchmarks/bob/benchmark.py pilot --out /tmp/bob-reference-pilot
python3 -m unittest discover -s benchmarks/bob -p 'test_*.py' -v

# Organizational policy, scoring, runner and fixture checks; no live model calls.
python3 -m pip install pytest
python3 -m pytest bobbench/tests -q
```

Output directories must be new. Follow `benchmarks/bob/README.md` in the archive to score model predictions and compare base/tuned results. Pair scores include accuracy, macro-F1, invalid and missing outputs, confusion matrix, provenance and optional latency. Freeze prompts and adapters before evaluating; evaluation data exposed during tuning becomes development data.

For organizational model runs, follow `bobbench/CONTRACT.md` and configure the answerer in `bobbench/answer.py`. This path needs the `openai` package and an authorized OpenAI-compatible endpoint and **incurs inference costs**. Available generic conditions are `no_memory`, `full_history`, `always_refuse` and `unfiltered`. BrainBob-specific `append_only` and `maintained` adapters are not included and report unsupported. Choose conditions explicitly.

Organizational CATS requires task correctness, behavior, provenance, authorized context, no protected content and the context budget to pass together. Report legitimate, boundary and maintenance strata separately, with their macro average and failure counts. Checker revision 0.2 is included. String-level checking is incomplete; it does not guarantee semantic leakage detection.

## Public labels and limitations

All labels and oracles in this release are **public**, including the structured pilot's gold inside `world_json` and organizational oracle files inside the archive. “Hidden” in the original contract means withheld from the evaluated adapter during execution, not confidential on the Hub. This release cannot support secret-test or contamination-free claims. The runner's separation is a protocol convention, not an adversarial isolation sandbox.

The sample is small: six organizational worlds with 27–31 timeline items each, one development world, and no independently adjudicated annotations. Memory pairs come from 20 evaluation templates and four separate development templates; lexical shortcuts and template effects can inflate results. Structured pilot facts remove natural-language extraction and answering difficulty. Reference controls are fixture/scorer checks, not evidence that BrainBob or a learned model generalizes. Cross-world aggregate claims require broader, independently reviewed data.

## Provenance and reuse

Source repository: [BrainBob](https://github.com/jerelvelarde/BrainBob).
Source Git revision: `{{SOURCE_REVISION}}`.
See [release-manifest.json](release-manifest.json) for per-file SHA-256 hashes and counts. The source archive excludes application state, caches, credentials, model artifacts and run outputs. No third-party benchmark data is redistributed.

**License: not specified by the source repository.** Public availability does not itself grant an open-source or open-data license. Contact the repository maintainers about reuse terms; a license can be added in a subsequent release once chosen.

For attribution, identify “Bob (Shared Brain) Benchmark, public pilot v0.1, BrainBob contributors” and include both the source Git revision and Hugging Face dataset revision. Do not cite this release as a peer-reviewed publication.
