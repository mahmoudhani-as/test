# Parse my own transcript to extract MCP tool calls/results (by requestId or tool_use order).
import json, sys
T='/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/wf_ab8422cb-21a/agent-af4f9abd2a0e1dddb.jsonl'

def load():
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
                else:
                    txt=rc if isinstance(rc,str) else json.dumps(rc)
                results[c['tool_use_id']]=txt
    return calls, results, order

def by_request_id(rid):
    calls, results, order = load()
    for tid in order:
        r=results.get(tid,'')
        if rid in r:
            return tid, calls[tid], r
    return None

if __name__=='__main__':
    rid=sys.argv[1]
    x=by_request_id(rid)
    if not x: print('NOT FOUND'); sys.exit(1)
    tid,(name,inp),r=x
    print(tid, name, json.dumps(inp)[:300]); print(len(r))
