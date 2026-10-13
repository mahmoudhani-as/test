# usage: python3 -I build.py <ad_id>
# Read-only: take the newest complete ad/get read of <ad_id> made BEFORE the first update call for it, classify it,
# decide AlreadyFixed / Write / Skipped / Hold, and build the ad/update payload (creative fields as read; only
# landing_page_url = new and utm_params = UTMs of new; pixel as exact string from this run's pixel/list).
# Saves payload_<ad>.json in W. (Adapted from apply10/work_tiktok_1/build.py.)
import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply12/work_tiktok_1')
from common import *

CU_FIELDS = ['ad_id', 'ad_name', 'identity_id', 'identity_type', 'ad_format', 'video_id', 'image_ids', 'ad_text', 'call_to_action',
             'landing_page_url', 'utm_params', 'tracking_pixel_id', 'display_name', 'avatar_icon_web_uri', 'aigc_disclosure_type',
             'creative_authorized', 'vast_moat_enabled']
BC_FIELDS = ['ad_id', 'ad_name', 'identity_type', 'identity_id', 'identity_authorized_bc_id', 'ad_format', 'image_ids', 'music_id',
             'ad_text', 'call_to_action', 'landing_page_url', 'utm_params', 'dark_post_status', 'creative_authorized',
             'vast_moat_enabled', 'tracking_pixel_id']
RO = {'adgroup_name', 'campaign_name', 'campaign_id', 'adgroup_id', 'advertiser_id', 'secondary_status', 'operation_status',
      'modify_time', 'create_time', 'profile_image_url', 'is_new_structure', 'campaign_automation_type', 'is_aco',
      'deeplink_type', 'viewability_postbid_partner', 'brand_safety_postbid_partner', 'optimization_event', 'ad_ref_pixel_id',
      'fallback_type', 'branded_content_disabled', 'app_name', 'product_info'}


def classify(a):
    idt, item = a.get('identity_type'), a.get('tiktok_item_id')
    if idt == 'BC_AUTH_TT' and item:
        return 'SPARK_PUSH_HOLD'
    if idt == 'AUTH_CODE':
        return 'SPARK_PULL'
    if idt == 'BC_AUTH_TT':
        return 'BC_NO_ITEM'
    if idt == 'CUSTOMIZED_USER':
        return 'CUSTOMIZED_USER'
    return 'OTHER:' + str(idt)


def pre_read(ad):
    ups = [i for i, tid, inp, txt, err in calls('tiktok_ad_update')
           if ((inp.get('payload') or {}).get('creatives') or [{}])[0].get('ad_id') == ad]
    first = min(ups) if ups else 10 ** 9
    rr = [r for r in (ad_reads().get(ad) or []) if r[0] < first]
    return rr[-1] if rr else None


def exact_pixel(read_value):
    """exact pixel id string from this run's pixel/list whose numeric value equals the (possibly imprecise) read value"""
    px = pixel_ids()
    m = [p for p in px if float(p) == float(read_value)]
    assert len(m) == 1, ('pixel not uniquely resolved', read_value, px)
    return m[0], px[m[0]]


def build(ad):
    u = INPD[ad]
    assert len(u['changes']) == 1
    ch = u['changes'][0]
    assert ch['slot'] == 'ad.landing_page_url', ch['slot']
    r = pre_read(ad)
    assert r, 'no complete pre-read'
    order, rid, a = r
    cls = classify(a)
    cur, extra, conflict = eff_url(a.get('landing_page_url'), a.get('utm_params'))
    if equiv(cur, ch['new']):
        dec = 'AlreadyFixed'
    elif cur == ch['now'] or cur in ch['alt_now']:
        dec = 'Write'
    else:
        dec = 'Skipped'
    if dec == 'Write' and cls == 'SPARK_PUSH_HOLD' and u.get('recipe') != 'spark_push':
        dec = 'Hold'
    fields = CU_FIELDS if cls == 'CUSTOMIZED_USER' else BC_FIELDS if cls == 'BC_NO_ITEM' else None
    payload, pixel_info = None, None
    if fields:
        cr = {}
        for k in fields:
            if k == 'landing_page_url':
                cr[k] = ch['new']
            elif k == 'utm_params':
                cr[k] = utm_from(ch['new'])
            elif k == 'tracking_pixel_id':
                if a.get('tracking_pixel_id') is None:
                    continue
                pid, pixel_info = exact_pixel(a['tracking_pixel_id'])
                cr[k] = pid
            else:
                cr[k] = a.get(k)
        payload = {"advertiser_id": u['account_id'], "adgroup_id": a['adgroup_id'], "creatives": [cr]}
    unsent = sorted(k for k, v in a.items() if v not in (None, '', [], {}) and (fields is None or k not in fields) and k not in RO)
    return dict(u=u, ch=ch, order=order, rid=rid, a=a, cls=cls, cur=cur, extra=extra, conflict=conflict, dec=dec,
                payload=payload, unsent=unsent, pixel_info=pixel_info)


if __name__ == '__main__':
    ad = sys.argv[1]
    b = build(ad)
    a, ch = b['a'], b['ch']
    print('ad', ad, '| pre-read rid', b['rid'], '| class', b['cls'], '| decision', b['dec'], '| excluded:', excluded(ad, ch['slot']),
          '| recipe:', b['u'].get('recipe'))
    print('CUR:', b['cur'])
    print('cur == now:', b['cur'] == ch['now'], '| cur in alt_now:', b['cur'] in ch['alt_now'], '| cur ~ new:', equiv(b['cur'], ch['new']),
          '| utm extra:', b['extra'], '| utm conflict:', b['conflict'])
    print('url field raw:', a.get('landing_page_url'))
    print('utm_params raw:', [(x['key'], x['value']) for x in a.get('utm_params') or []])
    print('ad_name == plan:', a.get('ad_name') == b['u']['ad_names'][0], '| adv ok:', a.get('advertiser_id') == b['u']['account_id'],
          '| op/sec:', a.get('operation_status'), a.get('secondary_status'), '| modify_time:', a.get('modify_time'))
    print('identity:', a.get('identity_type'), a.get('identity_id'), a.get('identity_authorized_bc_id'), '| item:', a.get('tiktok_item_id'),
          '| fmt:', a.get('ad_format'), '| cta:', a.get('call_to_action'), a.get('call_to_action_id'), '| card:', a.get('card_id'))
    print('ad_text notes:', text_notes(a.get('ad_text')), '| ad_text repr tail:', repr((a.get('ad_text') or '')[-6:]))
    print('pixel read:', a.get('tracking_pixel_id'), '| resolved:', b['pixel_info'])
    print('display_name:', repr(a.get('display_name')), '| unsent non-empty, non-RO fields:', b['unsent'])
    print('all read keys:', sorted(a.keys()))
    if b['payload']:
        json.dump(b['payload'], open(W + 'payload_%s.json' % ad, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('PAYLOAD_ASCII:', json.dumps(b['payload'], ensure_ascii=True, separators=(',', ':')))
