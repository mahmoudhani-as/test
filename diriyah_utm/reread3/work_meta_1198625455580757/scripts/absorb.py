import json, sys, os, shutil
W = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/reread3/work_meta_1198625455580757'
STORE = os.path.join(W, 'data', 'ads_store.json')
MARKS = ('MCP_OUTPUT_TRUNCATED', 'more items truncated', '[truncated', 'TRUNCATED')

def has_mark(o):
    if isinstance(o, str):
        return any(m in o for m in MARKS)
    if isinstance(o, dict):
        return any(has_mark(k) or has_mark(v) for k, v in o.items())
    if isinstance(o, list):
        return any(has_mark(x) for x in o)
    return False

def load(path):
    raw = json.loads(open(path, encoding='utf-8').read())
    if isinstance(raw, list):
        txt = ''.join(x.get('text', '') for x in raw if isinstance(x, dict))
        return json.loads(txt)
    return raw

store = json.load(open(STORE)) if os.path.exists(STORE) else {}
for p in sys.argv[1:]:
    tag = os.path.basename(p)
    dst = os.path.join(W, 'raw', tag)
    if not os.path.exists(dst):
        shutil.copy(p, dst)
    j = load(p)
    assert j.get('success') is True, j
    inner = j['data']['data']
    items = inner['data']
    budget = j.get('meta', {}).get('mcp_output_budget') or j['data'].get('meta', {}).get('mcp_output_budget')
    ok = bad = 0
    for it in items:
        if not isinstance(it, dict):
            print('  marker item:', it); bad += 1
            continue
        if has_mark(it):
            bad += 1
            print('  incomplete item:', it.get('id'))
            continue
        store[it['id']] = it
        ok += 1
    print(tag, 'items', len(items), 'complete', ok, 'incomplete', bad, 'budget', budget, 'paging' in inner, 'keys', list(inner.keys()))
json.dump(store, open(STORE, 'w'), ensure_ascii=False, indent=1)
print('store size', len(store))
