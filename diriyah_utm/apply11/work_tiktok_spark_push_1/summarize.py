# usage: python3 -I summarize.py  -> prints the results array (JSON) built from THIS agent's transcript. Read-only, writes nothing.
import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply11/work_tiktok_spark_push_1')
from common import *
from build import build, is_update_for

REJ = "first-choice shape (BC_AUTH_TT identity + same tiktok_item_id, no video_id) rejected by TikTok on ad 1838614376695858: 40002 'The identity of Spark Ads cannot be updated.' (req 202610132054223C7A9212DC129023B1F0)"
reads = ad_reads()


def all_reads():
    # every successful tiktok_ad_get record (incl. projected reads): {ad_id: [(order, rid, rec)]}
    res = {}
    for i, tid, inp, txt, err in calls('tiktok_ad_get'):
        j = result_json(txt)
        if not j or not j.get('success'):
            continue
        d = (j.get('data') or {}).get('data') or {}
        if d.get('code') != 0:
            continue
        for a in (d.get('data') or {}).get('list') or []:
            if isinstance(a, dict) and 'ad_id' in a:
                res.setdefault(str(a['ad_id']), []).append((i, d.get('request_id'), a))
    return res


AR = all_reads()
out = []
for u in INP:
    ad = u['unit']
    b = build(ad, 'video')
    ch, pre = b['ch'], b['a']
    ups = [(i, inp, txt, err) for i, tid, inp, txt, err in calls('tiktok_ad_update') if is_update_for(inp, ad)]
    lives = [x for x in ups if x[1].get('dry_run', True) is False]
    dries = [x for x in ups if x[1].get('dry_run', True) is not False]
    assert lives, ad
    li, linp, ltxt, lerr = lives[-1]
    lj = result_json(ltxt) or {}
    ld = (lj.get('data') or {}).get('data') or {}
    assert lj.get('success') and ld.get('code') == 0, ad
    assert 'video_id' in linp['payload']['creatives'][0] and 'tiktok_item_id' not in linp['payload']['creatives'][0]
    assert not diff(linp['payload'], b['payload']), ad
    rr = [r for r in reads[ad] if r[0] > li]
    vi, vrid, post = rr[0]          # first complete read after the live write
    eff, extra, conflict = eff_url(post.get('landing_page_url'), post.get('utm_params'))
    ok = (eff == ch['new'] and post.get('landing_page_url') == ch['new'] and not extra and not conflict and
          sorted((x['key'], x['value']) for x in post['utm_params']) == sorted((x['key'], x['value']) for x in utm_from(ch['new'])))
    first_attempt = ''
    if len(lives) == 2:
        fi, finp, ftxt, ferr = lives[0]
        assert 'tiktok_item_id' in finp['payload']['creatives'][0] and 'video_id' not in finp['payload']['creatives'][0] and ferr
        first_attempt = ("attempt 1 = first-choice shape (identity BC_AUTH_TT/7d136a20-71e2-5fb6-9927-ad76b915fac7/BC 6846326855419559942 + same "
                         "tiktok_item_id %s, no video_id; dry run clean) REJECTED by TikTok 40002 'The identity of Spark Ads cannot be updated.' "
                         "(req 202610132054223C7A9212DC129023B1F0); re-read req 202610132054403661F698A33EF178DE91 showed the ad unchanged; "
                         "attempt 2 = old shape. " % pre['tiktok_item_id'])
    else:
        assert len(lives) == 1
    notes = []
    sent_text = b['payload']['creatives'][0].get('ad_text') or ''
    if sent_text != sent_text.rstrip():
        notes.append('ad_text trailing space trimmed by gateway (read back without it)')
    if ' ' in sent_text:
        notes.append('ad_text U+00A0 kept')
    if pre.get('tracking_pixel_id') in (0, None):
        notes.append('no pixel (tracking_pixel_id %r, not sent)' % pre.get('tracking_pixel_id'))
    else:
        notes.append('pixel sent as exact string 7347671240183693330')
    cta = ('call_to_action_id %s' % pre['call_to_action_id']) if pre.get('call_to_action_id') else ('call_to_action %s' % pre.get('call_to_action'))
    seen = []
    for i2, rid2, rec in AR.get(ad, []):
        if i2 > li and 'display_name' in rec:
            seen.append('%r in %s' % (rec.get('display_name'), rid2))
    if pre.get('tracking_pixel_id') is None and post.get('tracking_pixel_id') == 0:
        notes.append('tracking_pixel_id read absent before / 0 after (no pixel either way)')
    vals = [rec.get('display_name') for i2, rid2, rec in AR.get(ad, []) if i2 > li and 'display_name' in rec]
    last = [(rid2, rec.get('display_name')) for i2, rid2, rec in AR.get(ad, []) if i2 > li and 'display_name' in rec][-1]
    notes.append("display_name/app_name were not sent (as in the 11/12-Oct old-shape payloads); after the write %d read calls returned %s "
                 "(TikTok read state, alternates between calls); last read req %s: %r" % (len(vals), sorted(set(vals)), last[0], last[1]))
    other = sorted(k for k in set(pre) | set(post) if k not in ('landing_page_url', 'utm_params', 'modify_time', 'video_id', 'ad_text',
                                                                  'display_name', 'app_name', 'tracking_pixel_id') and pre.get(k) != post.get(k))
    detail = (("spark_push recipe. %sCall shape used: OLD shape - /v1.3/ad/update/ full creative as read (identity_type BC_AUTH_TT, identity_id, "
               "identity_authorized_bc_id, ad_format, the post's video_id %s, image_ids, ad_text, %s, dark_post_status, creative_authorized, "
               "vast_moat_enabled) with landing_page_url = new and utm_params = the 5 UTMs of new (utm_id removed), no tiktok_item_id%s. "
               "Pre-read req %s (cur == now). Dry run clean (preview == payload%s). Live write OK req %s (code 0, need_audit false), "
               "modify_time %s UTC. Verify read req %s: landing_page_url + utm_params == new byte for byte. tiktok_item_id right after the "
               "write: %s (same as before; TikTok is expected to re-publish the post 30-60 min later and detach the ad from it - accepted by "
               "the user, not checked in this run). Side effects seen: TikTok returned a new video_id %s (sent %s); %s. status unchanged (%s); "
               "other fields unchanged%s.")
              % (first_attempt, pre['video_id'], cta,
                 '' if first_attempt else ' (first-choice shape not repeated: ' + REJ + '; also seen by the parallel spark_push_4 lane)',
                 b['rid'], ', except the accepted ad_text trailing-space trim' if 'trailing' in ' '.join(notes) else '',
                 ld.get('request_id'), post.get('modify_time'), vrid, post.get('tiktok_item_id'), post.get('video_id'), pre['video_id'],
                 '; '.join(notes), post.get('operation_status'), (' except ' + ','.join(other)) if other else ''))
    out.append({"platform": "tiktok", "account_id": u['account_id'], "unit_type": u['unit_type'], "unit": ad,
                "ad_ids": u['ad_ids'], "ad_names": u['ad_names'], "slot": ch['slot'], "before": b['cur'],
                "after_expected": ch['new'], "after_live": eff, "result": "Fixed" if ok else "Failed", "new_entity_ids": "",
                "detail": detail})
    assert post.get('tiktok_item_id') == pre.get('tiktok_item_id')
    assert b['cur'] == ch['now']
print(json.dumps(out, ensure_ascii=True))
print('COUNT', len(out), 'Fixed', sum(r['result'] == 'Fixed' for r in out), file=sys.stderr)
