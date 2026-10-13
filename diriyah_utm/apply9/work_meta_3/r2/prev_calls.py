import json, sys
T = sys.argv[1]
def rt(cc):
    if isinstance(cc, list):
        return ''.join(x.get('text','') for x in cc if isinstance(x, dict) and x.get('type')=='text')
    if isinstance(cc, str): return cc
    return json.dumps(cc)
uses, order, results = {}, [], {}
for line in open(T):
    line=line.strip()
    if not line: continue
    try: r=json.loads(line)
    except Exception: continue
    c=(r.get('message') or {}).get('content')
    if not isinstance(c, list): continue
    for b in c:
        if not isinstance(b, dict): continue
        if b.get('type')=='tool_use':
            if b['id'] not in uses: order.append(b['id'])
            uses[b['id']]=(b['name'], b.get('input') or {}, r.get('timestamp'))
        elif b.get('type')=='tool_result':
            results[b['tool_use_id']]=(rt(b.get('content')), b.get('is_error'))
for i in order:
    name, inp, ts = uses[i]
    res, err = results.get(i, (None, None))
    if name in ('Bash',):
        s = inp.get('command','')[:300].replace('\n',' | ')
        print(f'{ts} BASH {inp.get("description","")} :: {s}')
        print('    ->', (res or '')[:300].replace('\n',' | '), 'ERR' if err else '')
        continue
    if 'Whathed' in name or name in ('ToolSearch',):
        a = {k:v for k,v in inp.items() if k not in ('body','params')}
        print(f'{ts} {name.split("__")[-1]} {json.dumps(a, ensure_ascii=False)[:400]}')
        if 'body' in inp: print('    body:', json.dumps(inp['body'], ensure_ascii=False)[:600])
        if 'params' in inp: print('    params:', json.dumps(inp['params'], ensure_ascii=False)[:600])
        print('    ->', (res or '')[:700].replace('\n',' | '), 'ERR' if err else '')
    else:
        print(f'{ts} {name} {json.dumps(inp, ensure_ascii=False)[:200]}')
        print('    ->', (res or '')[:200].replace('\n',' | '), 'ERR' if err else '')
