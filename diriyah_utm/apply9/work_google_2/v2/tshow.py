import json, sys
# usage: python3 -I tshow.py <transcript.jsonl> <tool_use_id_suffix> [...]
path = sys.argv[1]
want = sys.argv[2:]
for line in open(path):
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
        if c.get('type') == 'tool_use' and any(c['id'].endswith(w) for w in want):
            print('=== USE', c['id'], c.get('name'))
            print(json.dumps(c.get('input'), ensure_ascii=False, indent=1))
        elif c.get('type') == 'tool_result' and any(c['tool_use_id'].endswith(w) for w in want):
            rc = c.get('content')
            if isinstance(rc, list):
                txt = ''.join(x.get('text', '') for x in rc if isinstance(x, dict) and x.get('type') == 'text')
            else:
                txt = rc if isinstance(rc, str) else json.dumps(rc)
            print('=== RES', c['tool_use_id'], 'is_error=', c.get('is_error'))
            print(txt[:6000])
