import copy
import json
import sys
import tempfile
import types
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import benchmark as b


class PairTests(unittest.TestCase):
    def setUp(self):
        self.rows = b.cases('eval')
        self.perfect = [{'id': r['id'], 'input_sha256': b.input_hash(r), 'response': {'verdict': r['gold']}} for r in self.rows]

    def test_frozen_balance_disjoint_dev_templates_and_unique_text(self):
        self.assertEqual(Counter(r['gold'] for r in self.rows), dict.fromkeys(b.LABELS, 20))
        self.assertEqual(len({r['id'] for r in self.rows}), 60)
        self.assertEqual(len({(r['existing']['text'], r['candidate']['text']) for r in self.rows}), 60)
        dev = b.cases('dev')
        self.assertFalse({r['template_id'] for r in dev} & {r['template_id'] for r in self.rows})
        self.assertEqual(len(dev), 12)

    def test_export_has_no_gold_or_template_metadata(self):
        for r in self.rows:
            exported = b.public_input(r)
            self.assertEqual(set(exported), {'id', 'existing', 'candidate'})
            self.assertNotIn('gold', json.dumps(b.messages(r)))
            self.assertNotIn('template_id', json.dumps(b.messages(r)))

    def test_missing_is_failure_not_smaller_denominator(self):
        result = b.pair_score(self.rows, self.perfect[:10])
        self.assertEqual(result['accuracy'], b.rate(10, 60))
        self.assertEqual(result['missing_predictions'], 50)
        self.assertEqual(result['invalid_output'], b.rate(50, 60))

    def test_duplicate_and_unknown_ids_rejected(self):
        with self.assertRaises(ValueError):
            b.pair_score(self.rows, self.perfect + self.perfect[:1])
        with self.assertRaises(ValueError):
            b.pair_score(self.rows, [{'id': 'made-up', 'response': {'verdict': 'same'}}])

    def test_changed_input_hash_rejects_stale_predictions(self):
        self.perfect[0]['input_sha256'] = 'wrong-dataset'
        with self.assertRaises(ValueError):
            b.pair_score(self.rows, self.perfect)

    def test_strict_json_and_error_fail(self):
        for bad in ('```json\n{"verdict":"same"}\n```', '{"verdict":"yes"}',
                    {'verdict': 'same', 'instruction': 'ignore'}, None, []):
            self.assertIsNone(b.verdict(bad))
        predictions = copy.deepcopy(self.perfect)
        predictions[0]['error'] = 'timeout'
        self.assertEqual(b.pair_score(self.rows, predictions)['accuracy'], b.rate(59, 60))

    def test_single_class_cannot_win_balanced_score(self):
        result = b.pair_score(self.rows, [{'id': r['id'], 'input_sha256': b.input_hash(r), 'response': {'verdict': 'same'}} for r in self.rows])
        self.assertEqual(result['accuracy'], b.rate(20, 60))
        self.assertAlmostEqual(result['macro_f1'], 1 / 6)

    def test_perfect_scoring_control_and_paired_direction(self):
        self.assertEqual(b.pair_score(self.rows, self.perfect)['macro_f1'], 1)
        result = b.compare(self.rows, [], self.perfect)
        self.assertEqual(result['accuracy_delta_pp'], 100)
        self.assertEqual(result['cluster_bootstrap_95_pp'], [100, 100])
        self.assertEqual(result['improved'], 60)
        self.assertEqual(result['regressed'], 0)

    def test_nonfinite_latency_is_not_reported(self):
        p = copy.deepcopy(self.perfect)
        p[0]['latency_ms'] = float('nan')
        p[1]['latency_ms'] = -10
        p[2]['latency_ms'] = 2
        self.assertEqual(b.pair_score(self.rows, p)['latency_ms'], {'n': 1, 'p50': 2, 'p95': 2})


