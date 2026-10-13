import json, sys, os, re, datetime
W = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/reread5/work_meta_1198625455580757'
STORE = os.path.join(W, 'data', 'ads_store.json')
MARKS = ('MCP_OUTPUT_TRUNCATED', 'more items truncated', '[truncated', 'TRUNCATED', 'truncated')

def has_mark(o):
    if isinstance(o, str):
        return any(m in o for m in MARKS)
    if isinstance(o, dict):
        return any(has_mark(k) or has_mark(v) for k, v in o.items())
    if isinstance(o, list):
        return any(has_mark(x) for x in o)
    return False

def strip_paging(o):
    # drop Graph paging blocks (their next/previous URLs can carry an access token)
    if isinstance(o, dict):
        return {k: strip_paging(v) for k, v in o.items() if k != 'paging'}
    if isinstance(o, list):
        return [strip_paging(x) for x in o]
    return o

def load(path):
    txt = open(path, encoding='utf-8').read()
    raw = json.loads(txt)
    if isinstance(raw, list):
        txt = ''.join(x.get('text', '') for x in raw if isinstance(x, dict))
        return json.loads(txt), txt
    return raw, txt

store = json.load(open(STORE)) if os.path.exists(STORE) else {}
for p in sys.argv[1:]:
    tag = os.path.basename(p)
    j, txt = load(p)
    print(tag, 'bytes', len(txt.encode('utf-8')), 'access_token in text:', 'access_token' in txt)
    assert j.get('success') is True, str(j)[:500]
    inner = j['data']['data']
    assert isinstance(inner, dict) and 'data' in inner, list(inner)
    items = inner['data']
    warn = j['data'].get('meta', {}).get('warnings')
    ok = bad = 0
    mtime = datetime.datetime.fromtimestamp(os.path.getmtime(p), datetime.timezone.utc).isoformat()
    for it in items:
        if not isinstance(it, dict):
            print('  marker item:', str(it)[:200]); bad += 1
            continue
        if has_mark(it):
            bad += 1
            print('  item with truncation marker:', it.get('id'))
            continue
        it = strip_paging(it)
        it['_fetched'] = mtime
        it['_src'] = tag
        store[it['id']] = it
        ok += 1
    print('  items', len(items), 'complete', ok, 'incomplete', bad, 'inner keys', list(inner.keys()), 'warnings', warn,
          'top-level text has trunc marker:', any(m in txt for m in MARKS[:3]))
json.dump(store, open(STORE, 'w'), ensure_ascii=False, indent=1)
print('store size', len(store))
