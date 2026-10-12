# Extract my own MCP tool calls + results from my transcript.
# usage: python3 tr.py list [N]        -> list last N tool calls (id, name, short input)
#        python3 tr.py dump <tool_use_id> <outfile>   -> write the result text (raw string) to outfile
import json, sys
T='/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/wf_ab8422cb-21a/agent-a6497fc413eadd5b3.jsonl'
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
            calls[c['id']]=(c.get('name'), c.get('input')); order.append(c['id'])
        elif c.get('type')=='tool_result':
            rc=c.get('content')
            if isinstance(rc, list):
                txt=''.join(x.get('text','') for x in rc if isinstance(x, dict) and x.get('type')=='text')
            else:
                txt=rc if isinstance(rc,str) else json.dumps(rc)
            results[c['tool_use_id']]=txt
cmd=sys.argv[1]
if cmd=='list':
    n=int(sys.argv[2]) if len(sys.argv)>2 else 10
    for i in order[-n:]:
        name,inp=calls[i]
        print(i, name, json.dumps(inp)[:200], 'RESULT_LEN=', len(results.get(i,'')))
elif cmd=='dump':
    i=sys.argv[2]; out=sys.argv[3]
    open(out,'w').write(results[i])
    print('wrote', out, len(results[i]))
