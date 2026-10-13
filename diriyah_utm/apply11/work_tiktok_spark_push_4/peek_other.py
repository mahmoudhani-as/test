# Read-only: list tiktok_ad_update calls (live) + result summary in another lane's transcript, to learn TikTok's response to the call shape.
import json, sys
TR = sys.argv[1]
ev = []
seen = set()
for line in open(TR, encoding='utf-8'):
    try:
        e = json.loads(line)
    except Exception:
        continue
    content = (e.get('message') or {}).get('content')
    if not isinstance(content, list):
        continue
    for c in content:
        if not isinstance(c, dict):
            continue
        if c.get('type') == 'tool_use' and ('u', c['id']) not in seen:
            seen.add(('u', c['id'])); ev.append(('use', c['id'], c.get('name', ''), c.get('input') or {}))
        elif c.get('type') == 'tool_result' and ('r', c.get('tool_use_id')) not in seen:
            seen.add(('r', c.get('tool_use_id')))
            cc = c.get('content')
            t = ''.join(x.get('text', '') for x in cc if isinstance(x, dict)) if isinstance(cc, list) else str(cc)
            ev.append(('result', c.get('tool_use_id'), t, bool(c.get('is_error'))))
res = {x[1]: x[2] for x in ev if x[0] == 'result'}
for x in ev:
    if x[0] != 'use' or not x[2].endswith('tiktok_native_action'):
        continue
    inp = x[3]
    if inp.get('action') not in ('tiktok_ad_update', 'tiktok_smart_plus_ad_update'):
        continue
    cr = ((inp.get('payload') or {}).get('creatives') or [{}])[0]
    keys = sorted(cr.keys())
    r = res.get(x[1], '')
    print('dry_run=', inp.get('dry_run'), 'ad', cr.get('ad_id'), 'keys', keys)
    print('   RESULT:', r[:600].replace('\n', ' '))
