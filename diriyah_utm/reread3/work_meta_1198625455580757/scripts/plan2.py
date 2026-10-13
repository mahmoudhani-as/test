import json, sys
B = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
W = B + '/reread3/work_meta_1198625455580757'
IN = B + '/reread/in/meta_1198625455580757.json'
prev = json.load(open(B + '/reread2/work_meta_1198625455580757/data/ads_store.json'))
store = json.load(open(W + '/data/ads_store.json'))
d = json.load(open(IN))
ngroups = int(sys.argv[1]); target = int(sys.argv[2])
def size(it):
    t = json.dumps(it, indent=2, ensure_ascii=False)
    return len(t) + 10 * (t.count('\n') + 1)
ids = []
for r in d:
    if r['ad_id'] not in ids:
        ids.append(r['ad_id'])
rem = [a for a in ids if a not in store]
est = {a: (size(prev[a]) if a in prev else 4600) for a in rem}
tot = sum(est.values())
per = tot / ngroups
groups = [[] for _ in range(ngroups)]; sz = [0] * ngroups
gi = 0
for a in rem:
    if sz[gi] + est[a] / 2 > per * (gi + 1) - sum(sz[:gi]) and gi < ngroups - 1 and groups[gi]:
        gi += 1
    groups[gi].append(a); sz[gi] += est[a]
known = sorted(store, key=lambda a: size(store[a]))
used = set()
out = []
for g, s in zip(groups, sz):
    pad = []
    for a in known:
        if s >= target:
            break
        if a in used:
            continue
        pad.append(a); used.add(a); s += size(store[a])
    out.append({'unknown': g, 'pad': pad, 'est': s})
STAT = ['ACTIVE','PAUSED','DELETED','PENDING_REVIEW','DISAPPROVED','PREAPPROVED','PENDING_BILLING_INFO','CAMPAIGN_PAUSED','ARCHIVED','ADSET_PAUSED','IN_PROCESS','WITH_ISSUES']
json.dump(out, open(W + '/data/groups2.json', 'w'))
for i, g in enumerate(out):
    print('GROUP', i, len(g['unknown']), 'unknown +', len(g['pad']), 'pad; est chars', g['est'])
    print(json.dumps([{'field': 'effective_status', 'operator': 'IN', 'value': STAT}, {'field': 'id', 'operator': 'IN', 'value': g['unknown'] + g['pad']}], separators=(',', ':')))
