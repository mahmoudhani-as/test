"""Extract every Whathead meta_native_action call (input + parsed result) from this agent's transcript.
Strips Graph 'paging' blocks (paging.next URLs can carry an access token) before saving.
Usage: grab.py TRANSCRIPT OUT_JSON"""
import json, re, sys
TRANSCRIPT, OUT = sys.argv[1], sys.argv[2]
inputs, results = {}, []
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


def strip_paging(x):
    if isinstance(x, dict):
        return {k: strip_paging(v) for k, v in x.items() if k != 'paging'}
    if isinstance(x, list):
        return [strip_paging(v) for v in x]
    if isinstance(x, str) and 'access_token=' in x:
        return re.sub(r'access_token=[^&\s"]+', 'access_token=REDACTED', x)
    return x


calls = []
for tid, content in results:
    source = 'inline'
    if isinstance(content, list):
        text = ''.join(x.get('text', '') for x in content if isinstance(x, dict) and x.get('type') == 'text')
    else:
        text = content if isinstance(content, str) else None
    if text and ('<persisted-output>' in text[:200] or 'Output has been saved to' in text[:400]):
        mm = re.search(r'(?:Full output saved to:|Output has been saved to) (\S+?\.(?:json|txt))', text)
        source = mm.group(1) if mm else 'persisted?'
        try:
            raw = open(source, encoding='utf-8').read()
            try:
                w = json.loads(raw)
                if isinstance(w, list) and w and isinstance(w[0], dict) and 'text' in w[0]:
                    text = ''.join(x.get('text', '') for x in w if isinstance(x, dict))
                else:
                    text = raw
            except Exception:
                text = raw
        except Exception:
            text = None
    s = text or ''
    try:
        payload = json.loads(s) if s else None
    except Exception:
        payload = None
    calls.append({'tool_use_id': tid, 'input': inputs[tid], 'source': source, 'raw_len': len(s),
                  'truncated': ('MCP_OUTPUT_TRUNCATED' in s) or bool(re.search(r'more items truncated', s)) or ('"truncated": true' in s),
                  'payload': strip_paging(payload), 'text_head': None if payload is not None else s[:500]})
json.dump(calls, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
for i, cl in enumerate(calls):
    inp = cl['input'] or {}
    p = cl['payload'] or {}
    dd = (((p.get('data') or {}).get('data')) or {}) if isinstance(p, dict) else {}
    n = len(dd.get('data', [])) if isinstance(dd, dict) and isinstance(dd.get('data'), list) else None
    print(i, cl['tool_use_id'][-8:], inp.get('action'), json.dumps(inp.get('query')),
          (json.dumps(inp.get('params'))[:90] if inp.get('params') else ''), 'n=', n, 'trunc=', cl['truncated'],
          'len=', cl['raw_len'], cl['source'][-50:], ('PARSEFAIL ' + (cl['text_head'] or '')[:200]) if cl['payload'] is None else '')
