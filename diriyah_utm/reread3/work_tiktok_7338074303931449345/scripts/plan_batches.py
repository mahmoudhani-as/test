import json, statistics, sizemodel as sm
W = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/reread3/work_tiktok_7338074303931449345'
FM = ["ad_id","ad_name","campaign_id","campaign_name","adgroup_id","adgroup_name","campaign_automation_type","ad_format",
      "landing_page_url","landing_page_urls","utm_params","deeplink","page_id","cpp_url","operation_status","secondary_status",
      "create_time","modify_time","smart_plus_ad_id"]
FS = ["ad_name","adgroup_id","campaign_id","create_time","modify_time","landing_page_url_list","deeplink_list","utm_params",
      "operation_status","secondary_status"]
inv = [l.rstrip('\n').split('\t') for l in open(W+'/raw/inventory_ad_get_STATUS_ALL.tsv') if not l.startswith('#')]
spinv = [l.rstrip('\n').split('\t') for l in open(W+'/raw/inventory_smart_plus_ad_get_STATUS_ALL.tsv') if not l.startswith('#')]
m = sm.SNAP['manual']; s = sm.SNAP['smart_plus']
agn, cn = {}, {}
for a, v in m.items():
    if v.get('adgroup_name'): agn[v['adgroup_id']] = v['adgroup_name']
    if v.get('campaign_name'): cn[v['campaign_id']] = v['campaign_name']
EXTRA = 30  # cpp_url etc. unknown
def mcost(a):
    v = m.get(a)
    if v is None: return None
    r = {k: v[k] for k in FM if k in v}
    r.setdefault('adgroup_name', agn.get(v['adgroup_id'], 'x'*95))
    r.setdefault('campaign_name', cn.get(v['campaign_id'], 'x'*100))
    return sm.item_cost(r) + EXTRA
def scost(a):
    v = s.get(a)
    if v is None: return None
    return sm.item_cost(v)
manual_ids = [r[0] for r in inv if r[1] == 'M']
new_children = [r[0] for r in inv if r[1] == 'C' and r[4].startswith('2026-10-13')]
known = {a: mcost(a) for a in manual_ids}
kn = [c for c in known.values() if c]
new12 = [known[a] for a in manual_ids if a.startswith('187883') and known[a]]
est_new = round(statistics.mean(new12)) if new12 else 1500
print('manual known', len(kn), 'unknown', sum(1 for c in known.values() if c is None), 'est for unknown (mean of 12 Oct-12 ads)', est_new)
items = [(a, known[a] if known[a] else est_new, 'M') for a in manual_ids] + [(a, 1000, 'C') for a in new_children]
tot = sum(c for _, c, _ in items)
print('items', len(items), 'total', tot, 'per batch of 3 incl wrapper', round(tot/3 + 745))
# greedy balance into 3 batches
B = [[], [], []]
for a, c, t in sorted(items, key=lambda x: -x[1]):
    i = min(range(3), key=lambda k: sum(x[1] for x in B[k]))
    B[i].append((a, c, t))
for i, b in enumerate(B):
    print('M batch', i, len(b), 'est bytes', sum(x[1] for x in b) + 745, 'unknown-size items', sum(1 for x in b if x[0] not in m))
# smart+: 111 parents (incl 8 deleted)
sp_ids = [r[0] for r in spinv]
sk = {a: scost(a) for a in sp_ids}
skn = [c for c in sk.values() if c]
est_s = round(statistics.mean(skn))
sitems = [(a, sk[a] if sk[a] else est_s) for a in sp_ids]
print('smart known', len(skn), 'unknown', len(sp_ids)-len(skn), 'est', est_s, 'total', sum(c for _, c in sitems))
SB = [[], [], []]
for a, c in sorted(sitems, key=lambda x: -x[1]):
    i = min(range(3), key=lambda k: sum(x[1] for x in SB[k]))
    SB[i].append((a, c))
for i, b in enumerate(SB):
    print('S batch', i, len(b), 'est bytes', sum(x[1] for x in b) + 760, 'unknown-size', sum(1 for x in b if x[0] not in s))
json.dump({'fields_manual': FM, 'fields_smart': FS,
           'manual_batches': [[x[0] for x in b] for b in B], 'manual_est': [sum(x[1] for x in b) + 745 for b in B],
           'smart_batches': [[x[0] for x in b] for b in SB], 'smart_est': [sum(x[1] for x in b) + 760 for b in SB]},
          open(W+'/batches.json', 'w'), indent=1)
