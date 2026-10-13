# Read-only: compile one result per change from this agent's transcript (exact strings). Prints JSON (no results file).
import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply11/work_tiktok_spark_push_4')
from common import *
A_REJ = {'1825844845218882': '202610132054404C195402E74B17BD6FFE', '1859827888563330': '2026101321000940EF01CDC4FC34A12DDC'}
LATE = '20261013211312D515A0701E223CCE8F17'
reads = ad_reads()
out = []
for u in INP:
    ad = u['unit']; ch = u['changes'][0]
    ups = update_calls(ad)
    lives = [x for x in ups if x[2].get('dry_run') is False]
    first = min(x[0] for x in ups)
    last = max(x[0] for x in lives)
    rr = reads.get(ad) or []
    pre = [r for r in rr if r[0] < first][-1]
    aft = [r for r in rr if r[0] > last][-1]
    _, rb, A0 = pre
    _, ra, A1 = aft
    cur0 = eff_url(A0.get('landing_page_url'), A0.get('utm_params'))[0]
    cur1 = eff_url(A1.get('landing_page_url'), A1.get('utm_params'))[0]
    assert cur0 == ch['now'] or cur0 in ch['alt_now']
    parts_ = []
    shape_used = None
    for (i, tid, inp, j, err, txt) in lives:
        cr = ((inp.get('payload') or {}).get('creatives') or [{}])[0]
        d = ((j or {}).get('data') or {}).get('data') or {}
        ut = ((((j or {}).get('error') or {}).get('details') or {}).get('upstream_details') or {}).get('tiktok') or {}
        code = d.get('code', ut.get('code')); rid = d.get('request_id', ut.get('request_id')); msg = d.get('message', ut.get('message'))
        if 'tiktok_item_id' in cr:
            sh = 'first-choice shape (identity_type BC_AUTH_TT, identity_id, identity_authorized_bc_id and the SAME tiktok_item_id %s, no video_id)' % cr['tiktok_item_id']
        else:
            sh = 'old shape (the post\'s video_id %s, no tiktok_item_id)' % cr['video_id']
        if code == 0:
            shape_used = sh
            parts_.append('live write /v1.3/ad/update/ (tiktok_ad_update) %s, every other creative field as read, landing_page_url = new, utm_params = UTMs of new (no utm_id)%s: req %s code 0 OK, need_audit %s' % (
                sh, ', pixel sent as exact string 7347671240183693330' if 'tracking_pixel_id' in cr else ', no pixel (none as read)', rid,
                str(d.get('data', {}).get('need_audit')).lower()))
        else:
            parts_.append('attempt with %s rejected by TikTok: code %s "%s" req %s (nothing changed)' % (sh, code, msg, rid))
    notes = []
    if A1.get('tiktok_item_id') == A0.get('tiktok_item_id'):
        notes.append('tiktok_item_id right after the write: %s (unchanged)' % A1.get('tiktok_item_id'))
    else:
        notes.append('tiktok_item_id right after the write: %s (was %s)' % (A1.get('tiktok_item_id'), A0.get('tiktok_item_id')))
    if A0.get('video_id') != A1.get('video_id'):
        notes.append('TikTok replaced video_id %s -> %s on the write (same as earlier old-shape writes); TikTok is expected to re-publish the post 30-60 min later and re-point the ad (user accepted)' % (A0.get('video_id'), A1.get('video_id')))
    if A0.get('ad_text') != A1.get('ad_text'):
        if (A0.get('ad_text') or '').rstrip() == A1.get('ad_text'):
            notes.append('ad_text trailing space trimmed by gateway (trailing %s removed)' % ('U+00A0' if A0['ad_text'].endswith('\xa0') else 'U+0020'))
        else:
            notes.append('ad_text changed!')
    other = []
    for k in sorted(set(A0) | set(A1)):
        if k in ('modify_time', 'landing_page_url', 'utm_params', 'secondary_status', 'video_id', 'ad_text'):
            continue
        if A0.get(k) != A1.get(k):
            other.append('%s %r -> %r' % (k, A0.get(k), A1.get(k)))
    if other:
        notes.append('other fields on the immediate read-back: ' + '; '.join(other))
    notes.append('status unchanged %s / %s' % (A1.get('operation_status'), A1.get('secondary_status')))
    pre_desc = 'pre-read ad/get req %s: URL == %s (BC_AUTH_TT Spark Push ad, identity %s, BC %s, tiktok_item_id %s, video_id %s, %s, cta %s)' % (
        rb, 'now' if cur0 == ch['now'] else 'alt_now', A0.get('identity_id'), A0.get('identity_authorized_bc_id'), A0.get('tiktok_item_id'),
        A0.get('video_id'), A0.get('ad_format'), A0.get('call_to_action_id') or A0.get('call_to_action'))
    if ad not in A_REJ and ad != '1825843873828865':
        parts_.insert(0, 'first-choice shape not re-sent: TikTok rejected it with 40002 "The identity of Spark Ads cannot be updated." on push-style ads 1825844845218882 (req 202610132054404C195402E74B17BD6FFE) and 1859827888563330 (req 2026101321000940EF01CDC4FC34A12DDC), i.e. on both identities these ads use; old shape used per recipe')
    rb_desc = 'read-back req %s: landing_page_url == new byte for byte, utm_params == UTMs of new (no utm_id)' % ra
    detail = 'spark_push recipe. Call shape used: %s. %s. %s. %s. %s. Check at 13:13 UTC (req %s): URL still new, tiktok_item_id still %s.' % (
        shape_used, pre_desc, '; '.join(parts_), rb_desc, '; '.join(notes), LATE, A1.get('tiktok_item_id'))
    if ad == '1825843873828865':
        detail = detail.replace('other fields on the immediate read-back: ', 'transient: immediate read-back showed ') + ' At 13:13 UTC display_name/app_name were "bujairiterrace" again (blank was transient). Same post kept (no video_id was sent, none existed: organic post ad).'
    if ad == '1857548919933985':
        detail += ' tracking_pixel_id was absent from the pre-read (ad group 1857201381031202 is REACH with pixel_id null, adgroup/get req 20261013211158EF5A8179A290B358B348), so no pixel was sent; it now reads 0 (= no pixel).'
    assert cur1 == ch['new'] and A1.get('landing_page_url') == ch['new']
    out.append({"platform": "tiktok", "account_id": u['account_id'], "unit_type": u['unit_type'], "unit": ad, "ad_ids": u['ad_ids'],
                "ad_names": u['ad_names'], "slot": ch['slot'], "before": cur0, "after_expected": ch['new'], "after_live": cur1,
                "result": "Fixed", "new_entity_ids": "", "detail": detail})
json.dump(out, open(W + 'results_preview.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(out))
for r in out:
    print(r['unit'], r['result'], r['before'] == INPD[r['unit']]['changes'][0]['now'], r['after_live'] == r['after_expected'])
print(json.dumps(out[0], ensure_ascii=False, indent=1))
print(json.dumps(out[1], ensure_ascii=False, indent=1))
print(json.dumps(out[3], ensure_ascii=False, indent=1))
