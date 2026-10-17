import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from pathlib import Path
from datetime import datetime,timezone
base='http://127.0.0.1:3001'
dataset=json.loads(Path('fixtures/company/rusty-rod.json').read_text())
def get(member,path,body=None):
 req=Request(base+path,headers={'X-BrainBob-Member':member,'Content-Type':'application/json'},data=json.dumps(body).encode() if body else None)
 try:
  with urlopen(req,timeout=60) as r:return r.status,json.load(r)
 except HTTPError as e:return e.code,None
def stream(member):
 out=[]
 with urlopen(Request(base+'/events?member='+member),timeout=30) as r:
  for raw in r:
   if not raw.startswith(b'data:'):continue
   e=json.loads(raw[5:])
   if e['type']=='replay.done':return out,e['seq']
   out.append(e)
 raise AssertionError('No replay boundary')
def allowed(member,scope):
 team=next(p['team'] for p in dataset['members'] if p['id']==member)
 return scope in ['rusty-rod','rusty-rod/'+team,'rusty-rod/'+team+'/'+member]
allmem={}; views={}; checks=[]
for p in dataset['members']:
 status,memories=get(p['id'],'/memories'); assert status==200
 assert all(allowed(p['id'],m['scope']) for m in memories)
 views[p['id']]=memories
 allmem.update({m['id']:m for m in memories})
 checks.append({'member':p['id'],'visible_memories':len(memories),'scope_filter':'passed'})
for p in dataset['members']:
 events,seq=stream(p['id'])
 for e in events:
  ids=[e.get(k) for k in ['memory_id','old_id','new_id']]+list(e.get('memory_ids',[]))+list(e.get('cited_ids',[]))
  if 'memory' in e:ids.append(e['memory']['id'])
  assert all(allowed(p['id'],allmem[mid]['scope']) for mid in ids if mid)
  if e['type'] in ['memory.retrieved','answer.produced']: assert e['viewer']==p['id']
 checks.append({'member':p['id'],'replayed_events':len(events),'event_reference_filter':'passed','cursor':seq})
private=next(m for m in views['exec-01'] if m['scope']=='rusty-rod/executive')
assert get('sales-01','/episodes/'+private['origin'])[0]==404
assert get('sales-01','/memories/'+private['id']+'/history')[0]==404
assert get('sales-01','/episodes',{'text':'Access boundary test: this must never be ingested.','scope':'rusty-rod/executive','author':'sales-01'})[0]==403
assert get('sales-01','/episodes',{'text':'Access boundary test: this must never be ingested.','scope':'rusty-rod','author':'exec-01'})[0]==403
result={'captured_at':datetime.now(timezone.utc).isoformat(),'backend':base,'checks':checks,'cross_team_source':404,'cross_team_history':404,'cross_team_write':403,'impersonated_author_write':403,'note':'Selected-identity authorization checks only. Member headers are not production authentication. Events were checked through replay.done; this does not exhaustively prove live-stream isolation.'}
Path('judging/live-workspace-20261017/access-checks.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS: 18 identity memory views and event replays; private source/history blocked; unauthorized writes blocked.')
