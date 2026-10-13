import json, sys
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply9/work_google_2')
from lib import *

# usage: python3 -I verify.py <out_readback.json> <readback_req_id> [more req ids] -- <unit_id> [<unit_id> ...]
# Byte-for-byte check of the GAQL read-back against "new" for each listed unit.
args = sys.argv[1:]
out_path = args[0]
sep = args.index('--')
req_ids = args[1:sep]
want = args[sep + 1:]
rows = {}
for rid in req_ids:
    rs, trunc, budget, inp = gaql_rows(rid)
    if trunc or (budget and budget.get('truncated')):
        print('WARNING truncated result in', rid)
    for r in rs:
        aga = r['adGroupAd']; ad = aga['ad']
        rows[ad['id']] = {
            'req': rid, 'final_urls': ad.get('finalUrls', []), 'final_url_suffix': ad.get('finalUrlSuffix'),
            'tracking_url_template': ad.get('trackingUrlTemplate'), 'status': aga.get('status'),
            'approval': (aga.get('policySummary') or {}).get('approvalStatus'),
            'campaign_status': r['campaign'].get('status'), 'ad_group': r['adGroup']['id'],
            'parent_suffix': [r['adGroup'].get('finalUrlSuffix'), r['campaign'].get('finalUrlSuffix'), r['customer'].get('finalUrlSuffix')],
            'parent_tut': [r['adGroup'].get('trackingUrlTemplate'), r['campaign'].get('trackingUrlTemplate'), r['customer'].get('trackingUrlTemplate')],
            'landing': landing(ad)}
U = {u['unit']: u for u in units()}
out = {}
for aid in want:
    u = U[aid]; ch = u['changes'][0]
    r = rows.get(aid)
    if r is None:
        print(aid, 'NOT IN READ-BACK'); out[aid] = None; continue
    byte_eq = (r['final_urls'] == [ch['new']]) and not r['final_url_suffix'] and r['landing'] == ch['new']
    parents_clean = not any(r['parent_suffix']) and not any(r['parent_tut']) and not r['tracking_url_template']
    out[aid] = dict(r, byte_equal_new=byte_eq, parents_clean=parents_clean)
    print(aid, 'BYTE_EQUAL_NEW' if byte_eq else 'MISMATCH', 'parents_clean' if parents_clean else 'PARENT/TRACKING SET',
          r['status'], r['campaign_status'], r['approval'], r['req'])
    if not byte_eq:
        print('   live:', json.dumps(r['final_urls'], ensure_ascii=False), 'suffix:', r['final_url_suffix'])
        print('   new :', ch['new'])
json.dump(out, open(out_path, 'w'), indent=1, ensure_ascii=False)
print('verified', sum(1 for v in out.values() if v and v['byte_equal_new']), 'of', len(want))
