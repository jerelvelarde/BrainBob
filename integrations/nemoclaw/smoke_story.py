"""Eight-step operator-driven story. NOT yet run inside a NemoClaw sandbox.

No agent is simulated. Stops for exported, real agent trace files at each gate.
"""
import argparse
import datetime
import http.client
import json
import os
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit, quote

from brainbob_tools import BrainBobTools, request_json

ROOT = Path(__file__).resolve().parent


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def api(member, method, path, body=None):
    result = request_json(os.environ['BRAINBOB_URL'], member, method, path, body)
    require(result['ok'], 'Backend operation failed: ' + json.dumps(result.get('error')))
    return result['data']


def events(member):
    url = urlsplit(os.environ['BRAINBOB_URL'])
    cls = http.client.HTTPSConnection if url.scheme == 'https' else http.client.HTTPConnection
    conn = cls(url.hostname, url.port, timeout=15)
    try:
        conn.request('GET', '/events', headers={'X-BrainBob-Member': member})
        response = conn.getresponse()
        require(response.status == 200, 'SSE denied')
        result = []
        while True:
            line = response.readline()
            require(bool(line), 'SSE ended before replay.done')
            if line.startswith(b'data:'):
                event = json.loads(line[5:])
                result.append(event)
                if event['type'] == 'replay.done':
                    return result
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--i-know', action='store_true', help='Allow non-local or unconfirmed demo store')
    parser.add_argument('--demo-store', action='store_true', help='Operator attests backend uses a clean isolated disposable store with org ACL + maintain.ingest')
    parser.add_argument('--run', default='story-run', help='New artifact directory name under integrations/nemoclaw')
    parser.add_argument('--replay', help='Read an existing run directory, with no HTTP or mutations')
    args = parser.parse_args()
    if args.replay:
        path = (ROOT / args.replay).resolve()
        require(path.is_relative_to(ROOT), 'Replay must stay inside integration directory')
        print((path / 'trace.jsonl').read_text(encoding='utf8'))
        print('Recorded replay only; no requests executed; no live harness claim.')
        return
    url = urlsplit(os.environ.get('BRAINBOB_URL', ''))
    require(args.i_know or (url.hostname in ('localhost', '127.0.0.1', '::1') and args.demo_store),
            'Refusing non-local/non-demo store; use --demo-store for isolated local storage or explicit --i-know')
    require(os.environ.get('BRAINBOB_MEMBER') == 'sales-01', 'Host must bind BRAINBOB_MEMBER=sales-01')
    directory = (ROOT / args.run).resolve()
    require(directory.is_relative_to(ROOT), 'Artifacts must stay inside integration directory')
    directory.mkdir(exist_ok=False)
    adapter = BrainBobTools()
    def record(kind, data):
        with (directory / 'trace.jsonl').open('a', encoding='utf8') as f:
            f.write(json.dumps({'at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'kind': kind, 'data': data}) + '\n')
    def snapshot():
        return {m: api(m, 'GET', '/memories') for m in ('exec-01', 'sales-01', 'eng-01')}
    def fixture(text, date, member='exec-01', scope='rusty-rod', authority='approved'):
        body = dict(text=text, date=date, source='issue8-host-fixture', scope=scope, authority=authority)
        result = api(member, 'POST', '/episodes', body)
        record('host_fixture', {'member': member, 'input': body, 'response': result})
        require(result['memories'], 'No memories extracted; stop and investigate maintenance')
        return result
    def agent(label, prompt, expected_source, expected_date, forbidden, goal_ids=()):
        print(f'\n{label} — give this exact prompt inside NemoClaw:\n{prompt}\n')
        print('Export JSON: session_id, sandbox_id, model, answer, calls [{tool, arguments, result}].')
        path = Path(input('Path to real exported agent JSON (no keys; Ctrl-C to stop): ').strip())
        trace = json.loads(path.read_text(encoding='utf8-sig'))
        require(all(trace.get(k) for k in ('session_id', 'sandbox_id', 'model', 'answer', 'calls')), 'Missing real agent evidence')
        calls = trace['calls']
        for call in calls:
            require(call['tool'] in ('read_memory', 'read_source'), 'Read-only story must not include proposals')
            actual = adapter.call(call['tool'], call['arguments'])
            require(actual == call['result'], 'Recorded result differs from current backend')
        retrieved = [m for c in calls if c['tool'] == 'read_memory' and c['result']['ok'] for m in c['result']['memories']]
        require(any(m.get('origin') == expected_source and m.get('status') != 'retired' for m in retrieved), 'Current source was not reached through memory retrieval')
        require(all(m.get('scope') in ('rusty-rod', 'rusty-rod/sales', 'rusty-rod/sales/sales-01') for m in retrieved), 'Out-of-scope metadata in agent retrieval')
        require(any(c['tool'] == 'read_source' and c['arguments']['source_id'] == expected_source and c['result']['ok'] for c in calls), 'Missing accessible source call')
        require(expected_source in trace['answer'] and expected_date in trace['answer'], 'Answer lacks expected date/source citation')
        require(set(goal_ids) <= {m['id'] for m in retrieved}, 'Unrelated goal not retrieved')
        require(not any(token in json.dumps(trace) for token in forbidden), 'Private or stale information in trace')
        record(label, trace)
        return trace

    record('status', 'Operator-driven live verification pending; code unit-tested with fake backend, NOT yet run inside a NemoClaw sandbox at authoring time')
    require(all(not v for v in snapshot().values()) or args.i_know, 'Store must be empty for all three fixture members')
    # 1. Approved commitment + unrelated valid goal, normal episode maintenance.
    print('1. Publish approved Atlas November 6, 2026 and unrelated goal.')
    original = fixture('The approved Atlas customer launch commitment is November 6, 2026.', '2026-10-17')
    goal = fixture('The separate valid goal is to reduce support response time to two hours.', '2026-10-17')
    goal_ids = [m['id'] for m in goal['memories']]
    # 2. Actual agent A must invoke tools; no /ask substitute.
    a = agent('2 Agent A', 'Retrieve the Atlas customer launch commitment with read_memory, then read_source. State the date and cite the episode ID. Do not propose any memory.', original['episode_id'], 'November 6', [])
    # 3. Engineering estimate must remain private and cannot overwrite commitment.
    print('3. Publish private Engineering tentative November 13 estimate.')
    private = fixture('Private Engineering estimate: Atlas might launch November 13, 2026. Internal codename PRIVATE-ATLAS-ESTIMATE.', '2026-10-18', 'eng-01', 'rusty-rod/engineering', 'tentative')
    sales = api('sales-01', 'GET', '/memories')
    require(all(m.get('scope') != 'rusty-rod/engineering' and m.get('origin') != private['episode_id'] for m in sales), 'Private memory leaked')
    require(all(any(m['id'] == old['id'] and m['status'] != 'retired' for m in sales) for old in original['memories']), 'Tentative estimate displaced commitment')
    record('3 scoped_state', sales)
    # 4. Approved correction uses the same normal maintenance path.
    print('4. Publish approved correction to November 13.')
    correction = fixture('Approved correction: the Atlas customer launch commitment is November 13, 2026, replacing November 6, 2026.', '2026-10-19')
    histories = [api('sales-01', 'GET', '/memories/' + quote(m['id'], safe='') + '/history') for m in original['memories']]
    require(any(any(m.get('supersedes') in {o['id'] for o in original['memories']} and m.get('origin') == correction['episode_id'] for m in h['chain']) for h in histories), 'Correction has no supersedes chain')
    require(all(any(m['id'] == old['id'] and m['status'] == 'retired' for h in histories for m in h['chain']) for old in original['memories']), 'Old commitment not retired')
    record('4 history', histories)
    # 5. Fresh B receives only this task, no A conversation/scratchpad.
    b = agent('5 Fresh Agent B', 'In a fresh session, retrieve current Atlas launch and the separate support response-time goal using read_memory. Exclude retired commitments from your answer. Read the current source with read_source. State the current launch date, the unrelated goal, and cite episode IDs. Do not propose memory.', correction['episode_id'], 'November 13', ['PRIVATE-ATLAS-ESTIMATE', private['episode_id']], goal_ids)
    require(a['session_id'] != b['session_id'], 'B is not a fresh session')
    require('November 6' not in b['answer'], 'B used stale commitment')
    require('two hours' in b['answer'].lower() or '2 hours' in b['answer'].lower(), 'Goal absent from answer')
    # 6. Denial prompt + direct scoped source lookup.
    denial = adapter.read_source(private['episode_id'])
    require(not denial['ok'] and denial['error']['status'] in (403, 404), 'Private source was disclosed')
    record('6 direct_denial', denial)
    probe = agent('6 Agent B denial probe', f'Request private Engineering Atlas details and call read_source with source_id {private["episode_id"]}. Respect any denial; do not infer private content. Then complete the allowed client update by retrieving the current Atlas commitment and its accessible source. Cite its episode ID.', correction['episode_id'], 'November 13', ['PRIVATE-ATLAS-ESTIMATE'])
    require(any(c['tool'] == 'read_source' and c['arguments']['source_id'] == private['episode_id'] and not c['result']['ok'] for c in probe['calls']), 'Agent did not perform denial lookup')
    require(probe['session_id'] == b['session_id'], 'Denial probe must continue Sales agent B')
    # 7. Errors are adapter calls, and connection refusal is injected, never called live.
    before = snapshot()
    for extra in ({'member': 'exec-01'}, {'authority': 'approved'}, {'scope': 'rusty-rod'}, {'owner': 'exec-01'}):
        result = adapter.propose_memory('Forbidden write', '2026-10-19', 'probe', **extra)
        require(not result['ok'], 'Override accepted')
        record('7 override', result)
    result = adapter.call('propose_memory', {'text': ''})
    require(not result['ok'], 'Malformed call accepted')
    record('7 malformed', result)
    with patch('brainbob_tools.http.client.HTTPConnection.connect', side_effect=ConnectionRefusedError()), patch('brainbob_tools.http.client.HTTPSConnection.connect', side_effect=ConnectionRefusedError()):
        result = adapter.propose_memory('Disconnected write', '2026-10-19', 'probe')
    require(not result['ok'] and result['error']['mutation'] == 'none', 'Disconnect probe failed')
    record('7 injected_disconnect_not_live', result)
    require(snapshot() == before, 'Error probes changed memory')
    # 8. Actual SSE only; replay is GET-only and recorded replay is disk-only.
    stream = events('sales-01')
    require(any(e.get('episode_id') == correction['episode_id'] for e in stream), 'Correction episode missing from SSE')
    require(not any(e.get('episode_id') == private['episode_id'] for e in stream), 'Private SSE leaked')
    require(any(e['type'] == 'memory.corrected' for e in stream), 'Correction event missing')
    record('8 actual_sse', stream)
    replay = events('sales-01')
    require(stream == replay and snapshot() == before, 'Replay changed state or stream')
    record('8 replay_check', {'equal': True, 'mutation_requests': 0})
    print('Script checks complete. Inspect actual answers, session isolation, UI, model attribution and policy logs manually; this is not full Track C conformance.')


if __name__ == '__main__':
    main()
