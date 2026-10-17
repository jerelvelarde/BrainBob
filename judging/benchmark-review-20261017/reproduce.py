"""Offline review evidence; reproduces known gaps, does not rescore any model run."""
import gzip
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from bobbench.schema import load_world, load_oracle, parse_time
from bobbench.policy import Policy
from bobbench.score import score_checkpoint

world = load_world(str(ROOT / 'bobbench/worlds/w2-authority-corrections.json'))
oracle = load_oracle(str(ROOT / 'bobbench/oracles/w2-authority-corrections.json'))
cp = next(c for c in world.checkpoints if c['checkpoint_id'] == 'cp-2')
policy = Policy.replay(world.raw, upto_seq=cp['seq'])
readable = {e['event_id'] for e in policy.readable_events(cp['principal'], parse_time(cp['requested_time']), cp.get('purpose'))}
record = {'answer': 'Previously due November 18, the release is now scheduled for December 2.',
          'context': '', 'cited_event_ids': ['w2-evt-01']}
result = score_checkpoint(oracle.checkpoints['cp-2'], record, cp, readable)
counts = defaultdict(lambda: defaultdict(lambda: {'probe_objects': 0, 'http_responses': 0}))
with gzip.open(ROOT / 'bobbench/results/20261017-141014/traces.jsonl.gz', 'rt') as stream:
    for line in stream:
        row = json.loads(line)
        if row.get('type') != 'checkpoint' or row.get('condition') not in ('append_only', 'maintained'):
            continue
        for surface, probe in (row.get('probes') or {}).items():
            if isinstance(probe, dict):
                counts[row['condition']][surface]['probe_objects'] += 1
                counts[row['condition']][surface]['http_responses'] += len(probe.get('responses') or [])
print(json.dumps({'reviewed_snapshot': '13df1c0', 'recorded_run_build': '5fcd554',
                  'mode': 'offline counterexample and trace inspection; no inference or historical rescore',
                  'wrong_current_date': {'record': record, 'expected_cats': 0, 'observed': result},
                  'surface_execution_counts': counts}, indent=2))
