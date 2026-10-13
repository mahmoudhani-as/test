# usage: python3 -I collect.py <transcript.jsonl> <out_json>
# Pairs every mcp__Whathed_MCP__tiktok_native_action tool_use in this agent's transcript with its result
# (inline text, or the persisted tool-results file named in the <persisted-output> stub) and writes
# [{seq, tool_use_id, input, result(parsed gateway JSON) or null, source, text_len}] to out_json.
# Prints one summary line per call (action, filter, page, items, truncation markers, page_info).
import json, sys, re
src, outp = sys.argv[1], sys.argv[2]
uses, order, results = {}, [], {}
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
        if not isinstance(c, dict):
            continue
        if c.get('type') == 'tool_use' and c.get('name') == 'mcp__Whathed_MCP__tiktok_native_action':
            if c['id'] not in uses:
                order.append(c['id'])
            uses[c['id']] = c.get('input')
        elif c.get('type') == 'tool_result':
            parts = c.get('content')
            if isinstance(parts, list):
                text = ''.join(p.get('text', '') for p in parts if isinstance(p, dict) and p.get('type') == 'text')
            else:
                text = parts if isinstance(parts, str) else ''
            results[c.get('tool_use_id')] = text
out = []
for seq, tid in enumerate(order):
    inp = uses[tid]
    text = results.get(tid)
    rec = {'seq': seq, 'tool_use_id': tid, 'input': inp, 'result': None, 'source': None, 'text_len': None}
    if text is None:
        rec['source'] = 'missing'
    else:
        m = re.search(r'(?:Full output saved to|Output has been saved to):?\s*(\S+)', text[:2000])
        if m and ('<persisted-output>' in text[:200] or text.startswith('Error: result (')):
            path = m.group(1).rstrip('.')
            raw = open(path, encoding='utf-8').read()
            try:
                outer = json.loads(raw)
            except Exception:
                outer = None
            if isinstance(outer, list):
                t2 = ''.join(p.get('text', '') for p in outer if isinstance(p, dict) and p.get('type') == 'text')
            else:
                t2 = raw
            rec['source'] = path
            text = t2
        else:
            rec['source'] = 'inline'
        rec['text_len'] = len(text)
        try:
            rec['result'] = json.loads(text)
        except Exception as e:
            rec['result'] = None
            rec['error'] = f'unparseable: {e}; head={text[:300]!r}'
    out.append(rec)
json.dump(out, open(outp, 'w', encoding='utf-8'), ensure_ascii=False)
for r in out:
    inp = r['input'] or {}
    p = inp.get('params') or {}
    res = r['result'] if isinstance(r['result'], dict) else {}
    inner = ((res.get('data') or {}).get('data') or {}) if isinstance(res.get('data'), dict) else {}
    dd = inner.get('data') or {} if isinstance(inner, dict) else {}
    lst = dd.get('list') if isinstance(dd, dict) else None
    n = len([x for x in lst if isinstance(x, dict)]) if isinstance(lst, list) else None
    mk = [x for x in lst if not isinstance(x, dict)] if isinstance(lst, list) else None
    bud = (res.get('meta') or {}).get('mcp_output_budget') if res else None
    f = dict(p.get('filtering') or {})
    for k in ('ad_ids', 'smart_plus_ad_ids'):
        if k in f:
            f[k] = f'<{len(f[k])} ids>'
    print(r['seq'], r['tool_use_id'][-6:], inp.get('action'), json.dumps(f), 'pg', p.get('page'), 'ps', p.get('page_size'),
          '| ok', res.get('success') if res else None, 'code', inner.get('code') if isinstance(inner, dict) else None,
          'items', n, 'mk', mk, 'pi', (dd.get('page_info') if isinstance(dd, dict) else None),
          'trunc', bool(bud and bud.get('truncated')), 'src', 'file' if r['source'] not in ('inline', 'missing') else r['source'],
          'len', r['text_len'], r.get('error', ''))
