# Extract snapchat_native_action tool results from this agent's own transcript.
# usage: python3 -I xt.py <label> <tool_use_id,...|last|lastN>   -> writes raw/<label>.json (list of {tool_use_id, input, result})
import json, sys, os, re
T='/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/wf_80cb2e13-cbd/agent-a511e18db19c7643d.jsonl'
OUT=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'raw')
uses={}; order=[]; results={}
for l in open(T):
    try: o=json.loads(l)
    except Exception: continue
    c=(o.get('message') or {}).get('content')
    if not isinstance(c,list): continue
    for p in c:
        if not isinstance(p,dict): continue
        if p.get('type')=='tool_use' and 'snapchat_native_action' in (p.get('name') or ''):
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
    res=None
    try: res=json.loads(txt)
    except Exception:
        m=re.search(r'(/[^\s"\']+\.(?:json|txt))', txt or '')
        if m and os.path.exists(m.group(1)):
            raw=open(m.group(1)).read()
            try:
                res=json.loads(raw)
                if isinstance(res,list) and res and isinstance(res[0],dict) and 'text' in res[0]:
                    res=json.loads(''.join(x.get('text','') for x in res))
            except Exception:
                res={'_unparsed_file':m.group(1)}
        else:
            res={'_unparsed':(txt or '')[:2000]}
    out.append({'tool_use_id':i,'input':uses[i],'result':res})
json.dump(out,open(os.path.join(OUT,label+'.json'),'w'),indent=1)
for o in out:
    r=o['result']
    d=(r.get('data') or {}) if isinstance(r,dict) else {}
    dd=(d.get('data') or {}) if isinstance(d,dict) else {}
    info={k:(len(v) if isinstance(v,list) else None) for k,v in dd.items() if isinstance(v,list)} if isinstance(dd,dict) else {}
    pg=dd.get('paging') if isinstance(dd,dict) else None
    trunc=(r.get('meta') or {}).get('mcp_output_budget') if isinstance(r,dict) else None
    print(o['tool_use_id'], json.dumps(o['input'])[:200], '| success=',r.get('success') if isinstance(r,dict) else None, '| lists=',info, '| paging=',pg, '| budget=',trunc)
