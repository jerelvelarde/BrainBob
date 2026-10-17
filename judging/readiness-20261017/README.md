# Readiness verification evidence — October 17, 2026

This directory records verification performed during the app-readiness assessment. No inference or GPU training was run to produce these artifacts.

- `memops-comparison.json`: independent rescore of Bonan's committed `base_eval.jsonl` and `tuned_eval.jsonl` from commit `d85064d4ee7d52646d22a69340974a9933015689`. The scorer and frozen cases are the `benchmarks/bob/` implementation from `ab084a6` (now merged locally). It reproduces 32/60 versus 42/60, +16.7 points, template-cluster bootstrap 95% [+5.0, +28.3], 17 improvements, seven regressions. Raw prediction hashes are embedded in the report. This is a public synthetic pair-classification diagnostic, not the organizational Bob pilot.
- `organizational-refusal-control/`: the actual six-world `bobbench` runner, 41 checkpoints, always-refuse control, one replicate, scorer 0.2. It made zero model calls and produced 0% legitimate / 25% macro CATS. Traces and scorecard are saved; adapter workdir/export copies were not retained here. The default answering model in metadata was not invoked. This is a negative-control plumbing result, not a model or app score.

Commands, run from the repository root:

```sh
python3 benchmarks/bob/benchmark.py compare \
  --base experiments/memops-small/out/runs/20261017-210457/base_eval.jsonl \
  --tuned experiments/memops-small/out/runs/20261017-210457/tuned_eval.jsonl \
  --out /tmp/new-memops-comparison.json

backend/.venv/bin/python -m bobbench.run \
  --worlds all --conditions always_refuse --fast \
  --out /tmp/new-bob-refusal-run
```

Use new output paths to preserve earlier evidence. The refusal run records source commit `3efd8f6` and a timestamp in its trace. Other teammates had unrelated frontend edits and the maintenance replay work in progress during execution; this is not a claim that the entire working tree was clean. The refusal control does not import those frontend or maintenance changes. The scorer fix it exercises was already committed in `cd469fb`.

See [the readiness scorecard](../../docs/readiness.md), [external data preflight](../../bench/evidence/gatemem-data-preflight.json), and the [integration runbook](../../apps/web/README.md) for scope and remaining blockers. Bonan confirmed canonical adapter revision `b904e6ec0baea37bf70209093b8c59332d3c450a`; the numerical rescore does not independently verify private model weights or training provenance.
