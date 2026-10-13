# usage: python3 -I collect.py <transcript.jsonl> <out_json>
# Pairs every mcp__Whathed_MCP__tiktok_native_action tool_use in this agent's transcript with its result
# (inline text, or the persisted tool-results file named in the <persisted-output> stub) and writes
# [{tool_use_id, input, result(parsed gateway JSON) or null, source}] to out_json.
import json, sys, re, os
src, outp = sys.argv[1], sys.argv[2]
uses, results = {}, {}
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
            uses[c['id']] = c.get('input')
        elif c.get('type') == 'tool_result':
            parts = c.get('content')
            if isinstance(parts, list):
                text = ''.join(p.get('text', '') for p in parts if isinstance(p, dict) and p.get('type') == 'text')
            else:
                text = parts if isinstance(parts, str) else ''
            results[c.get('tool_use_id')] = text
out = []
for tid, inp in uses.items():
    text = results.get(tid)
    rec = {'tool_use_id': tid, 'input': inp, 'result': None, 'source': None}
    if text is None:
        rec['source'] = 'missing'
    else:
        m = re.search(r'Full output saved to: (\S+)', text)
        if m and text.lstrip().startswith('<persisted-output>'):
            path = m.group(1)
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
        try:
            rec['result'] = json.loads(text)
        except Exception as e:
            rec['result'] = None
            rec['error'] = f'unparseable: {e}; head={text[:200]!r}'
    out.append(rec)
json.dump(out, open(outp, 'w', encoding='utf-8'), ensure_ascii=False)
for r in out:
    inp = r['input'] or {}
    p = inp.get('params') or {}
    res = r['result'] or {}
    inner = ((res.get('data') or {}).get('data') or {}) if isinstance(res, dict) else {}
    dd = inner.get('data') or {} if isinstance(inner, dict) else {}
    lst = dd.get('list') if isinstance(dd, dict) else None
    n = len([x for x in lst if isinstance(x, dict)]) if isinstance(lst, list) else None
    mk = [x for x in lst if not isinstance(x, dict)] if isinstance(lst, list) else None
    bud = (res.get('meta') or {}).get('mcp_output_budget') if isinstance(res, dict) else None
    print(r['tool_use_id'][-8:], inp.get('action'), json.dumps(p.get('filtering')), 'page', p.get('page'), 'ps', p.get('page_size'), '| code', inner.get('code') if isinstance(inner, dict) else None, 'items', n, 'markers', mk, 'pi', dd.get('page_info') if isinstance(dd, dict) else None, 'trunc', bool(bud and bud.get('truncated')), 'src', 'file' if r['source'] not in ('inline','missing') else r['source'], r.get('error',''))
