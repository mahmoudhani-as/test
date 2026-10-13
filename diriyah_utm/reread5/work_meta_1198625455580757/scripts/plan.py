import json
B = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
W = B + '/reread5/work_meta_1198625455580757'
prev = json.load(open(B + '/reread4/work_meta_1198625455580757/data/ads_store.json'))
ids = json.load(open(W + '/data/list_ids.json'))
def est(it):
    it = {k: v for k, v in it.items() if not k.startswith('_')}
    t = json.dumps(it, indent=2, ensure_ascii=False)
    return len(t.encode('utf-8')) + 10 * (t.count('\n') + 1) + 200
E = {a: est(prev[a]) for a in ids}
NG = 5
tot = sum(E.values())
print('total est', tot, 'per group', tot / NG, 'max single', max(E.values()))
# greedy bin packing, largest first, into NG bins
order = sorted(ids, key=lambda a: -E[a])
groups = [[] for _ in range(NG)]
sz = [0] * NG
for a in order:
    i = min(range(NG), key=lambda k: sz[k])
    groups[i].append(a)
    sz[i] += E[a]
STAT = ['ACTIVE','PAUSED','DELETED','PENDING_REVIEW','DISAPPROVED','PREAPPROVED','PENDING_BILLING_INFO','CAMPAIGN_PAUSED','ARCHIVED','ADSET_PAUSED','IN_PROCESS','WITH_ISSUES']
out = []
for g, s in zip(groups, sz):
    out.append({'ids': g, 'est': s})
json.dump(out, open(W + '/data/groups.json', 'w'))
for i, g in enumerate(out):
    print('GROUP', i, len(g['ids']), 'est', g['est'])
    print(json.dumps(json.dumps([{'field': 'effective_status', 'operator': 'IN', 'value': STAT}, {'field': 'id', 'operator': 'IN', 'value': g['ids']}], separators=(',', ':'))))
