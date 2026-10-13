# usage: python3 -I extract.py <transcript.jsonl> <out_dir>
# Extracts every Whathead tiktok_native_action tool result from this agent's transcript into out_dir/<tiktok_request_id>.json
import json, sys, os, re
src, outd = sys.argv[1], sys.argv[2]
os.makedirs(outd, exist_ok=True)
n = 0
for line in open(src, encoding='utf-8'):
    try:
        ev = json.loads(line)
    except Exception:
        continue
    msg = ev.get('message') or {}
    content = msg.get('content')
    if not isinstance(content, list):
        continue
    for c in content:
        if not isinstance(c, dict) or c.get('type') != 'tool_result':
            continue
        parts = c.get('content')
        if isinstance(parts, list):
            text = ''.join(p.get('text', '') for p in parts if isinstance(p, dict) and p.get('type') == 'text')
        else:
            text = parts if isinstance(parts, str) else ''
        if '"tiktokRequestId"' not in text:
            continue
        try:
            d = json.loads(text)
        except Exception as e:
            print('unparseable result', c.get('tool_use_id'), len(text), e)
            continue
        rid = (((d.get('data') or {}).get('meta') or {}).get('tiktokRequestId')) or c.get('tool_use_id')
        path = os.path.join(outd, f"{rid}.json")
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
        inner = (d.get('data') or {}).get('data') or {}
        dd = inner.get('data') or {}
        lst = dd.get('list') or []
        pi = dd.get('page_info')
        budget = (d.get('meta') or {}).get('mcp_output_budget')
        nondict = [x for x in lst if not isinstance(x, dict)]
        print(rid, (d.get('data') or {}).get('action'), 'items', len(lst), 'markers', nondict[:2], 'page_info', pi, 'truncated', (budget or {}).get('truncated'))
        n += 1
print('extracted', n)
