import json, sys
T = sys.argv[1]
uses, order, results = {}, [], {}
for line in open(T):
    line = line.strip()
    if not line:
        continue
    try:
        r = json.loads(line)
    except Exception:
        continue
    c = (r.get('message') or {}).get('content')
    if not isinstance(c, list):
        continue
    for b in c:
        if b.get('type') == 'tool_use':
            if b['id'] not in uses:
                order.append(b['id'])
            uses[b['id']] = (b['name'], b.get('input') or {})
        elif b.get('type') == 'tool_result':
            cc = b.get('content')
            if isinstance(cc, list):
                t = ''.join(x.get('text', '') for x in cc if isinstance(x, dict) and x.get('type') == 'text')
            else:
                t = cc if isinstance(cc, str) else json.dumps(cc)
            results[b['tool_use_id']] = (t, b.get('is_error'))
for i in order:
    name, inp = uses[i]
    if 'Whathed' not in name and len(sys.argv) < 3:
        continue
    res, err = results.get(i, (None, None))
    a = inp.get('action')
    pp = inp.get('path_params')
    dr = inp.get('dry_run')
    keys = sorted(k for k in inp if k not in ('action', 'path_params', 'dry_run'))
    print('---', i[-8:], name.split('__')[-1], a, 'dry_run=', dr, 'pp=', pp, 'keys=', keys, 'is_error=', err)
    if 'Whathed' in name and inp.get('payload') is not None:
        print('   payload:', json.dumps(inp.get('payload'), ensure_ascii=False)[:400])
    if 'Whathed' in name and inp.get('params') is not None:
        print('   params:', json.dumps(inp.get('params'), ensure_ascii=False)[:400])
    if 'Whathed' not in name:
        print('   input:', json.dumps(inp, ensure_ascii=False)[:300])
    print('   result:', (res or '')[:600].replace('\n', ' '))
