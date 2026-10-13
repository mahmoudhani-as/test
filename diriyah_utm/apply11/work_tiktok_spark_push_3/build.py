# usage: python3 -I build.py <ad_id> [item|video]
# Read-only: take the newest complete single-ad ad/get read of <ad_id> made BEFORE the first update call for it, classify it,
# decide AlreadyFixed / Write / Skipped, and build the spark_push ad/update payload:
#   item  (first choice): every creative field as read, identity kept, SAME tiktok_item_id, no video_id
#   video (fallback, old shape): every creative field as read, the post's video_id, no tiktok_item_id
# landing_page_url = new; utm_params = UTMs of new (no utm_id); pixel as exact string. Saves payload_<ad>_<shape>.json in W.
import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply11/work_tiktok_spark_push_3')
from common import *

FIELDS = ['ad_id', 'ad_name', 'identity_type', 'identity_id', 'identity_authorized_bc_id', 'ad_format', 'tiktok_item_id', 'video_id',
          'image_ids', 'music_id', 'promotional_music_disabled', 'item_duet_status', 'item_stitch_status', 'ad_text', 'call_to_action',
          'call_to_action_id', 'card_id', 'landing_page_url', 'utm_params', 'dark_post_status', 'creative_auto_enhancement_strategy_list',
          'tracking_pixel_id', 'creative_authorized', 'vast_moat_enabled']
RO = {'adgroup_name', 'campaign_name', 'campaign_id', 'adgroup_id', 'advertiser_id', 'secondary_status', 'operation_status',
      'modify_time', 'create_time', 'profile_image_url', 'is_new_structure', 'campaign_automation_type', 'is_aco',
      'optimization_event', 'ad_ref_pixel_id', 'branded_content_disabled', 'app_name', 'display_name', 'landing_page_urls',
      'carousel_image_labels'}
# defaults that are not sent (left as the platform default, equal to the read value)
DEFAULTS = {'deeplink': '', 'deeplink_type': 'NORMAL', 'playable_url': '', 'avatar_icon_web_uri': '', 'viewability_postbid_partner': 'UNSET',
            'brand_safety_postbid_partner': 'UNSET', 'fallback_type': 'UNSET', 'shopping_ads_fallback_type': 'DEFAULT',
            'dynamic_destination': 'UNSET', 'vertical_video_strategy': 'UNSET'}
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


def pre_read(ad):
    live = [i for i, inp, j, txt in updates(ad) if inp.get('dry_run') is False]
    first = min(live) if live else 10 ** 9
    rr = [r for r in (ad_reads().get(ad) or []) if r[0] < first]
    return rr[-1] if rr else None


def pixel_exact(v):
    m = [p for p in PIXELS if float(p) == float(v)]
    assert len(m) == 1, (v, m)
    return m[0]


def build(ad, shape='item'):
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
    cr = {}
    for k in FIELDS:
        if shape == 'item' and k == 'video_id':
            continue
        if shape == 'video' and k == 'tiktok_item_id':
            continue
        if k == 'landing_page_url':
            cr[k] = ch['new']
        elif k == 'utm_params':
            cr[k] = utm_from(ch['new'])
        elif k == 'tracking_pixel_id':
            if a.get(k) in EMPTY:
                continue
            cr[k] = pixel_exact(a[k])
        else:
            if a.get(k) in EMPTY:
                continue
            cr[k] = a.get(k)
    payload = {"advertiser_id": u['account_id'], "adgroup_id": a['adgroup_id'], "creatives": [cr]}
    unsent = sorted(k for k, v in a.items() if v not in EMPTY and k not in cr and k not in RO and DEFAULTS.get(k, object()) != v)
    return dict(u=u, ch=ch, order=order, rid=rid, a=a, cls=cls, cur=cur, extra=extra, conflict=conflict, dec=dec,
                payload=payload, unsent=unsent)


if __name__ == '__main__':
    ad = sys.argv[1]
    shape = sys.argv[2] if len(sys.argv) > 2 else 'item'
    b = build(ad, shape)
    a, ch = b['a'], b['ch']
    print('ad', ad, '| pre-read rid', b['rid'], '| class', b['cls'], '| decision', b['dec'], '| excluded:', excluded(ad, ch['slot']))
    print('CUR:', b['cur'])
    print('cur == now:', b['cur'] == ch['now'], '| cur in alt_now:', b['cur'] in ch['alt_now'], '| cur ~ new:', equiv(b['cur'], ch['new']),
          '| utm extra:', b['extra'], '| utm conflict:', b['conflict'])
    print('ad_name == plan:', a.get('ad_name') == b['u']['ad_names'][0], '| adv ok:', a.get('advertiser_id') == b['u']['account_id'],
          '| op/sec:', a.get('operation_status'), a.get('secondary_status'), '| modify_time:', a.get('modify_time'))
    print('identity:', a.get('identity_type'), a.get('identity_id'), a.get('identity_authorized_bc_id'), '| item:', a.get('tiktok_item_id'),
          '| video:', a.get('video_id'), '| fmt:', a.get('ad_format'), '| cta:', a.get('call_to_action'), a.get('call_to_action_id'),
          '| dark:', a.get('dark_post_status'), '| promo_music_disabled:', a.get('promotional_music_disabled'))
    print('ad_text notes:', text_notes(a.get('ad_text')))
    print('all read keys:', sorted(a.keys()))
    print('unsent non-empty, non-RO, non-default fields:', b['unsent'])
    fn = W + 'payload_%s_%s.json' % (ad, shape)
    json.dump(b['payload'], open(fn, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('PAYLOAD_JSON:', json.dumps(b['payload'], ensure_ascii=False, separators=(',', ':')))
