import json, sys
# usage: python3 -I tlog.py <transcript.jsonl> [maxin] [maxout]
path = sys.argv[1]
maxin = int(sys.argv[2]) if len(sys.argv) > 2 else 400
maxout = int(sys.argv[3]) if len(sys.argv) > 3 else 300
calls = {}
order = []
for line in open(path):
    try:
        e = json.loads(line)
    except Exception:
        continue
    ts = e.get('timestamp', '')
    msg = e.get('message') or {}
    content = msg.get('content')
    if not isinstance(content, list):
        continue
    for c in content:
        if not isinstance(c, dict):
            continue
        if c.get('type') == 'tool_use':
            inp = json.dumps(c.get('input'), ensure_ascii=False)
            print('%s USE  %s %s :: %s' % (ts[11:19], c['id'][-6:], c.get('name'), inp[:maxin]))
        elif c.get('type') == 'tool_result':
            rc = c.get('content')
            if isinstance(rc, list):
                txt = ''.join(x.get('text', '') for x in rc if isinstance(x, dict) and x.get('type') == 'text')
            else:
                txt = rc if isinstance(rc, str) else json.dumps(rc)
            print('%s RES  %s err=%s :: %s' % (ts[11:19], c['tool_use_id'][-6:], c.get('is_error'), txt[:maxout].replace('\n', ' | ')))
