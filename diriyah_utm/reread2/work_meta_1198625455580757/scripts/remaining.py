import json, sys
W = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/reread2/work_meta_1198625455580757'
IN = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/reread/in/meta_1198625455580757.json'
store = json.load(open(W + '/data/ads_store.json'))
d = json.load(open(IN))
# all ids known in account from lightweight list + input
ids = []
for r in d:
    if r['ad_id'] not in ids:
        ids.append(r['ad_id'])
extra = sys.argv[1].split(',') if len(sys.argv) > 1 and sys.argv[1] else []
for e in extra:
    if e not in ids:
        ids.append(e)
rem = [i for i in ids if i not in store]
pad = int(sys.argv[2]) if len(sys.argv) > 2 else 0
padding = [i for i in ids if i in store][:pad]
print(len(rem), 'remaining;', len(padding), 'padding')
flt = [{'field': 'effective_status', 'operator': 'IN', 'value': ['ACTIVE','PAUSED','DELETED','PENDING_REVIEW','DISAPPROVED','PREAPPROVED','PENDING_BILLING_INFO','CAMPAIGN_PAUSED','ARCHIVED','ADSET_PAUSED','IN_PROCESS','WITH_ISSUES']}, {'field': 'id', 'operator': 'IN', 'value': rem + padding}]
print(json.dumps(flt, separators=(',', ':')))
