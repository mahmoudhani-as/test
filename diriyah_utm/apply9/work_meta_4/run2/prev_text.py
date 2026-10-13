import json, sys
T = sys.argv[1]
n = 0
for line in open(T):
    line = line.strip()
    if not line:
        continue
    try:
        r = json.loads(line)
    except Exception:
        continue
    m = r.get('message') or {}
    c = m.get('content')
    role = m.get('role')
    if isinstance(c, str):
        print(f'[{role} str]', c[:1500]); continue
    if not isinstance(c, list):
        continue
    for b in c:
        t = b.get('type')
        if t == 'text' and role == 'assistant':
            print('[assistant text]', b['text'][:3000])
        elif t == 'tool_use':
            inp = b.get('input') or {}
            if 'Whathed' in b['name']:
                print('[tool_use]', b['name'].split('__')[-1], inp.get('action'), inp.get('path_params'), 'dry_run=', inp.get('dry_run'))
            else:
                print('[tool_use]', b['name'], json.dumps(inp)[:1200])
        elif t == 'tool_result':
            cc = b.get('content')
            if isinstance(cc, list):
                s = ''.join(x.get('text', '') for x in cc if isinstance(x, dict) and x.get('type') == 'text')
            else:
                s = cc if isinstance(cc, str) else json.dumps(cc)
            print('[tool_result]', 'ERR' if b.get('is_error') else '', s[:700].replace('\n', ' '))
