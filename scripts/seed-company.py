"""Import fictional source conversations through the real, permission-aware ingestion API.

No answers, extracted memories, grades, or events are precomputed. Existing source receipts
are checked against the original source before a repeat run skips them. Never clears a store.
"""
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import argparse
import base64
import os
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]

def validate(data):
    sys.path.insert(0, str(ROOT / 'backend'))
    from brainbob.acl import Org
    org = Org.load(ROOT / 'backend' / 'fixtures' / 'rusty_rod' / 'org.json')
    assert data['synthetic'] is True
    assert {p['id'] for p in data['members']} == set(org.members)
    sources = set()
    dates = []
    for ep in data['episodes']:
        assert ep['source'] not in sources, 'Source identifiers must be unique'
        sources.add(ep['source'])
        assert org.can_write(ep['author'], ep['scope']), f'Unauthorized write: {ep["key"]}'
        assert ep['authority'] != 'approved' or org.can_approve(ep['author'], ep['scope'])
        assert 'synthetic' in ep['text'].lower()
        dates.append(ep['date'])
    assert dates == sorted(dates), 'Import sources in chronological order'
    assert len({ep['scope'] for ep in data['episodes']}) == 22

def auth_headers():
    password = os.environ.get('BRAINBOB_DEMO_PASSWORD')
    if not password:
        return {}
    return {'Authorization': 'Basic ' + base64.b64encode(f'brainbob:{password}'.encode()).decode()}


def request(base, member, path, body=None):
    req = Request(base.rstrip('/') + path, headers={**auth_headers(), 'X-BrainBob-Member':member, 'Content-Type':'application/json'},
                  data=json.dumps(body).encode() if body is not None else None)
    try:
        with urlopen(req, timeout=600) as response:
            return json.load(response)
    except HTTPError as error:
        raise RuntimeError(f'{path}: HTTP {error.code}') from None

def receipts(base, member):
    req = Request(base.rstrip('/') + '/events?member=' + member, headers={**auth_headers(), 'X-BrainBob-Member':member})
    found = {}
    with urlopen(req, timeout=30) as response:
        for raw in response:
            if not raw.startswith(b'data:'):
                continue
            event = json.loads(raw[5:])
            if event['type'] == 'replay.done':
                return found
            if event['type'] == 'episode.ingested':
                found[event['source']] = event
    raise RuntimeError('Event replay ended before replay.done')

def verify_existing(base, ep, receipt):
    original = request(base, ep['author'], '/episodes/' + receipt['episode_id'])
    for field in ['text','date','source','scope']:
        if original[field] != ep[field]:
            raise RuntimeError(f'Source {ep["source"]} already exists with different {field}; version the dataset instead of overwriting it.')
    if not receipt.get('n_memories'):
        raise RuntimeError(f'Source {ep["source"]} has no successful extraction. Inspect its history before retrying; nothing was silently synthesized.')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', default='http://127.0.0.1:3001')
    parser.add_argument('--validate', action='store_true')
    parser.add_argument('--receipt', type=Path, default=ROOT/'data'/'workspace'/'company-import.json')
    args = parser.parse_args()
    source = ROOT/'fixtures'/'company'/'rusty-rod.json'
    data = json.loads(source.read_text())
    validate(data)
    if args.validate:
        print(f'Validated {len(data["episodes"])} source episodes, 18 people, 22 permission scopes.')
        return
    report = {'dataset':data['version'], 'sha256':hashlib.sha256(source.read_bytes()).hexdigest(), 'backend':args.base, 'episodes':[]}
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    for ep in data['episodes']:
        member = ep['author']
        if member not in existing:
            existing[member] = receipts(args.base, member)
        previous = existing[member].get(ep['source'])
        if previous:
            verify_existing(args.base, ep, previous)
            result = {'episode_id':previous['episode_id'], 'existing':True}
        else:
            result = request(args.base, member, '/episodes', {k:v for k,v in ep.items() if k != 'key'})
            if not result.get('memories'):
                raise RuntimeError(f'{ep["key"]}: ingestion produced no decisions; inspect the backend inference configuration.')
        report['episodes'].append({'key':ep['key'], **result})
        args.receipt.write_text(json.dumps(report, indent=2)+'\n')
        print(f'{len(report["episodes"]):02}/{len(data["episodes"])} {ep["key"]}: {result["episode_id"]}'+(' (already imported)' if previous else ''), flush=True)
    print('Import complete. All memory contents and maintenance decisions came from the backend.')

if __name__ == '__main__':
    try:
        main()
    except (URLError, RuntimeError) as error:
        raise SystemExit(f'Import stopped: {error}. Completed sources remain persisted; rerun to resume.') from None
