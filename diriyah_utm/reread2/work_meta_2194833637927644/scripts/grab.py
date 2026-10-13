"""Extract every Whathead meta_native_action call (input + parsed result) from this agent's transcript.
Writes data/calls.json: list of {tool_use_id, input, ok, truncated, payload(parsed JSON or None), raw_len, source}."""
import json, re, sys, os
TRANSCRIPT = sys.argv[1]
OUT = sys.argv[2]
inputs = {}
results = []
for line in open(TRANSCRIPT, encoding='utf-8'):
    try:
        o = json.loads(line)
    except Exception:
        continue
    m = o.get('message') or {}
    c = m.get('content')
    if not isinstance(c, list):
        continue
    for b in c:
        if not isinstance(b, dict):
            continue
        if b.get('type') == 'tool_use' and 'meta_native_action' in (b.get('name') or ''):
            inputs[b['id']] = b.get('input')
        elif b.get('type') == 'tool_result' and b.get('tool_use_id') in inputs:
            results.append((b['tool_use_id'], b.get('content')))
calls = []
for tid, content in results:
    text = None
    source = 'inline'
    if isinstance(content, list):
        parts = [x.get('text', '') for x in content if isinstance(x, dict) and x.get('type') == 'text']
        text = ''.join(parts)
    elif isinstance(content, str):
        text = content
    if text and text.lstrip().startswith('<persisted-output>'):
        mm = re.search(r'Full output saved to: (\S+)', text)
        source = mm.group(1) if mm else 'persisted?'
        try:
            w = json.load(open(source, encoding='utf-8'))
            if isinstance(w, list):
                text = ''.join(x.get('text', '') for x in w if isinstance(x, dict))
            else:
                text = json.dumps(w)
        except Exception as e:
            text = None
    payload = None
    try:
        payload = json.loads(text) if text else None
    except Exception:
        payload = None
    s = text or ''
    calls.append({'tool_use_id': tid, 'input': inputs[tid], 'source': source, 'raw_len': len(s),
                  'truncated': ('MCP_OUTPUT_TRUNCATED' in s) or bool(re.search(r'\[\d+ more items truncated\]', s)),
                  'payload': payload})
json.dump(calls, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
for i, cl in enumerate(calls):
    inp = cl['input'] or {}
    p = cl['payload'] or {}
    dd = (((p.get('data') or {}).get('data')) or {}) if isinstance(p, dict) else {}
    n = len(dd.get('data', [])) if isinstance(dd, dict) and isinstance(dd.get('data'), list) else None
    print(i, cl['tool_use_id'], inp.get('action'), json.dumps(inp.get('query')), (json.dumps(inp.get('params'))[:110] if inp.get('params') else ''), 'n=', n, 'trunc=', cl['truncated'], 'len=', cl['raw_len'], cl['source'][:60])
