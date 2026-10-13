# Read this agent's own MCP tool calls/results from its transcript (exact API text, no retyping).
import json, sys
T='/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/wf_ca2b546e-1d0/agent-a72fb2ff1d6cb71d1.jsonl'

def load_tr():
    calls={}; results={}; order=[]
    for line in open(T, encoding='utf-8'):
        try: e=json.loads(line)
        except Exception: continue
        msg=e.get('message') or {}
        content=msg.get('content')
        if not isinstance(content, list): continue
        for c in content:
            if not isinstance(c, dict): continue
            if c.get('type')=='tool_use':
                calls[c['id']]=(c.get('name'), c.get('input')); order.append(c['id'])
            elif c.get('type')=='tool_result':
                rc=c.get('content')
                if isinstance(rc, list):
                    txt=''.join(x.get('text','') for x in rc if isinstance(x, dict) and x.get('type')=='text')
                elif isinstance(rc, str):
                    txt=rc
                else:
                    txt=json.dumps(rc)
                results[c['tool_use_id']]=txt
    return calls, results, order

def by_reqid(reqid):
    """Return (tool_use_id, name, input, result_text) of the call whose result carries this requestId."""
    calls, results, order = load_tr()
    hits=[t for t in order if t in results and ('"requestId": "%s"' % reqid) in results[t]]
    if len(hits)!=1:
        raise KeyError('reqid %s hits %d' % (reqid, len(hits)))
    t=hits[0]
    return t, calls[t][0], calls[t][1], results[t]

if __name__=='__main__':
    calls, results, order = load_tr()
    n=int(sys.argv[1]) if len(sys.argv)>1 else 10
    for tid in order[-n:]:
        name, inp = calls[tid]
        r=results.get(tid,'')
        rid=''
        try: rid=json.loads(r).get('meta',{}).get('requestId','')
        except Exception: pass
        print(tid, (name or '').split('__')[-1], json.dumps(inp, ensure_ascii=False)[:160], '| len', len(r), '| req', rid)
