import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import benchmark as b

spec = importlib.util.spec_from_file_location('round2_evaluate', ROOT / 'round2/evaluate.py')
r2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r2)


class RoundTwoTests(unittest.TestCase):
    def test_public_handoff_has_only_expected_model_inputs(self):
        rows = b.read_jsonl(ROOT / 'round2/inputs.jsonl')
        manifest = json.loads((ROOT / 'round2/manifest.json').read_text())
        self.assertEqual(len(rows), 60)
        self.assertEqual(len({r['id'] for r in rows}), 60)
        self.assertEqual(b.digest(ROOT / 'round2/inputs.jsonl'), manifest['input_sha256'])
        self.assertEqual(b.digest(ROOT / 'benchmark.py'), manifest['scorer_sha256'])
        for row in rows:
            self.assertEqual(set(row), {'id', 'existing', 'candidate', 'input_sha256', 'messages'})
            self.assertEqual(row['messages'], b.messages(row))
            self.assertEqual(row['input_sha256'], b.input_hash(row))

    def test_key_input_and_scorer_tampering_are_rejected(self):
        # Public round-one examples exercise the loader without exposing new gold.
        rows = b.cases('dev')[:3]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            gold = root / 'gold.jsonl'
            b.write_jsonl(gold, rows)
            b.write_jsonl(root / 'inputs.jsonl', [dict(b.public_input(r), input_sha256=b.input_hash(r), messages=b.messages(r)) for r in rows])
            manifest = copy.deepcopy(json.loads((ROOT / 'round2/manifest.json').read_text()))
            manifest.update(gold_sha256=b.digest(gold), input_sha256=b.digest(root / 'inputs.jsonl'))
            b.save_json(root / 'manifest.json', manifest)
            self.assertEqual(r2.frozen_cases(gold, root)[0], rows)
            for target in (gold, root / 'inputs.jsonl'):
                original = target.read_bytes()
                target.write_bytes(original + b'\n')
                with self.assertRaises(ValueError):
                    r2.frozen_cases(gold, root)
                target.write_bytes(original)
            manifest['scorer_sha256'] = 'changed'
            b.save_json(root / 'manifest.json', manifest)
            with self.assertRaises(ValueError):
                r2.frozen_cases(gold, root)

    def test_reports_cannot_overwrite_earlier_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            report = Path(temp) / 'report.json'
            r2.save_new(report, {'original': True})
            with self.assertRaises(FileExistsError):
                r2.save_new(report, {'original': False})
            self.assertEqual(json.loads(report.read_text()), {'original': True})


if __name__ == '__main__':
    unittest.main()
