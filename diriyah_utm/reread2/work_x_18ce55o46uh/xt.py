# Extract x_ads_native_action tool results from this agent's own transcript.
# usage: python3 xt.py <label> <tool_use_id|last|lastN>   -> writes raw/<label>.json (list of {input, result})
import json, sys, os
T='/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/wf_a4323da7-858/agent-a4bed0439821e1244.jsonl'
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'raw')
uses={}; order=[]; results={}
for l in open(T):
    try: o=json.loads(l)
    except Exception: continue
    c=(o.get('message') or {}).get('content')
    if not isinstance(c,list): continue
    for p in c:
        if p.get('type')=='tool_use' and 'x_ads_native_action' in (p.get('name') or ''):
            if p['id'] not in uses:
                uses[p['id']]=p.get('input'); order.append(p['id'])
        elif p.get('type')=='tool_result' and p.get('tool_use_id') in uses:
            cc=p.get('content')
            if isinstance(cc,list):
                txt=''.join(x.get('text','') for x in cc if isinstance(x,dict))
            else:
                txt=cc if isinstance(cc,str) else json.dumps(cc)
            results[p['tool_use_id']]=txt
label=sys.argv[1]; sel=sys.argv[2]
if sel.startswith('last'):
    n=int(sel[4:] or 1)
    ids=[i for i in order if i in results][-n:]
else:
    ids=sel.split(',')
out=[]
for i in ids:
    txt=results.get(i)
    try: res=json.loads(txt)
    except Exception: res={'_unparsed':txt}
    out.append({'tool_use_id':i,'input':uses[i],'result':res})
json.dump(out,open(os.path.join(OUT,label+'.json'),'w'),indent=1)
for o in out:
    r=o['result']
    trunc=json.dumps(r.get('meta',{}).get('mcp_output_budget',{})) if isinstance(r,dict) else ''
    print(o['tool_use_id'], json.dumps(o['input'])[:200], 'success=',r.get('success') if isinstance(r,dict) else None, 'budget=',trunc[:200])
