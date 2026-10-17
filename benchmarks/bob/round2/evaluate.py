"""Evaluate frozen round-two predictions with evaluator-local gold and the existing scorer."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
import benchmark as b


def frozen_cases(gold, root=ROOT):
    manifest = json.loads((root / 'manifest.json').read_text())
    checks = [(gold, manifest['gold_sha256']),
              (root / 'inputs.jsonl', manifest['input_sha256']),
              (Path(b.__file__), manifest['scorer_sha256'])]
    if any(b.digest(path) != expected for path, expected in checks):
        raise ValueError('Frozen gold, inputs, or scorer hash mismatch; do not silently revise this evaluation')
    if hashlib.sha256(b.PROMPT.encode()).hexdigest() != manifest['prompt_sha256']:
        raise ValueError('Frozen prompt mismatch')
    rows = b.read_jsonl(gold)
    expected = [dict(b.public_input(r), input_sha256=b.input_hash(r), messages=b.messages(r)) for r in rows]
    if expected != b.read_jsonl(root / 'inputs.jsonl'):
        raise ValueError('Gold does not match the frozen model-visible inputs')
    return rows, manifest


def save_new(path, result):
    # Never overwrite earlier reports, including when a caller reuses an output path.
    with path.open('x') as target:
        target.write(json.dumps(result, indent=2, allow_nan=False) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    score = sub.add_parser('score')
    score.add_argument('--predictions', type=Path, required=True)
    score.add_argument('--model', required=True)
    comp = sub.add_parser('compare')
    comp.add_argument('--base', type=Path, required=True)
    comp.add_argument('--tuned', type=Path, required=True)
    for child in (score, comp):
        child.add_argument('--gold', type=Path, required=True, help='Evaluator-local frozen answer key')
        child.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    rows, manifest = frozen_cases(args.gold)
    if args.command == 'score':
        result = b.pair_score(rows, b.read_jsonl(args.predictions))
        result.update(model=args.model, predictions_sha256=b.digest(args.predictions))
    else:
        result = b.compare(rows, b.read_jsonl(args.base), b.read_jsonl(args.tuned))
        result.update(base_sha256=b.digest(args.base), tuned_sha256=b.digest(args.tuned))
    result['manifest'] = manifest
    result['evaluation_wrapper_sha256'] = b.digest(__file__)
    save_new(args.out, result)
    print(args.out)


if __name__ == '__main__':
    main()
