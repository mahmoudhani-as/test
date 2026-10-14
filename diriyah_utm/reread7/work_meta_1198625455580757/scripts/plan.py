import json
B = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
W = B + '/reread7/work_meta_1198625455580757'
prev = json.load(open(B + '/reread5/work_meta_1198625455580757/data/ads_store.json'))
inp = json.load(open(B + '/reread/in/meta_1198625455580757.json'))
ids = list(dict.fromkeys(r['ad_id'] for r in inp))
assert len(ids) == 84, len(ids)
missing = [a for a in ids if a not in prev]
assert not missing, missing


def env(items):
    o = {'success': True, 'data': {'success': True, 'action': 'meta_ad_account_id_ads_get', 'method': 'GET', 'host': 'graph.facebook.com',
         'path': '/v25.0/act_1198625455580757/ads', 'dryRun': False, 'data': {'data': items},
         'meta': {'requestId': None, 'waitedMs': 618, 'throttled': False, 'warnings': [], 'compatibility': None, 'compatibilitySkipped': True,
                  'mcp_result_projection': {'compact': True}}}, 'meta': {'requestId': '3245ed6e-069f-4c53-9bd9-ebbdc745df3d', 'latencyMs': 3025}}
    return len(json.dumps(o, indent=2, ensure_ascii=False).encode('utf-8'))


clean = {a: {k: v for k, v in prev[a].items() if not k.startswith('_')} for a in ids}
base = env([])
E = {a: env([clean[a]]) - base for a in ids}
NG = 4
order = sorted(ids, key=lambda a: -E[a])
groups = [[] for _ in range(NG)]
for a in order:
    i = min(range(NG), key=lambda k: env([clean[x] for x in groups[k]]))
    groups[i].append(a)
LOW, HIGH = 56000, 59500
small = sorted(ids, key=lambda a: E[a])
out = []
for g in groups:
    pad = []
    cur = env([clean[x] for x in g])
    for a in small:
        if cur >= LOW:
            break
        if a in g or a in pad:
            continue
        nxt = env([clean[x] for x in g + pad + [a]])
        if nxt > HIGH:
            continue
        pad.append(a)
        cur = nxt
    out.append({'ids': g, 'pad': pad, 'est': cur})
json.dump(out, open(W + '/data/groups.json', 'w'))
STAT = ['ACTIVE', 'PAUSED', 'DELETED', 'PENDING_REVIEW', 'DISAPPROVED', 'PREAPPROVED', 'PENDING_BILLING_INFO', 'CAMPAIGN_PAUSED', 'ARCHIVED',
        'ADSET_PAUSED', 'IN_PROCESS', 'WITH_ISSUES']
for i, g in enumerate(out):
    print('GROUP', i, len(g['ids']), '+', len(g['pad']), 'pad; est bytes', g['est'])
    print(json.dumps([{'field': 'effective_status', 'operator': 'IN', 'value': STAT}, {'field': 'id', 'operator': 'IN', 'value': g['ids'] + g['pad']}],
                     separators=(',', ':')))
assert sorted(sum((g['ids'] for g in out), [])) == sorted(ids)
print('NOT_IN filter for new ads:')
print(json.dumps([{'field': 'effective_status', 'operator': 'IN', 'value': STAT}, {'field': 'id', 'operator': 'NOT_IN', 'value': ids}],
                 separators=(',', ':')))
