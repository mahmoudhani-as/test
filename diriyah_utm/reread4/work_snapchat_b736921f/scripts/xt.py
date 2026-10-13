# Extract snapchat_native_action tool results from this agent's own transcript.
# usage: python3 -I xt.py <label> <tool_use_id,...|last|lastN>   -> writes ../raw/<label>.json (list of {tool_use_id, input, result})
import json, sys, os, re
T = '/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/wf_2da73588-63c/agent-a7bec156cf5509dcb.jsonl'
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'raw')
uses = {}; order = []; results = {}
for l in open(T):
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
        if p.get('type') == 'tool_use' and 'snapchat_native_action' in (p.get('name') or ''):
            if p['id'] not in uses:
                uses[p['id']] = p.get('input'); order.append(p['id'])
        elif p.get('type') == 'tool_result' and p.get('tool_use_id') in uses:
            cc = p.get('content')
            if isinstance(cc, list):
                txt = ''.join(x.get('text', '') for x in cc if isinstance(x, dict))
            else:
                txt = cc if isinstance(cc, str) else json.dumps(cc)
            results[p['tool_use_id']] = txt
label = sys.argv[1]; sel = sys.argv[2]
if sel.startswith('last'):
    n = int(sel[4:] or 1)
    ids = [i for i in order if i in results][-n:]
else:
    ids = sel.split(',')
out = []
for i in ids:
    txt = results.get(i)
    res = None
    try:
        res = json.loads(txt)
    except Exception:
        m = re.search(r'(/[^\s"\']+\.(?:json|txt))', txt or '')
        if m and os.path.exists(m.group(1)):
            raw = open(m.group(1)).read()
            try:
                res = json.loads(raw)
                if isinstance(res, list) and res and isinstance(res[0], dict) and 'text' in res[0]:
                    res = json.loads(''.join(x.get('text', '') for x in res))
            except Exception:
                res = {'_unparsed_file': m.group(1)}
        else:
            res = {'_unparsed': (txt or '')[:3000]}
    out.append({'tool_use_id': i, 'input': uses[i], 'result': res})
json.dump(out, open(os.path.join(OUT, label + '.json'), 'w'), indent=1)
for o in out:
    r = o['result']
    d = (r.get('data') or {}) if isinstance(r, dict) else {}
    dd = d.get('data') if isinstance(d, dict) else None
    info = {}
    src = dd if isinstance(dd, dict) else d
    if isinstance(src, dict):
        info = {k: (len(v) if isinstance(v, list) else None) for k, v in src.items() if isinstance(v, list)}
    pg = src.get('paging') if isinstance(src, dict) else None
    meta = r.get('meta') if isinstance(r, dict) else None
    print(o['tool_use_id'], json.dumps(o['input'])[:220], '| success=', r.get('success') if isinstance(r, dict) else None,
          '| keys=', list(r.keys())[:8] if isinstance(r, dict) else type(r).__name__, '| lists=', info, '| paging=', str(pg)[:200], '| meta=', str(meta)[:400])
