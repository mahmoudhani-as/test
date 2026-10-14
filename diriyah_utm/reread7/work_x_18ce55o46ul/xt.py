# Extract x_ads_native_action tool results from this agent's own transcript.
# usage: python3 xt.py <label> <tool_use_id,...|last|lastN>
#   -> writes raw/<label>.json (list of {tool_use_id, input, result})
# If a result was saved to a file (large output), the file content is loaded instead.
import json, sys, os, re
T = '/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/wf_1382dc0e-e06/agent-a5ef380a78e68516d.jsonl'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'raw')
uses = {}; order = []; results = {}
for l in open(T, encoding='utf-8'):
    try:
        o = json.loads(l)
    except Exception:
        continue
    c = (o.get('message') or {}).get('content')
    if not isinstance(c, list):
        continue
    for p in c:
        if not isinstance(p, dict):
            continue
        if p.get('type') == 'tool_use' and 'x_ads_native_action' in (p.get('name') or ''):
            if p['id'] not in uses:
                uses[p['id']] = p.get('input'); order.append(p['id'])
        elif p.get('type') == 'tool_result' and p.get('tool_use_id') in uses:
            cc = p.get('content')
            if isinstance(cc, list):
                txt = ''.join(x.get('text', '') for x in cc if isinstance(x, dict))
            else:
                txt = cc if isinstance(cc, str) else json.dumps(cc)
            results[p['tool_use_id']] = txt


def parse(txt):
    try:
        return json.loads(txt)
    except Exception:
        pass
    m = re.search(r'(/[^\s"\']+\.(?:json|txt))', txt or '')
    if m and os.path.exists(m.group(1)):
        raw = open(m.group(1), encoding='utf-8').read()
        try:
            res = json.loads(raw)
            if isinstance(res, list) and res and isinstance(res[0], dict) and 'text' in res[0]:
                res = json.loads(''.join(x.get('text', '') for x in res))
            return res
        except Exception:
            return {'_unparsed_file': m.group(1)}
    return {'_unparsed': (txt or '')[:3000]}


label = sys.argv[1]; sel = sys.argv[2]
if sel.startswith('last'):
    n = int(sel[4:] or 1)
    ids = [i for i in order if i in results][-n:]
else:
    ids = sel.split(',')
out = []
for i in ids:
    res = parse(results.get(i))
    out.append({'tool_use_id': i, 'input': uses[i], 'result': res})
os.makedirs(OUT, exist_ok=True)
json.dump(out, open(os.path.join(OUT, label + '.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
for o in out:
    r = o['result']
    inner = r
    while isinstance(inner, dict) and isinstance(inner.get('data'), dict):
        inner = inner['data']
    items = inner.get('data') if isinstance(inner, dict) else None
    print(o['tool_use_id'], json.dumps(o['input'], ensure_ascii=False)[:200],
          '| success=', r.get('success') if isinstance(r, dict) else None,
          '| items=', len(items) if isinstance(items, list) else type(items).__name__,
          '| next_cursor=', inner.get('next_cursor') if isinstance(inner, dict) else None,
          '| total=', inner.get('total_count') if isinstance(inner, dict) else None,
          '| keys=', list(r.keys())[:6] if isinstance(r, dict) else None)
