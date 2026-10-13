# Parse this agent's own transcript to extract MCP tool calls/results (matched by Whathead requestId).
import json
T = '/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/wf_b0959460-29d/agent-a363ec35b3d7f60a7.jsonl'

def load():
    calls = {}; results = {}; order = []
    for line in open(T, encoding='utf-8'):
        try:
            e = json.loads(line)
        except Exception:
            continue
        msg = e.get('message') or {}
        content = msg.get('content')
        if not isinstance(content, list):
            continue
        for c in content:
            if not isinstance(c, dict):
                continue
            if c.get('type') == 'tool_use':
                if c['id'] not in calls:
                    order.append(c['id'])
                calls[c['id']] = (c.get('name'), c.get('input'))
            elif c.get('type') == 'tool_result':
                rc = c.get('content')
                if isinstance(rc, list):
                    txt = ''.join(x.get('text', '') for x in rc if isinstance(x, dict) and x.get('type') == 'text')
                else:
                    txt = rc if isinstance(rc, str) else json.dumps(rc)
                results[c['tool_use_id']] = txt
    return calls, results, order

def by_request_id(rid):
    calls, results, order = load()
    hits = []
    for tid in order:
        r = results.get(tid, '')
        if ('"requestId": "%s"' % rid) in r or ('"requestId":"%s"' % rid) in r:
            hits.append((tid, calls[tid], r))
    if len(hits) != 1:
        raise SystemExit('request id %s matched %d results' % (rid, len(hits)))
    return hits[0]

def result_json(rid):
    tid, (name, inp), r = by_request_id(rid)
    return tid, name, inp, json.loads(r)
