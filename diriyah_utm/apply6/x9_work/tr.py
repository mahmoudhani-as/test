# Helper: read my own MCP tool calls/results from my transcript.
import json, sys
T='/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/wf_438dd2ce-50a/agent-a1f7bc2d26c5984a8.jsonl'

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

if __name__=='__main__':
    calls, results, order = load_tr()
    n=int(sys.argv[1]) if len(sys.argv)>1 else 10
    for tid in order[-n:]:
        name, inp = calls[tid]
        print(tid, name, json.dumps(inp, ensure_ascii=False)[:220], '| result len', len(results.get(tid,'')))