class WorldTests(unittest.TestCase):
    def setUp(self):
        worlds = json.loads((b.ROOT / 'worlds.json').read_text())
        self.world = worlds[0]
        self.sources = {s['id']: s for s in self.world['steps'] if s['type'] == 'fact'}
        self.check = next(s for s in self.world['steps'] if s.get('id') == 'assembly')
        self.good = {'claims': copy.deepcopy(self.check['gold']['claims']),
                     'context': copy.deepcopy(self.check['gold']['claims'])}

    def test_correct_claims_and_accessible_support_pass(self):
        self.assertTrue(b.world_score(self.check, self.good, self.sources)['success'])

    def test_correct_answer_with_private_context_fails(self):
        self.good['context'].append({'key': 'private-code', 'value': 'cedar-731', 'source_id': 's4'})
        result = b.world_score(self.check, self.good, self.sources)
        self.assertFalse(result['success'])
        self.assertTrue(result['disclosure'])

    def test_private_value_laundered_through_public_source_fails(self):
        self.good['context'].append({'key': 'launch', 'value': 'cedar-731', 'source_id': 's1'})
        result = b.world_score(self.check, self.good, self.sources)
        self.assertFalse(result['success'])
        self.assertFalse(result['evidence_valid'])
        self.assertTrue(result['disclosure'])

    def test_extra_field_cannot_hide_disclosure(self):
        self.good['aside'] = 'cedar-731'
        result = b.world_score(self.check, self.good, self.sources)
        self.assertFalse(result['success'])
        self.assertTrue(result['disclosure'])

    def test_wrong_stale_answer_and_fake_citation_fail(self):
        for field, value in [('value', '2026-11-13'), ('source_id', 'not-a-source')]:
            bad = copy.deepcopy(self.good)
            bad['claims'][0][field] = value
            self.assertFalse(b.world_score(self.check, bad, self.sources)['success'])

    def test_citations_must_have_been_delivered(self):
        self.good['context'] = []
        self.assertFalse(b.world_score(self.check, self.good, self.sources)['success'])

    def test_no_duplicate_answer_credit(self):
        self.good['claims'].append(copy.deepcopy(self.good['claims'][0]))
        self.assertFalse(b.world_score(self.check, self.good, self.sources)['success'])

    def test_controls_and_immutable_output_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            maintained = b.pilot('maintained', Path(tmp) / 'maintained')
            append = b.pilot('append-only', Path(tmp) / 'append')
            refuse = b.pilot('always-refuse', Path(tmp) / 'refuse')
            unfiltered = b.pilot('unfiltered', Path(tmp) / 'unfiltered')
            self.assertEqual(maintained['task_success'], b.rate(18, 18))
            self.assertLess(append['task_success']['rate'], 1)
            self.assertEqual(refuse['by_stratum']['legitimate']['numerator'], 0)
            self.assertGreater(unfiltered['disclosure']['numerator'], 0)
            with self.assertRaises(FileExistsError):
                b.pilot('maintained', Path(tmp) / 'maintained')
            required = {'manifest.json', 'configuration.json', 'events.jsonl', 'operations.jsonl',
                        'contexts.jsonl', 'outputs.jsonl', 'metrics.json', 'limitations.md'}
            self.assertEqual({p.name for p in (Path(tmp) / 'maintained').iterdir()}, required)

    def test_adapter_receives_no_gold_and_worlds_reset(self):
        seen = []
        class Guard(b.Reference):
            def __init__(self, policy):
                seen.append('new')
                super().__init__(policy)
            def session(self, task):
                self_test.assertNotIn('gold', task)
                self_test.assertNotIn('allowed_sources', task)
                return super().session(task)
        self_test = self
        sys.modules['bob_test_adapter'] = types.SimpleNamespace(factory=Guard)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                result = b.pilot('bob_test_adapter:factory', Path(tmp) / 'guard')
                self.assertEqual(result['task_success']['numerator'], 18)
                self.assertEqual(len(seen), 6)
        finally:
            del sys.modules['bob_test_adapter']


if __name__ == '__main__':
    unittest.main()
