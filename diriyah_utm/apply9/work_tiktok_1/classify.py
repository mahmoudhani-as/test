# usage: python3 -I classify.py   (read-only: classify each input ad from the newest ad/get read in my transcript)
import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply9/work_tiktok_1')
from h import *

R = ad_reads()
for u in INP:
    ad = u['unit']
    ch = u['changes'][0]
    assert len(u['changes']) == 1 and ch['slot'] == 'ad.landing_page_url', ad
    rr = R.get(ad)
    if not rr:
        print('==', ad, 'NOT READ YET')
        continue
    rid, a = rr[-1]
    assert '__mcp_truncated' not in json.dumps(a), 'truncated'
    cur, extra, conflict = eff_url(a.get('landing_page_url'), a.get('utm_params'))
    cls = classify(a)
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
    print('==', ad, cls, dec, 'probs:', probs)
    print('   rid=%s reads=%d op=%s sec=%s fmt=%s cta=%s cta_id=%s card=%s item=%s pixel=%r mod=%s adgroup=%s' % (
        rid, len(rr), a.get('operation_status'), a.get('secondary_status'), a.get('ad_format'), a.get('call_to_action'),
        a.get('call_to_action_id'), a.get('card_id'), a.get('tiktok_item_id'), a.get('tracking_pixel_id'), a.get('modify_time'),
        a.get('adgroup_id')))
    print('   cur == now:', cur == ch['now'], '| cur in alt:', cur in ch['alt_now'], '| cur~new:', equiv(cur, ch['new']),
          '| url field == cur:', a.get('landing_page_url') == cur, '| utm keys:', [x['key'] for x in (a.get('utm_params') or [])],
          '| text notes:', text_notes(a.get('ad_text')), '| ad_text:', repr(a.get('ad_text')))
    if cls in ('SPARK_PULL', 'CUSTOMIZED_USER', 'BC_AUTH_TT_NO_ITEM'):
        exp = expected_payload(u, a)
        sent_keys = set(exp['creatives'][0])
        ro = {'adgroup_name', 'campaign_name', 'campaign_id', 'adgroup_id', 'advertiser_id', 'secondary_status', 'operation_status',
              'modify_time', 'create_time', 'profile_image_url', 'is_new_structure', 'campaign_automation_type', 'is_aco',
              'deeplink_type', 'viewability_postbid_partner', 'brand_safety_postbid_partner', 'optimization_event', 'ad_ref_pixel_id',
              'app_name', 'display_name', 'product_info'}
        unsent = sorted(k for k, v in a.items() if v not in (None, '', [], {}, False, 0) and k not in sent_keys and k not in ro)
        print('   unsent non-empty fields (not read-only):', unsent)
        print('   expected payload:', json.dumps(exp, ensure_ascii=False))
