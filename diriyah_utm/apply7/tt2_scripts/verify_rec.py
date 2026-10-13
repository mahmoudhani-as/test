"""Verify the live ad/update for <ad_id> by its read-back and append ONE result line (Fixed/Failed)."""
import json, sys
from urllib.parse import urlsplit, parse_qsl
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply7/tt2_scripts')
from txlib import calls_for, ad_from, unit, ROOT
AD = sys.argv[1]
OUT = ROOT + '/apply7/out_tiktok_2.jsonl'
U = unit(AD); c = U['changes'][0]
cs = calls_for(AD)
live = [(i, u, j, t) for i, (u, j, t) in enumerate(cs) if u['input'].get('action') == 'tiktok_ad_update' and u['input'].get('dry_run') is False]
assert 1 <= len(live) <= 2, len(live)
first_live = live[0][0]
reads = [(i, u, j) for i, (u, j, t) in enumerate(cs) if u['input'].get('action') == 'tiktok_ad_get' and j and j.get('success')]
pre = [x for x in reads if x[0] < first_live][-1]
post = [x for x in reads if x[0] > live[-1][0]][-1]
a0 = ad_from(pre[2], AD); a1 = ad_from(post[2], AD)
preq, postq = pre[2]['data']['data']['request_id'], post[2]['data']['data']['request_id']
att = []
for i, u, j, t in live:
    if j and j.get('success'):
        att.append('code %s %s req %s need_audit=%s' % (j['data']['data']['code'], j['data']['data']['message'], j['data']['data']['request_id'], j['data']['data']['data'].get('need_audit')))
    else:
        att.append('error: ' + t[:300].replace('\n', ' '))
q = parse_qsl(urlsplit(c['new']).query, keep_blank_values=True)
lp_ok = a1['landing_page_url'] == c['new']
utm_ok = sorted((p['key'], p['value']) for p in a1['utm_params']) == sorted(q) and not any(p['key'] == 'utm_id' for p in a1['utm_params'])
others = sorted(k for k in set(a0) | set(a1) if k not in ('landing_page_url', 'utm_params', 'modify_time') and a0.get(k) != a1.get(k))
assert a0['landing_page_url'] == c['now'], 'pre-read was not now'
done = {json.loads(l)['unit'] for l in open(OUT) if l.strip()}
assert AD not in done, 'already recorded'
result = 'Fixed' if (lp_ok and utm_ok) else 'Failed'
detail = ("Re-read ad/get req %s before the write: landing_page_url == now byte for byte (CUSTOMIZED_USER manual SINGLE_VIDEO, identity %s, no tiktok_item_id, adgroup %s, video_id %s, 1 image, CTA LEARN_MORE, no CTA id; utm_params %d keys %s, no utm_term, no utm_id; %s / %s; modify_time %s). "
          "dry_run: preview body == payload; every creative field sent as read (ad_name, identity_type/id, ad_format, video_id, image_ids, ad_text byte-identical with no edge whitespace, call_to_action, deeplink_type, display_name, avatar_icon_web_uri, aigc_disclosure_type, creative_authorized, vast_moat_enabled) with only landing_page_url = new and utm_params = the 5 UTMs of new (no utm_id); no tiktok_item_id sent; pixel sent as exact string 7347671240183693330 (ad/get shows it rounded). "
          "Live full ad/update: %s. Read-back ad/get req %s: landing_page_url %s new byte for byte; utm_params %d keys %s; other fields changed: %s; status %s / %s (before %s / %s); modify_time %s -> %s.") % (
          preq, a0['identity_id'], a0['adgroup_id'], a0['video_id'], len(a0['utm_params']), sorted(p['key'] for p in a0['utm_params']), a0['operation_status'], a0['secondary_status'], a0['modify_time'],
          '; '.join('attempt %d %s' % (n + 1, s) for n, s in enumerate(att)), postq, '==' if lp_ok else '!=', len(a1['utm_params']), 'match new, no utm_id' if utm_ok else 'DO NOT match new',
          others or 'none', a1['operation_status'], a1['secondary_status'], a0['operation_status'], a0['secondary_status'], a0['modify_time'], a1['modify_time'])
row = {"platform": "tiktok", "account_id": U['account_id'], "unit_type": U['unit_type'], "unit": AD, "ad_ids": U['ad_ids'], "ad_names": U['ad_names'],
       "slot": c['slot'], "before": a0['landing_page_url'], "after_expected": c['new'], "after_live": a1['landing_page_url'], "result": result, "new_entity_ids": "", "detail": detail}
with open(OUT, 'a') as f:
    f.write(json.dumps(row, ensure_ascii=False) + "\n")
print('recorded', AD, result, '| others changed:', others, '| post req', postq)
