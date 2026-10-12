# usage: python3 cmpcall.py <ad_id> <dry|live>
# Finds, in this agent's transcript, the LAST tiktok_ad_update tool_use for <ad_id> with matching dry_run flag,
# checks its payload equals payloads.json[ad_id] exactly, and saves/prints the matching tool_result.
import json, sys
T='/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/wf_cb294060-2b1/agent-a5d13d24efcf7b84a.jsonl'
W='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/tt10_work/'
ad, mode = sys.argv[1], sys.argv[2]
want_dry = (mode=='dry')
P=json.load(open(W+'payloads.json'))[ad]
uses={}; results={}; order=[]
for line in open(T, encoding='utf-8'):
    try: e=json.loads(line)
    except Exception: continue
    content=(e.get('message') or {}).get('content')
    if not isinstance(content,list): continue
    for c in content:
        if not isinstance(c,dict): continue
        if c.get('type')=='tool_use' and c.get('name','').endswith('tiktok_native_action'):
            inp=c.get('input') or {}
            if inp.get('action')=='tiktok_ad_update':
                pl=inp.get('payload') or {}
                crs=pl.get('creatives') or []
                if crs and crs[0].get('ad_id')==ad and bool(inp.get('dry_run', True))==want_dry:
                    uses[c['id']]=inp; order.append(c['id'])
        if c.get('type')=='tool_result' and c.get('tool_use_id') in uses:
            cc=c.get('content')
            txt=''.join(x.get('text','') for x in cc if isinstance(x,dict)) if isinstance(cc,list) else str(cc)
            results[c['tool_use_id']]=txt
if not order: sys.exit('no matching call found')
tid=order[-1]; inp=uses[tid]
same = inp.get('payload')==P
extra = {k:v for k,v in inp.items() if k not in ('action','payload','dry_run')}
print('calls found:', len(order), 'last id:', tid, 'payload_equal:', same, 'dry_run:', inp.get('dry_run'), 'other args:', extra)
if not same:
    a=inp.get('payload')
    for k in set(P['creatives'][0])|set(a['creatives'][0]):
        if P['creatives'][0].get(k)!=a['creatives'][0].get(k): print('DIFF', k, repr(P['creatives'][0].get(k))[:300], '!=', repr(a['creatives'][0].get(k))[:300])
    for k in set(P)|set(a):
        if k!='creatives' and P.get(k)!=a.get(k): print('DIFF top', k, P.get(k), a.get(k))
r=results.get(tid)
if r is None: print('no result yet'); sys.exit(0)
open(W+f'resp_{mode}_{ad}.json','w',encoding='utf-8').write(r)
print('result saved', len(r))
try:
    j=json.loads(r)
except Exception:
    print(r[:3000]); sys.exit(0)
print(json.dumps(j, ensure_ascii=False)[:3000])
