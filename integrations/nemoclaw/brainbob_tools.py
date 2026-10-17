"""Written, unit-tested against a fake backend, NOT yet run inside a NemoClaw sandbox."""
from __future__ import annotations

import datetime
import http.client
import json
import os
import re
from urllib.parse import quote, urlsplit

FIELDS = ('id', 'text', 'status', 'date', 'scope', 'origin', 'source', 'supersedes', 'revision')


def obj(properties, required):
    return {'type': 'object', 'properties': properties, 'required': required,
            'additionalProperties': False}


STRING = {'type': 'string', 'minLength': 1}
INPUT_SCHEMAS = {
    'read_memory': obj({'task': STRING, 'limit': {'type': 'integer', 'minimum': 1, 'maximum': 100}}, ['task', 'limit']),
    'read_source': obj({'source_id': STRING}, ['source_id']),
    'propose_memory': obj({'text': STRING, 'date': {'type': 'string', 'format': 'date'}, 'source': STRING}, ['text', 'date', 'source']),
}
RECORD_SCHEMA = obj({k: ({'type': ['string', 'null']} if k == 'supersedes' else
                         {'type': ['string', 'integer', 'null']} if k == 'revision' else
                         {'type': 'string'}) for k in FIELDS}, ['id', 'text'])
ERROR_SCHEMA = obj({'code': STRING, 'message': STRING, 'status': {'type': 'integer'},
                    'mutation': {'enum': ['none', 'unknown']}}, ['code', 'message', 'mutation'])
OUTPUT_SCHEMAS = {
    name: {'type': 'object', 'oneOf': [
        obj({'ok': {'const': True}, **props}, ['ok', *props]),
        obj({'ok': {'const': False}, 'error': ERROR_SCHEMA}, ['ok', 'error'])]}
    for name, props in {
        'read_memory': {'memories': {'type': 'array', 'items': RECORD_SCHEMA}},
        'read_source': {'source': {'type': 'object'}},
        'propose_memory': {'episode_id': STRING, 'memories': {'type': 'array', 'items': RECORD_SCHEMA}},
    }.items()
}


def error(code, message, status=None, mutation='none'):
    detail = {'code': code, 'message': message, 'mutation': mutation}
    if status is not None:
        detail['status'] = status
    return {'ok': False, 'error': detail}


def request_json(base_url, member, method, path, body=None):
    """One request, no redirects/retries/proxies. Never echo response error bodies."""
    url = urlsplit(base_url)
    if url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password or url.query or url.fragment or url.path not in ('', '/'):
        raise ValueError('BRAINBOB_URL must be an HTTP(S) origin without credentials')
    conn_type = http.client.HTTPSConnection if url.scheme == 'https' else http.client.HTTPConnection
    conn = conn_type(url.hostname, url.port, timeout=15)
    sent = False
    try:
        # Connect explicitly so a refused connection is distinguishable from an ambiguous write.
        conn.connect()
        sent = True
        conn.request(method, path, body=json.dumps(body) if body is not None else None,
                     headers={'X-BrainBob-Member': member, 'Content-Type': 'application/json'})
        response = conn.getresponse()
        if not 200 <= response.status < 300:
            return error('http_error', 'Backend rejected request', response.status,
                         'unknown' if method == 'POST' and response.status >= 500 else 'none')
        data = json.loads(response.read())
        return {'ok': True, 'data': data}
    except (OSError, http.client.HTTPException, ValueError):
        return error('backend_unavailable', 'Backend unavailable or invalid response; no retry',
                     mutation='unknown' if sent and method == 'POST' else 'none')
    finally:
        conn.close()


class BrainBobTools:
    def __init__(self):
        # Snapshot host environment once; callers cannot replace identity via tool arguments.
        self._member = os.environ.get('BRAINBOB_MEMBER', '')
        self._url = os.environ.get('BRAINBOB_URL', '')

    def call(self, name, arguments):
        schema = INPUT_SCHEMAS.get(name)
        if schema is None or not isinstance(arguments, dict):
            return error('invalid_arguments', 'Unknown tool or non-object arguments')
        if set(arguments) != set(schema['required']):
            return error('invalid_arguments', 'Only the declared required fields are accepted')
        for key, value in arguments.items():
            if key == 'limit':
                if type(value) is not int or not 1 <= value <= 100:
                    return error('invalid_arguments', 'limit must be an integer from 1 to 100')
            elif not isinstance(value, str) or not value.strip():
                return error('invalid_arguments', 'Expected nonempty strings')
        if name == 'propose_memory':
            try:
                if datetime.date.fromisoformat(arguments['date']).isoformat() != arguments['date']:
                    raise ValueError()
            except ValueError:
                return error('invalid_arguments', 'date must be YYYY-MM-DD')
        if not self._member or not self._url or any(c in self._member for c in '\r\n'):
            return error('configuration_error', 'Host must configure BRAINBOB_MEMBER and BRAINBOB_URL')
        method, path, body = 'GET', '/memories', None
        if name == 'read_source':
            path = '/episodes/' + quote(arguments['source_id'], safe='')
        elif name == 'propose_memory':
            method, path = 'POST', '/episodes'
            body = dict(arguments, authority='discussion')
        try:
            result = request_json(self._url, self._member, method, path, body)
        except (ValueError, OSError, http.client.HTTPException):
            return error('configuration_error', 'Invalid host configuration or unavailable transport')
        if not result['ok']:
            return result
        data = result['data']
        try:
            if name == 'read_source':
                if not isinstance(data, dict) or not isinstance(data.get('id'), str):
                    raise ValueError()
                return {'ok': True, 'source': data}
            records = data if name == 'read_memory' else data['memories']
            if not isinstance(records, list) or any(not isinstance(m, dict) or not isinstance(m.get('id'), str) or not isinstance(m.get('text'), str) for m in records):
                raise ValueError()
            if name == 'read_memory':
                words = set(re.findall(r'\w+', arguments['task'].casefold()))
                def score(m):
                    return len(words & set(re.findall(r'\w+', m['text'].casefold())))
                records = sorted((m for m in records if score(m)), key=lambda m: (-score(m), m['id']))[:arguments['limit']]
            output = {'ok': True, 'memories': [{k: m[k] for k in FIELDS if k in m} for m in records]}
            if name == 'propose_memory':
                if not isinstance(data['episode_id'], str) or not data['episode_id']:
                    raise ValueError()
                output['episode_id'] = data['episode_id']
            return output
        except (KeyError, TypeError, ValueError):
            return error('invalid_response', 'Unexpected backend response; no retry',
                         mutation='unknown' if method == 'POST' else 'none')

    def read_memory(self, task=None, limit=None, **extra):
        return self.call('read_memory', dict(task=task, limit=limit, **extra))

    def read_source(self, source_id=None, **extra):
        return self.call('read_source', dict(source_id=source_id, **extra))

    def propose_memory(self, text=None, date=None, source=None, **extra):
        return self.call('propose_memory', dict(text=text, date=date, source=source, **extra))
