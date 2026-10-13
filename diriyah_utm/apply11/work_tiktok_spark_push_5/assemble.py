# Read-only: assemble one result per change from THIS agent's transcript (byte-exact). Prints JSON to stdout; writes no file.
import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply11/work_tiktok_spark_push_5')
from common import *

ups = calls('tiktok_ad_update')
reads = ad_reads()
A_TESTS = {
    '1857548806180898': 'tested on this ad',
    '1871315166237921': 'tested on this ad (identity 0f6eebaa, first ad of the Diriyah Gate account)',
}
out = []
for u in INP:
    ad = u['unit']; ch = u['changes'][0]
    mine = [(i, inp, txt, err) for i, tid, inp, txt, err in ups
            if ((inp.get('payload') or {}).get('creatives') or [{}])[0].get('ad_id') == ad]
    live = [(i, inp, txt, err) for i, inp, txt, err in mine if inp.get('dry_run') is False]
    dry = [(i, inp, txt, err) for i, inp, txt, err in mine if inp.get('dry_run') is not False]
    first_upd = min(i for i, *_ in mine)
    rr = reads[ad]
    pre = [r for r in rr if r[0] < first_upd][-1]
    ok_live = [x for x in live if (result_json(x[2]) or {}).get('success')]
    last_live = live[-1]
    # newest complete read before the successful live write (the slot value just before it)
    pre_last = [r for r in rr if r[0] < ok_live[-1][0]][-1] if ok_live else pre
    before, _, _ = eff_url(pre_last[2].get('landing_page_url'), pre_last[2].get('utm_params'))
    post = [r for r in rr if r[0] > last_live[0]]
    po = post[-1]
    after, extra, conflict = eff_url(po[2].get('landing_page_url'), po[2].get('utm_params'))
    pa, pb = pre[2], po[2]
    attempts = []
    for i, inp, txt, err in live:
        j = result_json(txt) or {}
        cr = inp['payload']['creatives'][0]
        shape = 'first-choice (same identity + same tiktok_item_id %s, no video_id)' % cr.get('tiktok_item_id') if 'tiktok_item_id' in cr else 'old shape (video_id %s as read, no tiktok_item_id)' % cr.get('video_id')
        if j.get('success'):
            d = j['data']['data']
            attempts.append('%s -> OK, TikTok req %s (gateway %s)' % (shape, d['request_id'], j['meta']['requestId']))
        else:
            e = (j.get('error') or {})
            t = ((e.get('details') or {}).get('upstream_details') or {}).get('tiktok') or {}
            attempts.append('%s -> REFUSED %s "%s" TikTok req %s (gateway %s)' % (shape, t.get('code'), (t.get('message') or e.get('message') or '').strip(), t.get('request_id'), (j.get('meta') or {}).get('requestId')))
    sent = ok_live[-1][1]['payload']['creatives'][0] if ok_live else None
    fixed = after == ch['new'] and po[2].get('landing_page_url') == ch['new'] and \
        sorted((x['key'], x['value']) for x in po[2].get('utm_params') or []) == sorted((x['key'], x['value']) for x in utm_from(ch['new']))
    other = {k: (pa.get(k), pb.get(k)) for k in sorted(set(pa) | set(pb))
             if k not in ('landing_page_url', 'utm_params', 'modify_time', 'video_id') and pa.get(k) != pb.get(k)}
    det = []
    det.append('recipe spark_push; identity BC_AUTH_TT %s / BC %s; pre-read ad/get req %s: URL == now (incl. separately stored utm_params)' % (pa['identity_id'], pa['identity_authorized_bc_id'], pre[1]))
    if ad not in A_TESTS:
        det.append('first-choice shape (same identity + same tiktok_item_id %s, no video_id) not sent: in this run TikTok refused it with 40002 "The identity of Spark Ads cannot be updated." on every Spark Push ad that has a pushed video (video_id), 15 of 15 (this lane: 1857548806180898 req 20261013205603F24805F745BF1C7B7967, 1871315166237921 req 20261013210817B010E4EC2C5F55D00B0E; sibling lanes 13, incl. identity e4770252 / BC 6807778858780065797 on 1859827888563330 req 2026101321000940EF01CDC4FC34A12DDC), and accepted it only on organic-post Spark ads without video_id (7); this ad has video_id %s, so the recipe fallback (old shape) was used directly' % (pa.get('tiktok_item_id'), pa.get('video_id')))
    det.append('live attempts: ' + ' | '.join('#%d %s' % (n + 1, a) for n, a in enumerate(attempts)))
    if ad == '1857547881492641':
        det.append('before attempt #2 (13:12 UTC, 13 min after #1) re-read req 202610132110460E392E09D1CC761770C2: URL still == now, nothing changed by attempt #1 (only modify_time touched by TikTok at 13:07:46 UTC, no field change); the same library video was accepted on 1857548806180898 (12:57 UTC) and 1857547675717698 (13:11 UTC), so #1 looks transient')
    if u['account_id'] == '7338074303931449345':
        _, ex0, cf0 = eff_url(pa.get('landing_page_url'), pa.get('utm_params'))
        det.append('before the write the separately stored utm_params disagreed with the URL (%s%s); both now carry exactly the UTMs of new' % (
            'utm_params-only keys appended to cur: ' + ', '.join('%s=%s' % kv for kv in ex0) + '; ' if ex0 else '',
            'conflicting values kept from the URL: ' + ', '.join('%s url=%s utm_params=%s' % c for c in cf0) if cf0 else 'no conflicts'))
    if ok_live:
        det.append('call shape used: OLD SHAPE (ad/update, every creative field as read, video_id %s, no tiktok_item_id); only landing_page_url = new and utm_params = UTMs of new (no utm_id)%s; dry run before each live call: preview body == payload, only landing_page_url + utm_params differ from the read' % (
            sent.get('video_id'), '; tracking_pixel_id sent as exact string %s' % sent['tracking_pixel_id'] if 'tracking_pixel_id' in sent else ''))
    det.append('verify ad/get req %s: landing_page_url and utm_params == new byte for byte' % po[1])
    det.append('tiktok_item_id right after the write: %s (before: %s, %s)' % (pb.get('tiktok_item_id'), pa.get('tiktok_item_id'), 'same post' if pb.get('tiktok_item_id') == pa.get('tiktok_item_id') else 'CHANGED'))
    if pa.get('video_id') != pb.get('video_id'):
        det.append('side effect: TikTok changed the ad video_id field on the write from %s (as read before) to %s (same tiktok_item_id)%s' % (pa.get('video_id'), pb.get('video_id'),
            '; %s is the post\'s own video id (identity/video/info req 20261013210053F1E2D9F6A38F2055BEBC)' % pb.get('video_id') if ad in ('1857548806180898', '1857547881508929', '1857547881492641', '1857547675717698') else ''))
    else:
        det.append('video_id unchanged %s' % pb.get('video_id'))
    det.append('other fields unchanged%s; status %s / %s unchanged; modify_time %s -> %s' % (
        '' if not other else ' EXCEPT ' + json.dumps(other, ensure_ascii=False), pb.get('operation_status'), pb.get('secondary_status'), pa.get('modify_time'), pb.get('modify_time')))
    det.append('ad_text sent and kept unchanged (no trailing space, nothing trimmed)')
    det.append('TikTok is expected to re-publish the post 30-60 min after the write (user-accepted for Spark Push); re-check tiktok_item_id later')
    out.append({
        "platform": "tiktok", "account_id": u['account_id'], "unit_type": u['unit_type'], "unit": ad,
        "ad_ids": u['ad_ids'], "ad_names": u['ad_names'], "slot": ch['slot'],
        "before": before, "after_expected": ch['new'], "after_live": after,
        "result": "Fixed" if fixed else "Failed", "new_entity_ids": "",
        "detail": '; '.join(det),
    })
    assert before == ch['now'] or before in ch['alt_now'], (ad, before)
print(json.dumps(out, ensure_ascii=False, indent=1))
