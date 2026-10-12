# Helper: read my own MCP tool calls/results from my transcript.
import json, sys, os
T='/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/wf_ab8422cb-21a/agent-a2b2072268f24b3b2.jsonl'

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

def find(pred, last=True):
    calls, results, order = load_tr()
    hits=[tid for tid in order if pred(calls[tid][0], calls[tid][1] or {}) and tid in results]
    if not hits: return None
    return hits[-1] if last else hits

def result_json(tid):
    calls, results, order = load_tr()
    txt=results[tid]
    try:
        return json.loads(txt)
    except Exception:
        # maybe saved to file path
        return txt

if __name__=='__main__':
    calls, results, order = load_tr()
    for tid in order[-int(sys.argv[1]) if len(sys.argv)>1 else -10:]:
        name, inp = calls[tid]
        print(tid, name, json.dumps(inp, ensure_ascii=False)[:200], '| result len', len(results.get(tid,'')))
