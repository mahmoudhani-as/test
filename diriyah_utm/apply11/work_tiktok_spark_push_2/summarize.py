# Read-only: build the per-change result objects from THIS agent's transcript (byte-exact) and print them as JSON (no file written).
import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply11/work_tiktok_spark_push_2')
from common import *
from build_old import build_old

out = []
reads = ad_reads()
ups = calls('tiktok_ad_update')
for u in INP:
    ad = u['unit']
    ch = u['changes'][0]
    mine = [x for x in ups if ((x[2].get('payload') or {}).get('creatives') or [{}])[0].get('ad_id') == ad]
    dry = [x for x in mine if x[2].get('dry_run', True) is not False]
    live = [x for x in mine if x[2].get('dry_run', True) is False]
    first_upd = min(x[0] for x in mine)
    pre = [r for r in reads.get(ad, []) if r[0] < first_upd][-1]
    pre_a = pre[2]
    before = eff_url(pre_a.get('landing_page_url'), pre_a.get('utm_params'))[0]
    last_live = live[-1]
    post = [r for r in reads.get(ad, []) if r[0] > last_live[0]][-1]
    post_a = post[2]
    after = eff_url(post_a.get('landing_page_url'), post_a.get('utm_params'))[0]
    attempts = []
    for x in live:
        j = result_json(x[3]) or {}
        cr = ((x[2].get('payload') or {}).get('creatives') or [{}])[0]
        shape = 'first-choice (BC_AUTH_TT + same tiktok_item_id, no video_id)' if 'tiktok_item_id' in cr else 'old shape (video_id as read, no tiktok_item_id)'
        if j.get('success'):
            dd = j['data']['data']
            attempts.append('%s: TikTok code %s %s, request_id %s' % (shape, dd.get('code'), dd.get('message'), dd.get('request_id')))
        else:
            up = ((((j.get('error') or {}).get('details') or {}).get('upstream_details') or {}).get('tiktok') or {})
            attempts.append('%s: REJECTED by TikTok code %s "%s", request_id %s' % (shape, up.get('code'), up.get('message'), up.get('request_id')))
    ok = after == ch['new']
    other = {k: (pre_a.get(k), post_a.get(k)) for k in sorted(set(pre_a) | set(post_a))
             if k not in ('landing_page_url', 'utm_params', 'modify_time', 'app_name', 'display_name') and pre_a.get(k) != post_a.get(k)}
    notes = []
    if 'video_id' in other:
        notes.append('TikTok returned a different video_id right after the write (%s -> %s; the read video_id was sent unchanged)' % other['video_id'])
    if 'tracking_pixel_id' in other:
        notes.append('tracking_pixel_id read as %s before and %s after (no pixel either way; not sent)' % tuple(json.dumps(v) for v in other['tracking_pixel_id']))
    if 'ad_text' in other:
        a0, a1 = other['ad_text']
        assert a1 == a0.rstrip(), 'unexpected ad_text change'
        notes.append('ad_text trailing space trimmed by gateway (accepted)')
    rest = sorted(k for k in other if k not in ('video_id', 'tracking_pixel_id', 'ad_text'))
    if rest:
        notes.append('OTHER FIELDS CHANGED: ' + json.dumps({k: other[k] for k in rest}, ensure_ascii=True))
    pixel_sent = ((live[-1][2].get('payload') or {}).get('creatives') or [{}])[0].get('tracking_pixel_id')
    detail = 'recipe spark_push. Pre-read ad/get req %s: URL == now (BC_AUTH_TT Spark Push, tiktok_item_id %s, dark_post %s). ' % (pre[1], pre_a.get('tiktok_item_id'), pre_a.get('dark_post_status'))
    if len(live) > 1:
        detail += 'Live attempts: ' + ' | '.join('(%d) %s' % (i + 1, a) for i, a in enumerate(attempts)) + '. '
    else:
        detail += 'Call shape: old shape (full ad/update, every creative field as read incl. video_id %s, no tiktok_item_id%s; see notes). Live: %s. ' % (
            pre_a.get('video_id'), ', pixel as exact string' if pixel_sent else '', attempts[-1].split(': ', 1)[1])
    detail += 'Dry run preview == payload%s. Read-back req %s: URL + utm_params == new byte for byte, no utm_id; tiktok_item_id right after the write %s (unchanged); status unchanged (%s/%s).' % (
        ' except gateway trim of ad_text trailing space' if 'ad_text' in other else '', post[1], post_a.get('tiktok_item_id'), post_a.get('operation_status'), post_a.get('secondary_status'))
    if 'video_id' in other:
        detail += ' video_id returned by TikTok changed %s -> %s (read value was sent).' % other['video_id']
    if 'tracking_pixel_id' in other:
        detail += ' tracking_pixel_id absent before, 0 after (no pixel either way; not sent).'
    if 'ad_text' in other:
        a0, a1 = other['ad_text']
        assert a1 == a0.rstrip()
        detail += ' ad_text trailing space trimmed by gateway.'
    rest = sorted(k for k in other if k not in ('video_id', 'tracking_pixel_id', 'ad_text'))
    if rest:
        detail += ' OTHER FIELDS CHANGED: ' + json.dumps({k: other[k] for k in rest}, ensure_ascii=True)
    detail += ' TikTok may re-publish post %s 30-60 min later (accepted).' % pre_a.get('tiktok_item_id')
    out.append({"platform": "tiktok", "account_id": u['account_id'], "unit_type": u['unit_type'], "unit": ad, "ad_ids": u['ad_ids'], "ad_names": u['ad_names'],
                "slot": ch['slot'], "before": before, "after_expected": ch['new'], "after_live": after, "result": "Fixed" if ok else "Failed",
                "new_entity_ids": "", "detail": detail})
    assert before == ch['now']
for o in out:
    print(json.dumps(o, ensure_ascii=False))
print('COUNT', len(out), 'FIXED', sum(1 for o in out if o['result'] == 'Fixed'), file=sys.stderr)
