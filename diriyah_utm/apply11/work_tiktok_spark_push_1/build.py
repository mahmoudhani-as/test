# usage: python3 -I build.py <ad_id> [item|video]
# Read-only: take the newest complete ad/get read of <ad_id> made BEFORE the first update call for it, classify it,
# decide AlreadyFixed / Write / Skipped, and build the spark_push ad/update payload:
#   item  (first choice): every creative field as read, SAME tiktok_item_id, no video_id
#   video (old shape, only if TikTok rejected the item shape): the post's video_id, no tiktok_item_id
# landing_page_url = new, utm_params = UTMs of new (no utm_id); pixel as exact string. Saves payload_<ad>_<shape>.json in W.
import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply11/work_tiktok_spark_push_1')
from common import *

# proven BC_AUTH_TT full-update field list (old Spark Push payloads of 11/12-Oct + carousels), shape-specific post field
BASE = ['ad_id', 'ad_name', 'identity_type', 'identity_id', 'identity_authorized_bc_id', 'ad_format', 'POST', 'image_ids',
        'music_id', 'ad_text', 'call_to_action', 'call_to_action_id', 'card_id', 'landing_page_url', 'utm_params',
        'tracking_pixel_id', 'dark_post_status', 'promotional_music_disabled', 'item_duet_status', 'item_stitch_status',
        'creative_authorized', 'vast_moat_enabled']
OPTIONAL = {'music_id', 'call_to_action', 'call_to_action_id', 'card_id', 'promotional_music_disabled', 'item_duet_status',
            'item_stitch_status'}   # sent only when the read has a non-empty value
RO = {'adgroup_name', 'campaign_name', 'campaign_id', 'adgroup_id', 'advertiser_id', 'secondary_status', 'operation_status',
      'modify_time', 'create_time', 'profile_image_url', 'is_new_structure', 'campaign_automation_type', 'is_aco',
      'deeplink_type', 'viewability_postbid_partner', 'brand_safety_postbid_partner', 'optimization_event', 'ad_ref_pixel_id',
      'fallback_type', 'branded_content_disabled', 'app_name', 'product_info', 'display_name', 'creative_auto_enhancement_strategy_list',
      'shopping_ads_fallback_type', 'dynamic_destination', 'vertical_video_strategy', 'video_id', 'tiktok_item_id', 'tracking_pixel_id'}
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


def is_update_for(inp, ad):
    return ((inp.get('payload') or {}).get('creatives') or [{}])[0].get('ad_id') == ad


def pre_read(ad):
    ups = [i for i, tid, inp, txt, err in calls('tiktok_ad_update') if is_update_for(inp, ad)]
    first = min(ups) if ups else 10 ** 9
    rr = [r for r in (ad_reads().get(ad) or []) if r[0] < first]
    return rr[-1] if rr else None


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
    payload = None
    if cls == 'SPARK_PUSH':
        cr = {}
        for k in BASE:
            if k == 'POST':
                if shape == 'item':
                    cr['tiktok_item_id'] = a['tiktok_item_id']
                else:
                    cr['video_id'] = a['video_id']
                continue
            if k == 'landing_page_url':
                cr[k] = ch['new']
            elif k == 'utm_params':
                cr[k] = utm_from(ch['new'])
            elif k == 'tracking_pixel_id':
                pv = a.get('tracking_pixel_id')
                if pv in (None, 0, '0', ''):
                    continue
                assert float(PIXEL) == float(pv), (PIXEL, pv)
                assert float(OTHER_PIXEL) != float(pv)
                cr[k] = PIXEL
            elif k in OPTIONAL:
                if a.get(k) not in EMPTY:
                    cr[k] = a[k]
            else:
                assert k in a, 'missing ' + k
                cr[k] = a.get(k)
        payload = {"advertiser_id": u['account_id'], "adgroup_id": a['adgroup_id'], "creatives": [cr]}
    sent = set(((payload or {}).get('creatives') or [{}])[0])
    unsent = sorted(k for k, v in a.items() if v not in EMPTY and v is not False and k not in sent and k not in RO)
    return dict(u=u, ch=ch, order=order, rid=rid, a=a, cls=cls, cur=cur, extra=extra, conflict=conflict, dec=dec,
                payload=payload, unsent=unsent, shape=shape)


if __name__ == '__main__':
    ad = sys.argv[1]
    shape = sys.argv[2] if len(sys.argv) > 2 else 'item'
    b = build(ad, shape)
    a, ch = b['a'], b['ch']
    print('ad', ad, '| pre-read rid', b['rid'], '| class', b['cls'], '| decision', b['dec'], '| excluded:', excluded(ad, ch['slot']),
          '| shape', shape)
    print('CUR:', b['cur'])
    print('cur == now:', b['cur'] == ch['now'], '| cur in alt_now:', b['cur'] in ch['alt_now'], '| cur ~ new:', equiv(b['cur'], ch['new']),
          '| utm extra:', b['extra'], '| utm conflict:', b['conflict'])
    print('ad_name == plan:', a.get('ad_name') == b['u']['ad_names'][0], '| adv ok:', a.get('advertiser_id') == b['u']['account_id'],
          '| op/sec:', a.get('operation_status'), a.get('secondary_status'), '| modify_time:', a.get('modify_time'))
    print('identity:', a.get('identity_type'), a.get('identity_id'), a.get('identity_authorized_bc_id'), '| item:', a.get('tiktok_item_id'),
          '| video:', a.get('video_id'), '| fmt:', a.get('ad_format'), '| cta:', a.get('call_to_action'), a.get('call_to_action_id'),
          '| card:', a.get('card_id'), '| pixel:', a.get('tracking_pixel_id'), '| dark:', a.get('dark_post_status'))
    print('ad_text notes:', text_notes(a.get('ad_text')), '| ad_text repr tail:', repr((a.get('ad_text') or '')[-6:]))
    print('unsent non-empty, non-RO fields:', b['unsent'])
    if b['payload']:
        json.dump(b['payload'], open(W + 'payload_%s_%s.json' % (ad, shape), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('PAYLOAD_ASCII:', json.dumps(b['payload'], ensure_ascii=True, separators=(',', ':')))
