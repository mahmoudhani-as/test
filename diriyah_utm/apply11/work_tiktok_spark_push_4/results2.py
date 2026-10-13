# Read-only: compact per-change results from this agent's transcript (exact strings). Prints JSON lines (no results file).
import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply11/work_tiktok_spark_push_4')
from common import *
LATE = '20261013211312D515A0701E223CCE8F17'
reads = ad_reads()
out = []
for u in INP:
    ad = u['unit']; ch = u['changes'][0]
    ups = update_calls(ad)
    lives = [x for x in ups if x[2].get('dry_run') is False]
    first = min(x[0] for x in ups); last = max(x[0] for x in lives)
    rr = reads.get(ad) or []
    _, rb, A0 = [r for r in rr if r[0] < first][-1]
    _, ra, A1 = [r for r in rr if r[0] > last][-1]
    cur0 = eff_url(A0.get('landing_page_url'), A0.get('utm_params'))[0]
    cur1 = eff_url(A1.get('landing_page_url'), A1.get('utm_params'))[0]
    assert cur0 == ch['now'] and cur1 == ch['new'] and A1['landing_page_url'] == ch['new']
    att = []
    ok = None
    for (i, tid, inp, j, err, txt) in lives:
        cr = inp['payload']['creatives'][0]
        d = ((j or {}).get('data') or {}).get('data') or {}
        ut = ((((j or {}).get('error') or {}).get('details') or {}).get('upstream_details') or {}).get('tiktok') or {}
        code = d.get('code', ut.get('code')); rid = d.get('request_id', ut.get('request_id')); msg = d.get('message', ut.get('message'))
        shape = 'A' if 'tiktok_item_id' in cr else 'B'
        if code == 0:
            ok = (shape, rid, d['data'].get('need_audit'), 'tracking_pixel_id' in cr)
        else:
            att.append('attempt 1 first-choice shape (BC_AUTH_TT identity + same tiktok_item_id %s, no video_id) rejected: TikTok %s "%s" req %s, nothing changed' % (cr['tiktok_item_id'], code, msg, rid))
    shape, rid, na, px = ok
    if shape == 'A':
        cs = 'first-choice shape: identity_type BC_AUTH_TT, identity_id, identity_authorized_bc_id and the SAME tiktok_item_id %s, no video_id (organic-post ad, it has no video_id)' % A0['tiktok_item_id']
    else:
        cs = 'old shape: the post\'s video_id %s, no tiktok_item_id' % A0['video_id']
        if not att:
            att.append('first-choice shape not re-sent: TikTok rejected it with 40002 "The identity of Spark Ads cannot be updated." on push-style ads 1825844845218882 (req 202610132054404C195402E74B17BD6FFE) and 1859827888563330 (req 2026101321000940EF01CDC4FC34A12DDC), covering both identities these ads use')
    s = 'spark_push. Call shape used: %s. ' % cs
    s += 'Pre-read req %s: URL == now (BC_AUTH_TT, identity %s, BC %s, tiktok_item_id %s, video_id %s). ' % (rb, A0['identity_id'], A0['identity_authorized_bc_id'], A0['tiktok_item_id'], A0.get('video_id'))
    s += '; '.join(att) + ('. ' if att else '')
    s += 'Live /v1.3/ad/update/ with every creative field as read, landing_page_url = new, utm_params = UTMs of new (no utm_id)%s: req %s code 0, need_audit %s. ' % (
        ', pixel as exact string 7347671240183693330' if px else ', no pixel (none as read)', rid, str(na).lower())
    s += 'Read-back req %s: landing_page_url == new byte for byte, utm_params == UTMs of new. ' % ra
    s += 'tiktok_item_id right after the write: %s (%s). ' % (A1['tiktok_item_id'], 'unchanged' if A1['tiktok_item_id'] == A0['tiktok_item_id'] else 'CHANGED from %s' % A0['tiktok_item_id'])
    if A0.get('video_id') != A1.get('video_id'):
        s += 'TikTok swapped video_id to %s on the write (as in earlier old-shape writes); TikTok re-publishing the post 30-60 min after the write is expected (user accepted). ' % A1['video_id']
    if A0.get('ad_text') != A1.get('ad_text'):
        assert A0['ad_text'].rstrip() == A1['ad_text']
        s += 'ad_text trailing space trimmed by gateway (trailing %s). ' % ('U+00A0' if A0['ad_text'].endswith('\xa0') else 'U+0020')
    if ad == '1825843873828865':
        s += 'Immediate read-back showed display_name/app_name "" (were "bujairiterrace"); at 13:13 UTC they were "bujairiterrace" again (transient). '
    if ad == '1857548919933985':
        s += 'tracking_pixel_id was absent in the pre-read (ad group 1857201381031202 is REACH, pixel_id null, adgroup/get req 20261013211158EF5A8179A290B358B348), none sent; it now reads 0 (no pixel). '
    s += 'Status unchanged %s / %s. 13:13 UTC check req %s: URL still new, tiktok_item_id still %s.' % (A1['operation_status'], A1['secondary_status'], LATE, A1['tiktok_item_id'])
    out.append({"platform": "tiktok", "account_id": u['account_id'], "unit_type": u['unit_type'], "unit": ad, "ad_ids": u['ad_ids'],
                "ad_names": u['ad_names'], "slot": ch['slot'], "before": cur0, "after_expected": ch['new'], "after_live": cur1,
                "result": "Fixed", "new_entity_ids": "", "detail": s})
json.dump(out, open(W + 'results_preview2.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for r in out:
    print(json.dumps(r, ensure_ascii=False))
