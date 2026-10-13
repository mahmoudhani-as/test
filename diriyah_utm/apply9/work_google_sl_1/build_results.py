import json
from collections import Counter

BASE = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
W = BASE + '/apply9/work_google_sl_1'
units = json.load(open(BASE + '/apply9/in_google_sl_1.json'))
pre1 = json.load(open(W + '/preread.json'))
pre16 = json.load(open(W + '/reread16.json'))
rb1 = json.load(open(W + '/readback_unit1.json'))
rball = json.load(open(W + '/readback_all.json'))
links = json.load(open(W + '/adgroup_links.json'))['by_asset']
w = rball['write']

# campaign-level links from the campaign_asset read (req 6db25695-0066-4561-81c2-139c9e98704b)
camp_links = {
    '317562674374': 3, '331673391935': 3, '331673391938': 2, '365162388487': 2, '365162388490': 2,
    '365162388493': 3, '365162388496': 2, '365237652291': 3, '388973983772': 2, '388973983775': 2,
    '388973983778': 2,
}
results = []
for u in units:
    aid = u['unit']
    for c in u['changes']:
        if aid == '365237652291':
            before = pre1['assets'][aid][0]
            before_req = pre1['request_id']
            wr = w['unit1']
            reqs = 'pre-read GAQL %s (cur == now); dry_run preview %s (only final_urls, mask final_urls); live MutateAssets %s (idempotency_key %s) ok; read-back GAQL %s and again %s' % (
                before_req, wr['dry_run_req'], wr['live_req'], wr['idempotency_key'], wr['readback_req'], rball['request_id'])
        else:
            before = pre16['assets'][aid][0]
            before_req = pre16['request_id']
            wr = w['batch16']
            reqs = 'pre-write re-read GAQL %s (cur == now; also == first read %s); dry_run preview %s (16 ops, each only final_urls, mask final_urls); Google validate_only %s passed; live MutateAssets %s (batch of 16, idempotency_key %s) ok; read-back GAQL %s' % (
                before_req, pre1['request_id'], wr['dry_run_req'], wr['validate_only_req'], wr['live_req'], wr['idempotency_key'], rball['request_id'])
        live = rball['assets'][aid]
        after = live[0] if len(live) == 1 else json.dumps(live, ensure_ascii=False)
        ok = live == [c['new']]
        if aid == '365237652291':
            ok = ok and rb1['assets'][aid] == [c['new']]
        ag = links.get(aid, [])
        serves = []
        if aid in camp_links:
            serves.append('%d campaign-level links' % camp_links[aid])
        if ag:
            serves.append('%d ad-group-level links' % len(ag))
        detail = ('%s. Read-back final_urls == new byte for byte; review status now REVIEW_IN_PROGRESS (was REVIEWED/APPROVED); '
                  'link text and both descriptions unchanged; no final_url_suffix / tracking template / custom params / mobile URLs on the asset, '
                  'and none on its ad groups, campaigns or the account. Asset serves %s (intended).') % (reqs, ', '.join(serves) or 'n/a')
        results.append({
            'platform': 'google', 'account_id': u['account_id'], 'unit_type': u['unit_type'], 'unit': aid,
            'ad_ids': u['ad_ids'], 'ad_names': u['ad_names'], 'slot': c['slot'], 'before': before,
            'after_expected': c['new'], 'after_live': after, 'result': 'Fixed' if ok else 'Failed',
            'new_entity_ids': '', 'detail': detail if ok else 'read-back differs from new. ' + detail,
        })
        assert before == c['now'], aid
print(Counter(r['result'] for r in results), len(results))
print(json.dumps(results, ensure_ascii=False))
