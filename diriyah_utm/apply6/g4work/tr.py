import json, glob
TR = '/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/wf_35f459a6-efe/agent-a9238e21d2f75db0f.jsonl'
def _texts(content):
    if isinstance(content, str):
        yield content
    elif isinstance(content, list):
        for c in content:
            if isinstance(c, dict):
                if c.get('type') == 'text':
                    yield c.get('text', '')
                elif c.get('type') == 'tool_result':
                    yield from _texts(c.get('content'))
def get_result(request_id):
    found = []
    for line in open(TR, encoding='utf-8'):
        if request_id not in line:
            continue
        o = json.loads(line)
        msg = o.get('message', {})
        for t in _texts(msg.get('content')):
            if request_id in t:
                found.append(t)
    if not found:
        raise SystemExit('requestId not found: ' + request_id)
    obj = json.loads(found[-1])
    return obj
def results_of(obj):
    return obj['data']['data']['data']['results']
