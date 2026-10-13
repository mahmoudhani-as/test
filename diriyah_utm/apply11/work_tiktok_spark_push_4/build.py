# usage: python3 -I build.py <ad_id> <A|B>
#   A = spark_push first choice: BC_AUTH_TT identity + SAME tiktok_item_id, no video_id, every other creative field as read
#   B = old shape (fallback): the post's video_id, no tiktok_item_id
# Read-only: newest complete ad/get read of <ad_id> made BEFORE the first update call for it; classify; decide; build payload.
import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply11/work_tiktok_spark_push_4')
from common import *

BASE = ['ad_id', 'ad_name', 'identity_type', 'identity_id', 'identity_authorized_bc_id', 'ad_format']
REST = ['image_ids', 'music_id', 'ad_text', 'call_to_action', 'call_to_action_id', 'card_id', 'landing_page_url', 'utm_params',
        'dark_post_status', 'creative_authorized', 'vast_moat_enabled', 'tracking_pixel_id', 'creative_auto_enhancement_strategy_list',
        'promotional_music_disabled', 'item_duet_status', 'item_stitch_status', 'deeplink', 'page_id']
RO = {'adgroup_name', 'campaign_name', 'campaign_id', 'adgroup_id', 'advertiser_id', 'secondary_status', 'operation_status',
      'modify_time', 'create_time', 'profile_image_url', 'is_new_structure', 'campaign_automation_type', 'is_aco',
      'deeplink_type', 'viewability_postbid_partner', 'brand_safety_postbid_partner', 'optimization_event',
      'branded_content_disabled', 'app_name', 'display_name', 'avatar_icon_web_uri', 'playable_url', 'video_id', 'tiktok_item_id'}


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


def pre_read(ad, latest=False):
    """newest complete read before the first update call (latest=False), or newest complete read before the next call (latest=True)"""
    ups = [x[0] for x in update_calls(ad)]
    first = min(ups) if (ups and not latest) else 10 ** 9
    rr = [r for r in (ad_reads().get(ad) or []) if r[0] < first]
    if latest and ups:
        rr = [r for r in rr if r[0] > max(ups)]
    return rr[-1] if rr else None


def empty(v):
    return v is None or v == '' or v == [] or v == {}


def build(ad, shape, latest=False):
    u = INPD[ad]
    assert len(u['changes']) == 1
    ch = u['changes'][0]
    assert ch['slot'] == 'ad.landing_page_url', ch['slot']
    r = pre_read(ad, latest)
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
            cr[k] = a.get(k)
        if shape == 'A':
            cr['tiktok_item_id'] = str(a['tiktok_item_id'])
        else:
            assert a.get('video_id'), 'no video_id for old shape'
            cr['video_id'] = a['video_id']
        for k in REST:
            if k == 'landing_page_url':
                cr[k] = ch['new']
            elif k == 'utm_params':
                cr[k] = utm_from(ch['new'])
            elif k == 'tracking_pixel_id':
                if a.get('tracking_pixel_id') in (None, 0, '0', ''):
                    continue  # no pixel as read (0 = none)
                m = [p for p in PIXELS if float(p) == float(a['tracking_pixel_id'])]
                assert len(m) == 1, (m, a['tracking_pixel_id'])
                cr[k] = m[0]
            elif k == 'call_to_action' and not empty(a.get('call_to_action_id')):
                continue  # call_to_action_id wins; send it instead (as read)
            else:
                if empty(a.get(k)) and k not in ('creative_authorized', 'vast_moat_enabled'):
                    continue
                if k in a:
                    cr[k] = a.get(k)
        payload = {"advertiser_id": u['account_id'], "adgroup_id": a['adgroup_id'], "creatives": [cr]}
    sent = set(payload['creatives'][0].keys()) if payload else set()
    unsent = sorted(k for k, v in a.items() if not empty(v) and k not in sent and k not in RO)
    return dict(u=u, ch=ch, order=order, rid=rid, a=a, cls=cls, cur=cur, extra=extra, conflict=conflict, dec=dec,
                payload=payload, unsent=unsent)


if __name__ == '__main__':
    ad, shape = sys.argv[1], sys.argv[2]
    b = build(ad, shape, len(sys.argv) > 3 and sys.argv[3] == 'latest')
    a, ch = b['a'], b['ch']
    print('ad', ad, '| pre-read rid', b['rid'], '| class', b['cls'], '| decision', b['dec'], '| excluded:', excluded(ad, ch['slot']))
    print('CUR:', b['cur'])
    print('cur == now:', b['cur'] == ch['now'], '| cur in alt_now:', b['cur'] in ch['alt_now'], '| cur ~ new:', equiv(b['cur'], ch['new']),
          '| utm extra:', b['extra'], '| utm conflict:', b['conflict'])
    print('ad_name == plan:', a.get('ad_name') == b['u']['ad_names'][0], '| adv ok:', a.get('advertiser_id') == b['u']['account_id'],
          '| op/sec:', a.get('operation_status'), a.get('secondary_status'), '| modify_time:', a.get('modify_time'))
    print('identity:', a.get('identity_type'), a.get('identity_id'), a.get('identity_authorized_bc_id'), '| item:', a.get('tiktok_item_id'),
          '| video:', a.get('video_id'), '| fmt:', a.get('ad_format'), '| cta:', a.get('call_to_action'), a.get('call_to_action_id'),
          '| card:', a.get('card_id'), '| image_ids:', a.get('image_ids'))
    print('ad_text notes:', text_notes(a.get('ad_text')), '| ad_text repr tail:', repr((a.get('ad_text') or '')[-6:]))
    print('display/app:', repr(a.get('display_name')), repr(a.get('app_name')), '| unsent non-empty, non-RO fields:', b['unsent'])
    if b['payload']:
        json.dump(b['payload'], open(W + 'payload_%s_%s.json' % (ad, shape), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('PAYLOAD_ASCII:', json.dumps(b['payload'], ensure_ascii=True, separators=(',', ':')))
