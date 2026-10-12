# Read MCP tool calls/results from a transcript (default: my own).
# usage: python3 tr.py list [N] [transcript]  | python3 tr.py dump <tool_use_id> <outfile> [transcript]
import json, sys
MINE='/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/wf_438dd2ce-50a/agent-ab9d6df4d9c0896f7.jsonl'
def load(T=MINE):
    calls={}; order=[]; results={}
    for line in open(T):
        try: e=json.loads(line)
        except Exception: continue
        msg=e.get('message') or {}
        content=msg.get('content')
        if not isinstance(content, list): continue
        for c in content:
            if not isinstance(c, dict): continue
            if c.get('type')=='tool_use':
                if c['id'] not in calls: order.append(c['id'])
                calls[c['id']]=(c.get('name'), c.get('input'))
            elif c.get('type')=='tool_result':
                rc=c.get('content')
                if isinstance(rc, list):
                    txt=''.join(x.get('text','') for x in rc if isinstance(x, dict) and x.get('type')=='text')
                else:
                    txt=rc if isinstance(rc,str) else json.dumps(rc)
                results[c['tool_use_id']]=txt
    return calls, order, results
if __name__=='__main__':
    cmd=sys.argv[1]
    if cmd=='list':
        n=int(sys.argv[2]) if len(sys.argv)>2 else 10
        T=sys.argv[3] if len(sys.argv)>3 else MINE
        calls, order, results = load(T)
        for i in order[-n:]:
            name,inp=calls[i]
            print(i, name, json.dumps(inp, ensure_ascii=False)[:400], 'RESULT_LEN=', len(results.get(i,'')))
    elif cmd=='dump':
        i=sys.argv[2]; out=sys.argv[3]
        T=sys.argv[4] if len(sys.argv)>4 else MINE
        calls, order, results = load(T)
        open(out,'w').write(results[i])
        print('wrote', out, len(results[i]))
