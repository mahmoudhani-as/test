import json, sys
W = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/reread2/work_meta_1198625455580757'
IN = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/reread/in/meta_1198625455580757.json'
store = json.load(open(W + '/data/ads_store.json'))
d = json.load(open(IN))
def size(it):
    s = json.dumps(it, indent=2, ensure_ascii=False)
    return len(s.encode()) + 8 * (s.count('\n') + 1)
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
        v = 1250 + nb(name) + nb(url) + 3 * 130
    elif any('child_attachments' in r['slot'] for r in rs):
        nchild = sum(1 for r in rs if 'child_attachments' in r['slot'])
        v = 1350 + nb(name) + nb(url) * (1 + nchild) + nchild * 230
    else:
        v = 1250 + nb(name) + nb(url)
    return v + 240
order = [l.strip() for l in open(W + '/data/order.txt') if l.strip()]
rem = [a for a in order if a not in store]
target = int(sys.argv[1]); lo = int(sys.argv[2]); maxn = int(sys.argv[3])
groups = []; cur = []; tot = 0
for a in rem:
    e = est(a)
    if cur and (tot + e > target or len(cur) >= maxn):
        groups.append([cur, tot]); cur = []; tot = 0
    cur.append(a); tot += e
if cur: groups.append([cur, tot])
known = [a for a in order if a in store]
known_sorted = sorted(known, key=lambda a: -size(store[a]))
out = []
for g, t in groups:
    pad = []
    for a in known_sorted:
        if t >= lo or len(g) + len(pad) >= maxn: break
        if t + size(store[a]) <= target:
            pad.append(a); t += size(store[a])
    out.append({'unknown': g, 'pad': pad, 'est': t, 'n': len(g) + len(pad)})
    print(len(g), 'unknown +', len(pad), 'pad =', len(g) + len(pad), 'items, est', t)
json.dump(out, open(W + '/data/groups.json', 'w'))
flt0 = {'field': 'effective_status', 'operator': 'IN', 'value': ['ACTIVE','PAUSED','DELETED','PENDING_REVIEW','DISAPPROVED','PREAPPROVED','PENDING_BILLING_INFO','CAMPAIGN_PAUSED','ARCHIVED','ADSET_PAUSED','IN_PROCESS','WITH_ISSUES']}
for i, g in enumerate(out):
    print('GROUP', i, json.dumps([flt0, {'field': 'id', 'operator': 'IN', 'value': g['unknown'] + g['pad']}], separators=(',', ':')))
