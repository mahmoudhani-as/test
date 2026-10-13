import json, sys
B = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
W = B + '/reread3/work_meta_1198625455580757'
IN = B + '/reread/in/meta_1198625455580757.json'
prev = json.load(open(B + '/reread2/work_meta_1198625455580757/data/ads_store.json'))
d = json.load(open(IN))
target = int(sys.argv[1]) if len(sys.argv) > 1 else 57000
skip = set(sys.argv[2].split(',')) if len(sys.argv) > 2 and sys.argv[2] else set()
def size(it):
    t = json.dumps(it, indent=2, ensure_ascii=False)
    return len(t.encode()) + 10 * (t.count('\n') + 1) + 120  # +120: longer creative names after 13-Oct fixes
ids = []
for r in d:
    if r['ad_id'] not in ids:
        ids.append(r['ad_id'])
groups = []; cur = []; tot = 0
for a in ids:
    if a in skip:
        continue
    e = size(prev[a]) if a in prev else 4600
    if cur and tot + e > target:
        groups.append((cur, tot)); cur = []; tot = 0
    cur.append(a); tot += e
if cur:
    groups.append((cur, tot))
STAT = ['ACTIVE','PAUSED','DELETED','PENDING_REVIEW','DISAPPROVED','PREAPPROVED','PENDING_BILLING_INFO','CAMPAIGN_PAUSED','ARCHIVED','ADSET_PAUSED','IN_PROCESS','WITH_ISSUES']
json.dump([g for g, t in groups], open(W + '/data/groups.json', 'w'))
for i, (g, t) in enumerate(groups):
    print('GROUP', i, len(g), 'ads est', t)
    print(json.dumps([{'field': 'effective_status', 'operator': 'IN', 'value': STAT}, {'field': 'id', 'operator': 'IN', 'value': g}], separators=(',', ':')))
