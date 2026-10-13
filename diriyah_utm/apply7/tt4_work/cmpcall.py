# usage: python3 -I cmpcall.py <ad_id> <dry|live>
# Finds in this agent's transcript the LAST tiktok_ad_update tool_use for <ad_id> with that dry_run flag, checks its payload
# == payload_<ad_id>.json exactly, saves its tool_result to resp_<mode>_<ad_id>.json and summarises it.
import json, sys
sys.path.insert(0,'/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply7/tt4_work')
from common import *
ad, mode = sys.argv[1], sys.argv[2]; want_dry=(mode=='dry')
P=json.load(open(T+f'payload_{ad}.json'))
uses={}; order=[]
for c in tool_uses():
    if c.get('name','').endswith('tiktok_native_action'):
        inp=c.get('input') or {}
        if inp.get('action')=='tiktok_ad_update':
            crs=(inp.get('payload') or {}).get('creatives') or []
            if crs and crs[0].get('ad_id')==ad and bool(inp.get('dry_run',True))==want_dry:
                uses[c['id']]=inp; order.append(c['id'])
results={i:t for i,t in tool_results() if i in uses}
if not order: sys.exit('no matching call found')
print('calls found:',len(order))
tid=order[-1]; inp=uses[tid]
same=inp.get('payload')==P
extra={k:v for k,v in inp.items() if k not in ('action','payload','dry_run')}
print('payload_equal:',same,'dry_run:',inp.get('dry_run'),'other args:',extra)
if not same:
    a=inp.get('payload')
    for k in set(P['creatives'][0])|set(a['creatives'][0]):
        if P['creatives'][0].get(k)!=a['creatives'][0].get(k): print('DIFF',k,repr(P['creatives'][0].get(k))[:300],'!=',repr(a['creatives'][0].get(k))[:300])
    for k in set(P)|set(a):
        if k!='creatives' and P.get(k)!=a.get(k): print('DIFF top',k,P.get(k),a.get(k))
r=results.get(tid)
if r is None: print('no result yet'); sys.exit(0)
open(T+f'resp_{mode}_{ad}.json','w',encoding='utf-8').write(r)
try: j=json.loads(r)
except Exception: print('NON-JSON RESULT:', r[:3000]); sys.exit(0)
if not j.get('success'):
    print('ERROR RESULT:', json.dumps(j,ensure_ascii=False)[:3000]); sys.exit(0)
d=j.get('data',{})
if want_dry:
    body=d['data']['request']['body']
    print('dryRun:',d.get('dryRun'),'| preview body == payload:',body==P,'| warnings:',d['data'].get('warnings'),'| preflightBlocking:',d['data'].get('preflightBlocking'))
    if body!=P:
        for k in set(P['creatives'][0])|set(body['creatives'][0]):
            if P['creatives'][0].get(k)!=body['creatives'][0].get(k): print('PREVIEW DIFF',k,repr(P['creatives'][0].get(k))[:300],'!=',repr(body['creatives'][0].get(k))[:300])
        for k in set(P)|set(body):
            if k!='creatives' and P.get(k)!=body.get(k): print('PREVIEW DIFF top',k,P.get(k),body.get(k))
else:
    dd=d.get('data',{})
    print('dryRun:',d.get('dryRun'),'| code:',dd.get('code'),'| message:',dd.get('message'),'| request_id:',dd.get('request_id'))
    data=dd.get('data') or {}
    print('ad_ids:',data.get('ad_ids'),'need_audit:',data.get('need_audit'))
    for cr in data.get('creatives') or []:
        print('resp landing_page_url == payload:', cr.get('landing_page_url')==P['creatives'][0]['landing_page_url'], '| modify_time', cr.get('modify_time'),
              '| ad_text == payload:', cr.get('ad_text')==P['creatives'][0].get('ad_text'), '| ad_text == payload.rstrip():', cr.get('ad_text')==(P['creatives'][0].get('ad_text') or '').rstrip())
    print('meta:', json.dumps(d.get('meta'),ensure_ascii=False))
