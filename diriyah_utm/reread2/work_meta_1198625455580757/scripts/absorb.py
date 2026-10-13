import json, sys, os
W = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/reread2/work_meta_1198625455580757'
STORE = os.path.join(W, 'data', 'ads_store.json')
MARK = 'MCP_OUTPUT_TRUNCATED'

def has_mark(o):
    if isinstance(o, str):
        return MARK in o or 'more items truncated' in o
    if isinstance(o, dict):
        return any(has_mark(k) or has_mark(v) for k, v in o.items())
    if isinstance(o, list):
        return any(has_mark(x) for x in o)
    return False

def load(path):
    txt0 = open(path, encoding='utf-8').read()
    raw = json.loads(txt0)
    if isinstance(raw, list):
        txt = ''.join(x.get('text', '') for x in raw if isinstance(x, dict))
    else:
        txt = json.dumps(raw)
    return json.loads(txt)

store = json.load(open(STORE)) if os.path.exists(STORE) else {}
for p in sys.argv[1:]:
    j = load(p)
    inner = j['data']['data']
    items = inner['data']
    budget = j.get('meta', {}).get('mcp_output_budget')
    ok = bad = 0
    for it in items:
        if not isinstance(it, dict):
            print('  marker item:', it)
            continue
        if has_mark(it):
            bad += 1
            print('  incomplete item:', it.get('id'))
            continue
        store[it['id']] = it
        ok += 1
    print(p, 'items', len(items), 'complete', ok, 'incomplete', bad, 'budget', budget, 'paging' in inner, inner.get('paging'))
json.dump(store, open(STORE, 'w'), ensure_ascii=False, indent=1)
print('store size', len(store))
