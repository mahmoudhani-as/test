import json, sys
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply9/work_google_2')
from lib import *

# usage: python3 -I preread.py <out.json> <req_id> [<req_id> ...]
out_path = sys.argv[1]
req_ids = sys.argv[2:]
rows = {}
parents = {}
for rid in req_ids:
    rs, trunc, budget, inp = gaql_rows(rid)
    if trunc or (budget and budget.get('truncated')):
        print('WARNING truncated result in', rid, trunc, budget)
    for r in rs:
        aga = r['adGroupAd']
        ad = aga['ad']
        aid = ad['id']
        if aid in rows:
            print('WARNING duplicate row for ad', aid, 'in', rid)
        rows[aid] = {
            'req': rid,
            'type': ad.get('type'),
            'final_urls': ad.get('finalUrls', []),
            'final_url_suffix': ad.get('finalUrlSuffix'),
            'tracking_url_template': ad.get('trackingUrlTemplate'),
            'ad_group_ad_status': aga.get('status'),
            'approval': (aga.get('policySummary') or {}).get('approvalStatus'),
            'ad_group': r['adGroup']['id'], 'ad_group_name': r['adGroup'].get('name'),
            'ad_group_suffix': r['adGroup'].get('finalUrlSuffix'), 'ad_group_tut': r['adGroup'].get('trackingUrlTemplate'),
            'campaign': r['campaign']['id'], 'campaign_status': r['campaign'].get('status'),
            'campaign_suffix': r['campaign'].get('finalUrlSuffix'), 'campaign_tut': r['campaign'].get('trackingUrlTemplate'),
            'customer_suffix': r['customer'].get('finalUrlSuffix'), 'customer_tut': r['customer'].get('trackingUrlTemplate'),
            'landing': landing(ad),
        }

U = units()
ex = excluded()
plan = []
from collections import Counter
cnt = Counter()
for u in U:
    for ch in u['changes']:
        aid = u['unit']
        r = rows.get(aid)
        if r is None:
            plan.append({'unit': aid, 'slot': ch['slot'], 'cls': 'MISSING'})
            cnt['MISSING'] += 1
            continue
        cur = r['landing']
        cls = classify(cur, ch)
        flags = []
        if len(r['final_urls']) != 1: flags.append('final_urls_len=%d' % len(r['final_urls']))
        for k in ('final_url_suffix', 'tracking_url_template', 'ad_group_suffix', 'ad_group_tut', 'campaign_suffix', 'campaign_tut', 'customer_suffix', 'customer_tut'):
            if r.get(k): flags.append('%s=%s' % (k, r[k]))
        if (aid, ch['slot']) in ex: flags.append('EXCLUDED')
        exact_now = (cur == ch['now'])
        plan.append({'unit': aid, 'slot': ch['slot'], 'cls': cls, 'exact_now': exact_now,
                     'cur_eq_new_bytes': cur == ch['new'], 'flags': flags,
                     'type': r['type'], 'status': r['ad_group_ad_status'], 'approval': r['approval'],
                     'ad_group': r['ad_group'], 'ad_group_name': r['ad_group_name'], 'campaign': r['campaign'],
                     'campaign_status': r['campaign_status'], 'req': r['req'], 'cur': cur})
        cnt[cls] += 1
json.dump({'rows': rows, 'plan': plan}, open(out_path, 'w'), indent=1, ensure_ascii=False)
print('rows read:', len(rows), 'units:', len(U), 'changes:', sum(len(u['changes']) for u in U))
print('classes:', dict(cnt))
for p in plan:
    if p['cls'] != 'Write' or not p.get('exact_now') or p.get('flags'):
        print('NOTE', json.dumps(p, ensure_ascii=False)[:600])
print('types:', Counter(p.get('type') for p in plan))
print('approval:', Counter(p.get('approval') for p in plan))
print('status:', Counter((p.get('status'), p.get('campaign_status')) for p in plan))
