import json, sys
W = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/reread2/work_meta_1198625455580757'
IN = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/reread/in/meta_1198625455580757.json'
store = json.load(open(W + '/data/ads_store.json'))
d = json.load(open(IN))
def size(it):
    s = json.dumps(it, indent=2, ensure_ascii=False)
    return len(s.encode()) + 8 * (s.count('\n') + 1)
# model: estimate unknown ad size from input rows
rows = {}
for r in d:
    rows.setdefault(r['ad_id'], []).append(r)
def est(aid):
    rs = rows[aid]
    slot0 = rs[0]['slot']
    name = rs[0]['ad_name']
    url = rs[0]['url_11oct'] or ''
    nb = lambda s: len(s.encode())
    if 'asset_feed_spec' in slot0:
        return 1250 + nb(name) + nb(url) + 3 * 130
    if any('child_attachments' in r['slot'] for r in rs):
        nchild = sum(1 for r in rs if 'child_attachments' in r['slot'])
        return 1350 + nb(name) + nb(url) * (1 + nchild) + nchild * 230
    return 1250 + nb(name) + nb(url)
# calibrate on stored
errs = []
for aid, it in store.items():
    if aid in rows:
        errs.append(size(it) - est(aid))
print('calib err min/max/mean', min(errs), max(errs), sum(errs) / len(errs))
order = [l.strip() for l in open(W + '/data/order.txt') if l.strip()]
rem = [a for a in order if a not in store]
print('remaining', len(rem))
target = int(sys.argv[1]) if len(sys.argv) > 1 else 61000
maxn = 25
groups = []
cur = []; tot = 0
for a in rem:
    e = est(a)
    if cur and (tot + e > target or len(cur) >= maxn):
        groups.append((cur, tot)); cur = []; tot = 0
    cur.append(a); tot += e
if cur: groups.append((cur, tot))
known = sorted(store, key=lambda a: size(store[a]))
for g, t in groups:
    print(len(g), t)
json.dump([g for g, t in groups], open(W + '/data/groups.json', 'w'))
