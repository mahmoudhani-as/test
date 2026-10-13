# usage: python3 -I build_old.py <ad_id> [...]
# Read-only: spark_push fallback ("old shape", after TikTok rejected the first-choice shape with 40002):
# every creative field as read (non-empty) incl. the post's video_id, WITHOUT tiktok_item_id; BC identity kept;
# landing_page_url = new, utm_params = UTMs of new (no utm_id), pixel as exact string.
# Uses the newest complete ad/get read made BEFORE the first old-shape update call for the ad (or the newest read if none yet).
# Saves payload_old_<ad>.json in W and prints the ASCII-escaped payload.
import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply11/work_tiktok_spark_push_2')
from common import *
from build import classify, EMPTY, RO, DEFAULTS

OLD_FIELDS = ['ad_id', 'ad_name', 'identity_type', 'identity_id', 'identity_authorized_bc_id', 'ad_format', 'video_id',
              'image_ids', 'music_id', 'promotional_music_disabled', 'ad_text', 'call_to_action', 'call_to_action_id', 'card_id',
              'landing_page_url', 'utm_params', 'dark_post_status', 'creative_authorized', 'vast_moat_enabled', 'tracking_pixel_id']


def first_old_order(ad):
    ups = [x[0] for x in calls('tiktok_ad_update')
           if ((x[2].get('payload') or {}).get('creatives') or [{}])[0].get('ad_id') == ad
           and 'video_id' in ((x[2].get('payload') or {}).get('creatives') or [{}])[0]]
    return min(ups) if ups else 10 ** 9


def build_old(ad):
    u = INPD[ad]
    ch = u['changes'][0]
    first = first_old_order(ad)
    rr = [r for r in (ad_reads().get(ad) or []) if r[0] < first]
    assert rr, 'no complete read'
    order, rid, a, ts = rr[-1]
    assert classify(a) == 'SPARK_PUSH', classify(a)
    cur, extra, conflict = eff_url(a.get('landing_page_url'), a.get('utm_params'))
    if equiv(cur, ch['new']):
        dec = 'AlreadyFixed'
    elif cur == ch['now'] or cur in ch['alt_now']:
        dec = 'Write'
    else:
        dec = 'Skipped'
    cr = {}
    for k in OLD_FIELDS:
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
    assert 'tiktok_item_id' not in cr and cr.get('video_id') == a['video_id'] and a['video_id']
    payload = {"advertiser_id": u['account_id'], "adgroup_id": a['adgroup_id'], "creatives": [cr]}
    unsent = sorted(k for k, v in a.items() if v not in EMPTY and k not in OLD_FIELDS and k not in RO and DEFAULTS.get(k) != v)
    return dict(u=u, ch=ch, rid=rid, a=a, cur=cur, dec=dec, payload=payload, unsent=unsent)


if __name__ == '__main__':
    for ad in sys.argv[1:]:
        b = build_old(ad)
        a = b['a']
        print('==== ad', ad, '| read rid', b['rid'], '| decision', b['dec'], '| item', a.get('tiktok_item_id'), '| video', a.get('video_id'),
              '| modify_time', a.get('modify_time'), '| unsent:', b['unsent'], '| excluded:', excluded(ad, b['ch']['slot']))
        print('CUR:', b['cur'])
        json.dump(b['payload'], open(W + 'payload_old_%s.json' % ad, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('ASCII:', json.dumps(b['payload'], ensure_ascii=True, separators=(',', ':')))
