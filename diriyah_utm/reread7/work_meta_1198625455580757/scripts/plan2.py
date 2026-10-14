import json
B = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
W = B + '/reread7/work_meta_1198625455580757'
prev = json.load(open(B + '/reread5/work_meta_1198625455580757/data/ads_store.json'))
store = json.load(open(W + '/data/ads_store.json'))
ids = json.load(open(W + '/data/list_ids.json'))
todo = [a for a in ids if a not in store]
print('todo', len(todo))


def env(items):
    o = {'success': True, 'data': {'success': True, 'action': 'meta_ad_account_id_ads_get', 'method': 'GET', 'host': 'graph.facebook.com',
         'path': '/v25.0/act_1198625455580757/ads', 'dryRun': False, 'data': {'data': items, 'meta': {'aggregate_pages': True, 'pages_fetched': 1}},
         'meta': {'requestId': None, 'waitedMs': 618, 'throttled': False, 'warnings': [], 'compatibility': None, 'compatibilitySkipped': True,
                  'mcp_result_projection': {'compact': True}}}, 'meta': {'requestId': '3245ed6e-069f-4c53-9bd9-ebbdc745df3d', 'latencyMs': 3025}}
    return len(json.dumps(o, indent=2, ensure_ascii=False).encode('utf-8'))


clean = {a: {k: v for k, v in prev[a].items() if not k.startswith('_')} for a in ids}
base = env([])
E = {a: env([clean[a]]) - base for a in ids}
print('todo est total', env([clean[a] for a in todo]))
NG = 3
order = sorted(todo, key=lambda a: -E[a])
groups = [[] for _ in range(NG)]
for a in order:
    i = min(range(NG), key=lambda k: env([clean[x] for x in groups[k]]))
    groups[i].append(a)
LOW, HIGH = 56000, 59000
small = sorted([a for a in ids if a not in todo], key=lambda a: E[a])
out = []
for g in groups:
    pad = []
    cur = env([clean[x] for x in g])
    for a in small:
        if cur >= LOW:
            break
        if a in pad:
            continue
        nxt = env([clean[x] for x in g + pad + [a]])
        if nxt > HIGH:
            continue
        pad.append(a)
        cur = nxt
    out.append({'ids': g, 'pad': pad, 'est': cur})
json.dump(out, open(W + '/data/groups2.json', 'w'))
STAT = ['ACTIVE', 'PAUSED', 'DELETED', 'PENDING_REVIEW', 'DISAPPROVED', 'PREAPPROVED', 'PENDING_BILLING_INFO', 'CAMPAIGN_PAUSED', 'ARCHIVED',
        'ADSET_PAUSED', 'IN_PROCESS', 'WITH_ISSUES']
for i, g in enumerate(out):
    print('GROUP', i, len(g['ids']), '+', len(g['pad']), 'pad; est bytes', g['est'])
    print(json.dumps([{'field': 'effective_status', 'operator': 'IN', 'value': STAT}, {'field': 'id', 'operator': 'IN', 'value': g['ids'] + g['pad']}],
                     separators=(',', ':')))
assert sorted(sum((g['ids'] for g in out), [])) == sorted(todo)
