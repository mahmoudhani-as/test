import json, sys, os, uuid

# usage: python3 -I payload.py <asset_id> [<asset_id> ...]
# Prints the exact MutateAssets params (final_urls only, mask final_urls) and an idempotency key
# (stable per asset set via a ledger, so a retry reuses the same key).
BASE = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
W = BASE + '/apply9/work_google_sl_1'
units = {u['unit']: u for u in json.load(open(BASE + '/apply9/in_google_sl_1.json'))}
excl = {str(e.get('ad_id')) for e in json.load(open(BASE + '/work/excl_platform_refused_v2.json'))}
ids = sys.argv[1:]
ops = []
for aid in ids:
    u = units[aid]
    assert u['unit_type'] == 'sitelink_asset' and len(u['changes']) == 1, aid
    assert aid not in excl, 'EXCLUDED ' + aid
    ops.append({'update': {'resource_name': 'customers/%s/assets/%s' % (u['account_id'], aid),
                           'final_urls': [u['changes'][0]['new']]}, 'update_mask': 'final_urls'})
params = {'operations': ops}
ledger_p = W + '/idem_ledger.json'
ledger = json.load(open(ledger_p)) if os.path.exists(ledger_p) else {}
k = ','.join(ids)
ledger.setdefault(k, str(uuid.uuid4()))
json.dump(ledger, open(ledger_p, 'w'), indent=1)
json.dump(params, open(W + '/payload_%s.json' % (ids[0] if len(ids) == 1 else 'batch_%d' % len(ids)), 'w'), ensure_ascii=False, indent=1)
print('KEY', ledger[k])
print('PARAMS', json.dumps(params, ensure_ascii=False))
