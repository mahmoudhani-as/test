# usage: python3 -I classify.py <saved ad/get result> [...]
# Read-only: classify each input ad from the saved ad/get text and decide AlreadyFixed / Write / Skipped / Hold.
import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply8/work_tiktok_1/scripts')
from common import *

ads = {}
rids = {}
for p in sys.argv[1:]:
    j = load_tool_json(p)
    assert j['success'] and j['data']['data']['code'] == 0, str(j)[:500]
    rid = j['data']['data']['request_id']
    for a in j['data']['data']['data']['list']:
        assert '__mcp_truncated' not in json.dumps(a), 'truncated'
        ads[a['ad_id']] = a
        rids[a['ad_id']] = rid

for u in INP:
    ad = u['unit']
    if u['changes'][0]['slot'] != 'ad.landing_page_url':
        print('==', ad, 'slot', u['changes'][0]['slot'], '(not a manual ad slot; skip here)')
        continue
    a = ads.get(ad)
    if a is None:
        print('==', ad, 'NOT IN READ')
        continue
    ch = u['changes'][0]
    cur, extra, conflict = eff_url(a.get('landing_page_url'), a.get('utm_params'))
    idt = a.get('identity_type')
    item = a.get('tiktok_item_id')
    if idt == 'BC_AUTH_TT' and item:
        cls = 'SPARK_PUSH_HOLD'
    elif idt == 'AUTH_CODE':
        cls = 'SPARK_PULL'
    elif idt == 'BC_AUTH_TT':
        cls = 'BC_NO_ITEM'
    elif idt == 'CUSTOMIZED_USER':
        cls = 'CUSTOMIZED_USER'
    else:
        cls = 'OTHER:' + str(idt)
    if equiv(cur, ch['new']):
        dec = 'AlreadyFixed'
    elif cur == ch['now'] or cur in ch['alt_now']:
        dec = 'Write'
    else:
        dec = 'Skipped'
    probs = []
    if conflict:
        probs.append('utm_params conflict %r' % conflict)
    if extra:
        probs.append('utm_params keys not in URL %r' % extra)
    if excluded(ad, ch['slot']):
        probs.append('EXCLUDED (platform-refused)')
    if a.get('ad_name') != u['ad_names'][0]:
        probs.append('ad_name differs from plan: %r' % a.get('ad_name'))
    if a.get('advertiser_id') != u['account_id']:
        probs.append('advertiser differs')
    tn = text_notes(a.get('ad_text'))
    print('==', ad, cls, dec, 'probs:', probs)
    print('   rid=%s op=%s sec=%s fmt=%s cta=%s cta_id=%s card=%s item=%s pixel=%r mod=%s adgroup=%s' % (
        rids[ad], a.get('operation_status'), a.get('secondary_status'), a.get('ad_format'), a.get('call_to_action'),
        a.get('call_to_action_id'), a.get('card_id'), item, a.get('tracking_pixel_id'), a.get('modify_time'), a.get('adgroup_id')))
    print('   cur == now:', cur == ch['now'], '| cur in alt:', cur in ch['alt_now'], '| cur~new:', equiv(cur, ch['new']),
          '| url field == cur:', a.get('landing_page_url') == cur, '| utm keys:', [x['key'] for x in (a.get('utm_params') or [])],
          '| text notes:', tn)
    other = sorted(k for k, v in a.items() if v not in (None, '', [], {}, False) and k not in (
        'ad_id', 'ad_name', 'identity_id', 'identity_type', 'ad_format', 'video_id', 'image_ids', 'ad_text', 'call_to_action',
        'landing_page_url', 'utm_params', 'tracking_pixel_id', 'display_name', 'avatar_icon_web_uri', 'aigc_disclosure_type',
        'creative_authorized', 'vast_moat_enabled', 'adgroup_name', 'campaign_name', 'campaign_id', 'adgroup_id', 'advertiser_id',
        'secondary_status', 'operation_status', 'modify_time', 'create_time', 'profile_image_url', 'is_new_structure',
        'campaign_automation_type', 'deeplink_type', 'viewability_postbid_partner', 'brand_safety_postbid_partner'))
    print('   other non-empty fields:', other)
