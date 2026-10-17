"""Six public structured worlds. Gold is stripped before calls to candidate adapters."""
import json
from pathlib import Path


def fact(sid, key, value, scope='org', actor='exec', approved=True, depends_on=None):
    return dict(type='fact', id=sid, key=key, value=value, scope=scope,
                actor=actor, approved=approved, depends_on=depends_on or [])


def check(cid, principal, keys, claims, allowed, stratum='legitimate'):
    return dict(type='checkpoint', id=cid, principal=principal, keys=keys,
                gold={'claims': [dict(key=k, value=v, source_id=s) for k, v, s in claims],
                      'allowed_sources': allowed, 'stratum': stratum})


def world(wid, steps):
    return dict(id=wid, policy={
        'readers': {'org': ['exec', 'sales', 'eng'], 'sales': ['sales'],
                    'personal': ['sales'], 'eng': ['eng'], 'client': ['client']},
        'approvers': {'org': ['exec'], 'sales': ['sales'], 'personal': ['sales'],
                      'eng': ['eng'], 'client': ['publisher']}}, steps=steps)


WORLDS = [
    world('scoped-assembly', [
        fact('s1', 'launch', '2026-11-06'),
        fact('s2', 'format', 'bullets', 'personal', 'sales'),
        fact('s3', 'tone', 'concise', 'sales', 'sales'),
        fact('s4', 'private-code', 'cedar-731', 'eng', 'eng'),
        check('assembly', 'sales', ['launch', 'format', 'tone'],
              [('launch', '2026-11-06', 's1'), ('format', 'bullets', 's2'), ('tone', 'concise', 's3')], ['s1', 's2', 's3']),
        check('private-denied', 'sales', ['private-code'], [], ['s1', 's2', 's3'], 'boundary'),
        check('private-allowed', 'eng', ['private-code'], [('private-code', 'cedar-731', 's4')], ['s1', 's4']),
    ]),
    world('authority-change', [
        fact('a1', 'launch', '2026-11-06'),
        fact('a2', 'launch', '2026-11-13', 'org', 'eng', False),
        check('tentative', 'sales', ['launch'], [('launch', '2026-11-06', 'a1')], ['a1', 'a2']),
        fact('a3', 'launch', '2026-11-13', 'org', 'sales', True),
        check('forged-approval', 'sales', ['launch'], [('launch', '2026-11-06', 'a1')], ['a1', 'a2', 'a3'], 'boundary'),
        fact('a4', 'launch', '2026-11-13'),
        check('approved-correction', 'sales', ['launch'], [('launch', '2026-11-13', 'a4')], ['a1', 'a2', 'a3', 'a4']),
    ]),
    world('cross-org-publication', [
        fact('p1', 'launch', '2026-11-13'),
        fact('p2', 'margin', '42 percent', 'sales', 'sales'),
        check('before-publication', 'client', ['launch'], [], [], 'boundary'),
        fact('p3', 'launch', '2026-11-13', 'client', 'publisher', depends_on=['p1']),
        check('published', 'client', ['launch'], [('launch', '2026-11-13', 'p3')], ['p3']),
        check('private-margin', 'client', ['margin'], [], ['p3'], 'boundary'),
    ]),
    world('revocation', [
        fact('r1', 'contact', 'support@atlas.example'),
        fact('r2', 'sales-code', 'violet-204', 'sales', 'sales'),
        check('before-revoke', 'sales', ['sales-code'], [('sales-code', 'violet-204', 'r2')], ['r1', 'r2']),
        dict(type='revoke', scope='sales', principal='sales'),
        check('after-revoke', 'sales', ['sales-code'], [], ['r1'], 'boundary'),
        check('still-allowed', 'sales', ['contact'], [('contact', 'support@atlas.example', 'r1')], ['r1']),
    ]),
    world('conflict-retention', [
        fact('c1', 'goal', 'reduce response time'),
        fact('c2', 'budget', 'USD 12000'),
        fact('c3', 'budget', 'USD 15000', 'org', 'eng', False),
        dict(type='audit', source_ids=['c3']),
        check('retain-old', 'sales', ['goal'], [('goal', 'reduce response time', 'c1')], ['c1', 'c2', 'c3']),
        check('retain-approved', 'sales', ['budget'], [('budget', 'USD 12000', 'c2')], ['c1', 'c2', 'c3']),
        fact('c4', 'forecast', 'USD 9000', 'eng', 'eng', False),
        check('uncertain', 'eng', ['forecast'], [], ['c1', 'c2', 'c3', 'c4'], 'boundary'),
    ]),
    world('correction-propagation', [
        fact('d1', 'launch', '2026-11-06'),
        fact('d2', 'summary-launch', '2026-11-06', 'client', 'publisher', depends_on=['d1']),
        check('summary-initial', 'client', ['summary-launch'], [('summary-launch', '2026-11-06', 'd2')], ['d2']),
        fact('d3', 'launch', '2026-11-13'),
        check('invalidate-stale', 'client', ['summary-launch'], [], ['d2'], 'maintenance'),
        fact('d4', 'summary-launch', '2026-11-13', 'client', 'publisher', depends_on=['d3']),
        check('summary-corrected', 'client', ['summary-launch'], [('summary-launch', '2026-11-13', 'd4')], ['d2', 'd4']),
    ]),
]

if __name__ == '__main__':
    (Path(__file__).parent / 'worlds.json').write_text(json.dumps(WORLDS, indent=2) + '\n')
