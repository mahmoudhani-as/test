# usage: python3 -I cmpcall.py <ad_id> <dry|live> [action]
# Finds in my transcript the LAST update tool_use for <ad_id> with that dry_run flag, checks its payload == payload_<ad_id>.json exactly,
# saves its tool_result to resp_<mode>_<ad_id>.json and summarises it.
import json, sys
sys.path.insert(0,'/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply7/tt6_work')
from common import *
ad, mode = sys.argv[1], sys.argv[2]; want_dry=(mode=='dry')
P=json.load(open(T+f'payload_{ad}.json'))
def ad_of(inp):
    p=inp.get('payload') or {}
    if inp.get('action')=='tiktok_ad_update':
        crs=p.get('creatives') or []
        return crs[0].get('ad_id') if crs else None
    if inp.get('action')=='tiktok_smart_plus_ad_update':
        return p.get('smart_plus_ad_id')
uses={}; order=[]
for tid,inp in tool_uses():
    if inp.get('action') in ('tiktok_ad_update','tiktok_smart_plus_ad_update') and ad_of(inp)==ad and bool(inp.get('dry_run',True))==want_dry:
        uses[tid]=inp; order.append(tid)
if not order: sys.exit('no matching call found')
tid=order[-1]; inp=uses[tid]
results={t:x for t,x in tool_results() if t in uses}
same=inp.get('payload')==P
extra={k:v for k,v in inp.items() if k not in ('action','payload','dry_run')}
print('calls found:',len(order),'| payload_equal:',same,'| dry_run:',inp.get('dry_run'),'| action:',inp.get('action'),'| other args:',extra)
def diff(a,b,path=''):
    if isinstance(a,dict) and isinstance(b,dict):
        for k in sorted(set(a)|set(b)): diff(a.get(k,'<absent>'),b.get(k,'<absent>'),path+'.'+k)
    elif a!=b: print('DIFF',path,repr(a)[:300],'!=',repr(b)[:300])
if not same: diff(P, inp.get('payload'))
r=results.get(tid)
if r is None: print('no result yet'); sys.exit(0)
open(T+f'resp_{mode}_{ad}.json','w',encoding='utf-8').write(r)
try: j=json.loads(r)
except Exception: print('NON-JSON RESULT:', r[:3000]); sys.exit(0)
d=j.get('data',{})
if not j.get('success'): print('ERROR RESULT:', r[:3000]); sys.exit(0)
if want_dry:
    body=d['data']['request']['body']
    print('dryRun:',d.get('dryRun'),'| path:',d['data']['request']['path'],'| preview body == payload:',body==P,'| warnings:',d['data'].get('warnings'),'| preflightBlocking:',d['data'].get('preflightBlocking'))
    if body!=P: diff(P, body)
else:
    dd=d.get('data',{})
    print('dryRun:',d.get('dryRun'),'| code:',dd.get('code'),'| message:',dd.get('message'),'| request_id:',dd.get('request_id'))
    data=dd.get('data') or {}
    print('data keys:', list(data.keys())[:30])
    print('ad_ids:',data.get('ad_ids'),'need_audit:',data.get('need_audit'))
    for cr in data.get('creatives') or []:
        print('resp landing_page_url == payload:', cr.get('landing_page_url')==P['creatives'][0]['landing_page_url'], '| modify_time', cr.get('modify_time'), '| ad_text == payload:', cr.get('ad_text')==P['creatives'][0].get('ad_text'))
    print('meta:', json.dumps(d.get('meta'),ensure_ascii=False))
