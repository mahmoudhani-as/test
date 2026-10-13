# usage: python3 -I build.py [ad_id ...]
# Read-only: take the newest complete ad/get read of <ad_id> made BEFORE the first update call for it, classify it,
# decide AlreadyFixed / Write / Skipped, and build the spark_push first-choice ad/update payload:
# every creative field as read (non-empty), video_id NOT sent, SAME tiktok_item_id + BC identity kept,
# landing_page_url = new, utm_params = UTMs of new (no utm_id), pixel as exact string. Saves payload_<ad>.json in W.
import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply11/work_tiktok_spark_push_2')
from common import *

SP_FIELDS = ['ad_id', 'ad_name', 'identity_type', 'identity_id', 'identity_authorized_bc_id', 'ad_format', 'tiktok_item_id',
             'image_ids', 'music_id', 'promotional_music_disabled', 'ad_text', 'call_to_action', 'call_to_action_id', 'card_id',
             'landing_page_url', 'utm_params', 'dark_post_status', 'creative_authorized', 'vast_moat_enabled', 'tracking_pixel_id']
RO = {'adgroup_name', 'campaign_name', 'campaign_id', 'adgroup_id', 'advertiser_id', 'secondary_status', 'operation_status',
      'modify_time', 'create_time', 'profile_image_url', 'is_new_structure', 'campaign_automation_type', 'is_aco',
      'optimization_event', 'ad_ref_pixel_id', 'branded_content_disabled', 'app_name', 'product_info', 'display_name'}
DEFAULTS = {'deeplink_type': 'NORMAL', 'fallback_type': 'UNSET', 'shopping_ads_fallback_type': 'DEFAULT', 'dynamic_destination': 'UNSET',
            'vertical_video_strategy': 'UNSET', 'viewability_postbid_partner': 'UNSET', 'brand_safety_postbid_partner': 'UNSET'}
EMPTY = (None, '', [], {})


def classify(a):
    idt, item = a.get('identity_type'), a.get('tiktok_item_id')
    if idt == 'BC_AUTH_TT' and item:
        return 'SPARK_PUSH'
    if idt == 'AUTH_CODE':
        return 'SPARK_PULL'
    if idt == 'BC_AUTH_TT':
        return 'BC_NO_ITEM'
    if idt == 'CUSTOMIZED_USER':
        return 'CUSTOMIZED_USER'
    return 'OTHER:' + str(idt)


def first_update_order(ad):
    ups = [x[0] for x in calls('tiktok_ad_update') if ((x[2].get('payload') or {}).get('creatives') or [{}])[0].get('ad_id') == ad]
    return min(ups) if ups else 10 ** 9


def pre_read(ad):
    first = first_update_order(ad)
    rr = [r for r in (ad_reads().get(ad) or []) if r[0] < first]
    return rr[-1] if rr else None


def build(ad):
    u = INPD[ad]
    assert len(u['changes']) == 1
    ch = u['changes'][0]
    assert ch['slot'] == 'ad.landing_page_url', ch['slot']
    r = pre_read(ad)
    assert r, 'no complete pre-read'
    order, rid, a, ts = r
    cls = classify(a)
    cur, extra, conflict = eff_url(a.get('landing_page_url'), a.get('utm_params'))
    if equiv(cur, ch['new']):
        dec = 'AlreadyFixed'
    elif cur == ch['now'] or cur in ch['alt_now']:
        dec = 'Write'
    else:
        dec = 'Skipped'
    payload = None
    if cls == 'SPARK_PUSH':
        cr = {}
        for k in SP_FIELDS:
            if k == 'landing_page_url':
                cr[k] = ch['new']
            elif k == 'utm_params':
                cr[k] = utm_from(ch['new'])
            elif k == 'tracking_pixel_id':
                pv = a.get('tracking_pixel_id')
                if pv in (None, 0, '0', ''):
                    continue
                if float(pv) == float(int(PIXEL)):
                    assert float(pv) != float(int(OTHER_PIXEL))
                    cr[k] = PIXEL
                else:
                    raise AssertionError('unknown pixel %r' % pv)
            elif k in a and a[k] not in EMPTY:
                cr[k] = a[k]
        assert 'video_id' not in cr and cr['tiktok_item_id'] == a['tiktok_item_id']
        payload = {"advertiser_id": u['account_id'], "adgroup_id": a['adgroup_id'], "creatives": [cr]}
    unsent = sorted(k for k, v in a.items() if v not in EMPTY and k not in SP_FIELDS and k not in RO and DEFAULTS.get(k) != v)
    return dict(u=u, ch=ch, order=order, rid=rid, a=a, ts=ts, cls=cls, cur=cur, extra=extra, conflict=conflict, dec=dec,
                payload=payload, unsent=unsent)


if __name__ == '__main__':
    ads = sys.argv[1:] or [u['unit'] for u in INP]
    for ad in ads:
        b = build(ad)
        a, ch = b['a'], b['ch']
        print('==== ad', ad, '| pre-read rid', b['rid'], '| class', b['cls'], '| decision', b['dec'], '| excluded:', excluded(ad, ch['slot']), '| recipe:', b['u'].get('recipe'))
        print('CUR:', b['cur'])
        print('cur == now:', b['cur'] == ch['now'], '| cur in alt_now:', b['cur'] in ch['alt_now'], '| cur ~ new:', equiv(b['cur'], ch['new']),
              '| utm extra:', b['extra'], '| utm conflict:', b['conflict'])
        print('ad_name == plan:', a.get('ad_name') == b['u']['ad_names'][0], '| adv ok:', a.get('advertiser_id') == b['u']['account_id'],
              '| op/sec:', a.get('operation_status'), a.get('secondary_status'), '| modify_time:', a.get('modify_time'))
        print('identity:', a.get('identity_type'), a.get('identity_id'), a.get('identity_authorized_bc_id'), '| item:', a.get('tiktok_item_id'),
              '| video:', a.get('video_id'), '| fmt:', a.get('ad_format'), '| cta:', a.get('call_to_action'), a.get('call_to_action_id'),
              '| dark:', a.get('dark_post_status'), '| pixel:', a.get('tracking_pixel_id'))
        print('ad_text notes:', text_notes(a.get('ad_text')), '| unsent non-empty non-RO non-default fields:', b['unsent'])
        if b['payload']:
            json.dump(b['payload'], open(W + 'payload_%s.json' % ad, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
