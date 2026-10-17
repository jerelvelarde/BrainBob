"""pytest-compatible unittest suite: fake HTTP connections, no sockets."""
import copy
import http.client
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brainbob_tools import BrainBobTools


class FakeHTTP:
    records = []
    requests = []
    status = 200
    disconnected = False
    bad_json = False

    def __init__(self, *args, **kwargs):
        pass

    def connect(self):
        if self.disconnected:
            raise ConnectionRefusedError()

    def request(self, method, path, body, headers):
        self.requests.append((method, path, json.loads(body) if body else None, headers))
        visible = [m for m in self.records if m['scope'] == 'rusty-rod' or m['scope'] == 'rusty-rod/sales']
        self.data = visible
        if path.startswith('/episodes/'):
            self.data = {'id': 'ep-1', 'text': 'Atlas source'}
        if method == 'POST' and self.status == 200:
            m = {'id': 'new', 'text': json.loads(body)['text'], 'scope': 'rusty-rod/sales'}
            self.records.append(m)
            self.data = {'episode_id': 'ep-new', 'memories': [m]}

    def getresponse(self):
        return self

    def read(self):
        return b'bad' if self.bad_json else json.dumps(self.data).encode()

    def close(self):
        pass


class AdapterTests(unittest.TestCase):
    def setUp(self):
        FakeHTTP.records = [
            {'id': 'b', 'text': 'Atlas launch', 'scope': 'rusty-rod', 'status': 'trial', 'origin': 'ep-1'},
            {'id': 'a', 'text': 'Atlas launch', 'scope': 'rusty-rod/sales', 'revision': 2, 'supersedes': None},
            {'id': 'secret', 'text': 'Atlas private', 'scope': 'rusty-rod/engineering'},
        ]
        FakeHTTP.requests = []
        FakeHTTP.status, FakeHTTP.disconnected, FakeHTTP.bad_json = 200, False, False
        self.env = patch.dict(os.environ, BRAINBOB_MEMBER='sales-01', BRAINBOB_URL='http://localhost:3001')
        self.env.start()
        self.addCleanup(self.env.stop)
        self.http = patch('brainbob_tools.http.client.HTTPConnection', FakeHTTP)
        self.http.start()
        self.addCleanup(self.http.stop)
        self.tools = BrainBobTools()

    def test_scoped_ranked_projection(self):
        result = self.tools.read_memory('Atlas', 2)
        self.assertEqual([m['id'] for m in result['memories']], ['a', 'b'])
        self.assertNotIn('date', result['memories'][0])
        self.assertNotIn('revision', result['memories'][1])
        self.assertIsNone(result['memories'][0]['supersedes'])
        self.assertEqual(self.tools.read_memory('unmatched', 2)['memories'], [])
        self.assertEqual(len(self.tools.read_memory('Atlas', 1)['memories']), 1)
        self.assertEqual(FakeHTTP.requests[0][3]['X-BrainBob-Member'], 'sales-01')

    def test_http_errors_no_retry_or_mutation(self):
        before = copy.deepcopy(FakeHTTP.records)
        for status in (401, 403, 404, 500):
            FakeHTTP.status = status
            for name, args in [('read_source', {'source_id': 'private'}),
                               ('propose_memory', {'text': 'x', 'date': '2026-10-17', 'source': 'x'})]:
                count = len(FakeHTTP.requests)
                result = self.tools.call(name, args)
                self.assertEqual(result['error']['status'], status)
                self.assertEqual(len(FakeHTTP.requests), count + 1)
                self.assertEqual(FakeHTTP.records, before)

    def test_extra_fields_rejected_before_network(self):
        for field in ('member', 'author', 'owner', 'scope', 'authority', 'headers', 'X-BrainBob-Member', 'url'):
            self.assertFalse(self.tools.propose_memory('approved x', '2026-10-17', 'x', **{field: 'exec-01'})['ok'])
            self.assertFalse(self.tools.read_memory('Atlas', 1, **{field: 'x'})['ok'])
            self.assertFalse(self.tools.read_source('ep-1', **{field: 'x'})['ok'])
        self.assertEqual(FakeHTTP.requests, [])
        self.assertEqual(len(FakeHTTP.records), 3)

    def test_discussion_and_host_identity_snapshot(self):
        os.environ['BRAINBOB_MEMBER'] = 'exec-01'
        result = self.tools.propose_memory('APPROVED launch', '2026-10-17', 'chat')
        self.assertTrue(result['ok'])
        method, path, body, headers = FakeHTTP.requests[0]
        self.assertEqual((method, path), ('POST', '/episodes'))
        self.assertEqual(body, {'text': 'APPROVED launch', 'date': '2026-10-17', 'source': 'chat', 'authority': 'discussion'})
        self.assertEqual(headers['X-BrainBob-Member'], 'sales-01')

    def test_malformed_no_network(self):
        for args in (None, [], {}, {'task': 'x', 'limit': True}, {'task': '', 'limit': 1}, {'task': 'x', 'limit': '2'}, {'task': 'x', 'limit': 101}):
            self.assertFalse(self.tools.call('read_memory', args)['ok'])
        for date in ('2026-02-30', '20261017', ''):
            self.assertFalse(self.tools.propose_memory('x', date, 'x')['ok'])
        self.assertFalse(self.tools.call('unknown', {})['ok'])
        self.assertEqual(FakeHTTP.requests, [])
        self.assertEqual(len(FakeHTTP.records), 3)

    def test_disconnected_no_mutation(self):
        FakeHTTP.disconnected = True
        before = copy.deepcopy(FakeHTTP.records)
        result = self.tools.propose_memory('x', '2026-10-17', 'x')
        self.assertEqual(result['error']['mutation'], 'none')
        self.assertEqual(result['error']['code'], 'backend_unavailable')
        self.assertEqual(FakeHTTP.requests, [])
        self.assertEqual(FakeHTTP.records, before)

    def test_invalid_json_read_and_source_path(self):
        FakeHTTP.bad_json = True
        self.assertFalse(self.tools.read_source('../x?member=exec-01')['ok'])
        self.assertEqual(FakeHTTP.requests[0][1], '/episodes/..%2Fx%3Fmember%3Dexec-01')
        self.assertEqual(len(FakeHTTP.records), 3)

    def test_configuration_no_mutation(self):
        for url in ('http://user:secret@localhost:3001', 'file:///tmp/a', 'http://localhost:3001?member=exec-01'):
            os.environ['BRAINBOB_URL'] = url
            self.assertFalse(BrainBobTools().read_memory('Atlas', 1)['ok'])
        self.assertEqual(FakeHTTP.requests, [])

    def test_lost_post_response_is_unknown_and_never_retried(self):
        # A backend can commit before its response is lost. Never promise rollback.
        with patch.object(FakeHTTP, 'getresponse', side_effect=http.client.RemoteDisconnected()):
            result = self.tools.propose_memory('x', '2026-10-17', 'x')
        self.assertEqual(result['error']['mutation'], 'unknown')
        self.assertEqual(len(FakeHTTP.requests), 1)
        self.assertEqual(len(FakeHTTP.records), 4)

    def test_invalid_read_response_is_structured_without_mutation(self):
        with patch.object(FakeHTTP, 'read', return_value=b'{"unexpected":true}'):
            result = self.tools.read_memory('Atlas', 2)
        self.assertEqual(result['error']['code'], 'invalid_response')
        self.assertEqual(len(FakeHTTP.records), 3)


if __name__ == '__main__':
    unittest.main()
