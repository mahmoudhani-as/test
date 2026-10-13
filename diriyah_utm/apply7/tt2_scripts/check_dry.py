"""Read-only: compare the latest dry-run ad/update for <ad_id> with the latest successful ad/get before it."""
import json, sys
from urllib.parse import urlsplit, parse_qsl
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply7/tt2_scripts')
from txlib import calls_for, ad_from, unit
AD = sys.argv[1]
U = unit(AD); c = U['changes'][0]
cs = calls_for(AD)
dry = [(i, u, j) for i, (u, j, t) in enumerate(cs) if u['input'].get('action') == 'tiktok_ad_update' and u['input'].get('dry_run') is True]
i, du, dj = dry[-1]
reads = [(u, j) for (u, j, t) in cs[:i] if u['input'].get('action') == 'tiktok_ad_get' and j and j.get('success')]
r = reads[-1][1]; a = ad_from(r, AD)
sent = du['input']['payload']; cr = sent['creatives'][0]
q = parse_qsl(urlsplit(c['new']).query, keep_blank_values=True)
ok = dj['data']['data']['request']['body'] == sent and sent['advertiser_id'] == a['advertiser_id'] == U['account_id'] and sent['adgroup_id'] == a['adgroup_id'] and len(sent['creatives']) == 1 and cr['ad_id'] == AD
for k, v in cr.items():
    if k == 'landing_page_url': t = v == c['new']
    elif k == 'utm_params': t = v == [{'key': kk, 'value': vv} for kk, vv in q] and not any(p['key'] == 'utm_id' for p in v)
    elif k == 'tracking_pixel_id': t = v == '7347671240183693330' and float(int(v)) == float(a['tracking_pixel_id'])
    else: t = (v == a[k])
    if not t: print(' DIFF', k, repr(v)[:200], repr(a.get(k))[:200])
    ok &= t
notsent = sorted(k for k in a if k not in cr and a[k] not in (None, '', [], {}, False, 'UNSET'))
ok &= notsent == ['adgroup_id', 'adgroup_name', 'advertiser_id', 'campaign_automation_type', 'campaign_id', 'campaign_name', 'create_time', 'is_new_structure', 'modify_time', 'operation_status', 'profile_image_url', 'secondary_status']
ok &= a['identity_type'] == 'CUSTOMIZED_USER' and not a.get('tiktok_item_id') and a['landing_page_url'] == c['now']
print(AD, 'read req', r['data']['data']['request_id'], '| before==now', a['landing_page_url'] == c['now'], '| DRY RUN OK (preview==payload, all creative fields as read except URL+UTM):', ok)
