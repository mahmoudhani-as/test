# usage: python3 cmpcall.py <ad_id> <dry|live>
# Finds in THIS agent's transcript the LAST tiktok_ad_update tool_use for <ad_id> with the matching dry_run flag,
# checks its payload equals payloads.json[ad_id] exactly, saves the tool_result text to resp_<mode>_<ad>.json and summarises it.
import json, sys
T='/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/wf_72787710-74a/agent-af65adb9115dc0723.jsonl'
X='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/tt6_work2/'
ad, mode = sys.argv[1], sys.argv[2]
want_dry=(mode=='dry')
P=json.load(open(X+'payloads.json'))[ad]
pre=json.load(open(X+'pre_all.json'))[ad]
uses={}; results={}; order=[]; nall=0
for line in open(T, encoding='utf-8'):
    try: e=json.loads(line)
    except Exception: continue
    content=(e.get('message') or {}).get('content')
    if not isinstance(content,list): continue
    for c in content:
        if c.get('type')=='tool_use' and c.get('name','').endswith('tiktok_native_action'):
            inp=c.get('input') or {}
            if inp.get('action')=='tiktok_ad_update':
                crs=(inp.get('payload') or {}).get('creatives') or []
                if crs and crs[0].get('ad_id')==ad:
                    nall+=1
                    if bool(inp.get('dry_run', True))==want_dry:
                        uses[c['id']]=inp; order.append(c['id'])
        if c.get('type')=='tool_result' and c.get('tool_use_id') in uses:
            cc=c.get('content')
            txt=''.join(x.get('text','') for x in cc if isinstance(x,dict)) if isinstance(cc,list) else str(cc)
            results[c['tool_use_id']]=txt
if not order: sys.exit('no matching call found')
tid=order[-1]; inp=uses[tid]
same=inp.get('payload')==P
extra={k:v for k,v in inp.items() if k not in ('action','payload','dry_run')}
print('update calls for ad (any mode):', nall, '| calls in mode', mode, ':', len(order), '| payload_equal:', same, '| dry_run:', inp.get('dry_run'), '| extra args:', extra)
if not same:
    a=inp.get('payload') or {}
    for k in set(P['creatives'][0])|set(a.get('creatives',[{}])[0]):
        if P['creatives'][0].get(k)!=a['creatives'][0].get(k): print('DIFF', k, repr(P['creatives'][0].get(k))[:300], '!=', repr(a['creatives'][0].get(k))[:300])
    for k in set(P)|set(a):
        if k!='creatives' and P.get(k)!=a.get(k): print('DIFF top', k, P.get(k), a.get(k))
r=results.get(tid)
if r is None: print('no result yet'); sys.exit(0)
open(X+f'resp_{mode}_{ad}.json','w',encoding='utf-8').write(r)
try: j=json.loads(r)
except Exception: print('NON-JSON RESULT:', r[:3000]); sys.exit(0)
d=j.get('data') or {}
if want_dry:
    dd=d.get('data') or {}
    body=(dd.get('request') or {}).get('body')
    print('dry success:', j.get('success'), d.get('success'), '| dryRun:', d.get('dryRun'), dd.get('dryRun'), '| warnings:', dd.get('warnings'), '| preflightBlocking:', dd.get('preflightBlocking'))
    print('preview path:', (dd.get('request') or {}).get('path'), '| preview body == payload:', body==P)
    cr=(body or {}).get('creatives',[{}])[0]
    diffs=[k for k,v in cr.items() if k not in ('tracking_pixel_id',) and v!=pre.get(k)]
    print('fields differing from live pre-read:', diffs, '| pixel sent:', cr.get('tracking_pixel_id'), 'live:', pre.get('tracking_pixel_id'))
    print('fields in pre-read not sent (non-null):', sorted(k for k,v in pre.items() if k not in cr and v not in (None,'',[],'UNSET','NORMAL') and not k.startswith('_')))
else:
    dd=(d.get('data') or {})
    print('live success:', j.get('success'), d.get('success'), '| dryRun:', d.get('dryRun'), '| code:', dd.get('code'), '| message:', dd.get('message'), '| request_id:', dd.get('request_id'))
    data=dd.get('data') or {}
    print('ad_ids:', data.get('ad_ids'), '| need_audit:', data.get('need_audit'))
    for cr in data.get('creatives') or []:
        print('resp landing_page_url == new:', cr.get('landing_page_url')==P['creatives'][0]['landing_page_url'], '| modify_time:', cr.get('modify_time'), '| op:', cr.get('operation_status'),
              '| item:', cr.get('tiktok_item_id'), '| identity:', cr.get('identity_type'), cr.get('identity_id'))
        diffs=[(k,pre.get(k),v) for k,v in cr.items() if k not in ('landing_page_url','utm_params','modify_time') and v!=pre.get(k)]
        print('resp fields differing from pre-read:', diffs)
        print('resp utm_params:', [(x['key'],x['value']) for x in (cr.get('utm_params') or [])])
