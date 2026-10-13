# Read-only: compact results, one per change, from THIS agent's transcript (byte-exact). Prints JSON to stdout; writes no file.
import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply11/work_tiktok_spark_push_5')
from common import *

ups = calls('tiktok_ad_update')
reads = ad_reads()
POSTVID = ('1857548806180898', '1857547881508929', '1857547881492641', '1857547675717698')
out = []
for u in INP:
    ad = u['unit']; ch = u['changes'][0]
    mine = [(i, inp, txt) for i, tid, inp, txt, err in ups if ((inp.get('payload') or {}).get('creatives') or [{}])[0].get('ad_id') == ad]
    live = [(i, inp, txt) for i, inp, txt in mine if inp.get('dry_run') is False]
    first_upd = min(i for i, *_ in mine)
    rr = reads[ad]
    pre = [r for r in rr if r[0] < first_upd][-1]
    ok = [x for x in live if (result_json(x[2]) or {}).get('success')]
    pre_last = [r for r in rr if r[0] < ok[-1][0]][-1]
    before, _, _ = eff_url(pre_last[2].get('landing_page_url'), pre_last[2].get('utm_params'))
    posts = [r for r in rr if r[0] > live[-1][0]]
    po, p1 = posts[-1], posts[0]
    after, _, _ = eff_url(po[2].get('landing_page_url'), po[2].get('utm_params'))
    after1, _, _ = eff_url(p1[2].get('landing_page_url'), p1[2].get('utm_params'))
    assert after1 == after and p1[2].get('tiktok_item_id') == po[2].get('tiktok_item_id') and p1[2].get('utm_params') == po[2].get('utm_params')
    pa, pb = pre[2], po[2]
    att = []
    for i, inp, txt in live:
        j = result_json(txt) or {}
        cr = inp['payload']['creatives'][0]
        sh = 'A (same item, no video_id)' if 'tiktok_item_id' in cr else 'OLD (video_id)'
        if j.get('success'):
            att.append('%s OK req %s' % (sh, j['data']['data']['request_id']))
        else:
            t = (((j.get('error') or {}).get('details') or {}).get('upstream_details') or {}).get('tiktok') or {}
            att.append('%s REFUSED %s "%s" req %s' % (sh, t.get('code'), (t.get('message') or '').strip(), t.get('request_id')))
    sent = ok[-1][1]['payload']['creatives'][0]
    fixed = after == ch['new'] and pb.get('landing_page_url') == ch['new'] and \
        sorted((x['key'], x['value']) for x in pb.get('utm_params') or []) == sorted((x['key'], x['value']) for x in utm_from(ch['new']))
    other = sorted(k for k in set(pa) | set(pb) if k not in ('landing_page_url', 'utm_params', 'modify_time', 'video_id') and pa.get(k) != pb.get(k))
    d = []
    d.append('spark_push; call shape used: OLD (ad/update, every creative field as read, video_id %s, no tiktok_item_id; identity BC_AUTH_TT %s / BC %s kept); only landing_page_url = new + utm_params = UTMs of new (no utm_id)%s' % (
        sent.get('video_id'), pa['identity_id'], pa['identity_authorized_bc_id'], ', pixel as exact string ' + sent['tracking_pixel_id'] if 'tracking_pixel_id' in sent else ''))
    if not any('A (same item' in a for a in att):
        d.append('first-choice shape A not sent (TikTok refuses it on every pushed-video Spark ad, see notes)')
    d.append('pre-read req %s (URL == now)' % pre[1])
    if ad == '1857547881492641':
        d.append('re-read before #2 req %s: URL still == now (attempt #1 changed nothing; TikTok only touched modify_time 13:07:46 UTC)' % pre_last[1])
    d.append('live: ' + ' | '.join('#%d %s' % (n + 1, a) for n, a in enumerate(att)))
    d.append('dry runs: preview == payload, only landing_page_url + utm_params differ from the read')
    d.append('verify req %s%s: URL + utm_params == new byte for byte' % (p1[1], '' if p1[1] == po[1] else ' (same at later re-read req %s)' % po[1]))
    d.append('tiktok_item_id right after the write: %s (%s)' % (p1[2].get('tiktok_item_id'), 'unchanged' if p1[2].get('tiktok_item_id') == pa.get('tiktok_item_id') else 'CHANGED from ' + str(pa.get('tiktok_item_id'))))
    if pa.get('video_id') != pb.get('video_id'):
        d.append('TikTok changed the ad video_id field %s -> %s%s' % (pa.get('video_id'), pb.get('video_id'), " (= the post's own video id)" if ad in POSTVID else ''))
    else:
        d.append('video_id unchanged')
    d.append('no other field changed%s; status %s/%s; modify_time -> %s UTC' % ('' if not other else ' EXCEPT ' + ','.join(other), pb.get('operation_status'), pb.get('secondary_status'), pb.get('modify_time')))
    if u['account_id'] == '7338074303931449345':
        _, ex0, cf0 = eff_url(pa.get('landing_page_url'), pa.get('utm_params'))
        d.append('old utm_params disagreed with the URL (%s); both now = UTMs of new' % '; '.join(
            ['utm_params-only ' + ','.join('%s=%s' % kv for kv in ex0)] * bool(ex0) + ['%s url=%s vs utm_params=%s' % c for c in cf0]))
    d.append('ad_text unchanged (nothing trimmed); post re-publish 30-60 min after the write expected (user-accepted)')
    out.append({"platform": "tiktok", "account_id": u['account_id'], "unit_type": u['unit_type'], "unit": ad,
                "ad_ids": u['ad_ids'], "ad_names": u['ad_names'], "slot": ch['slot'],
                "before": before, "after_expected": ch['new'], "after_live": after,
                "result": "Fixed" if fixed else "Failed", "new_entity_ids": "", "detail": '; '.join(d)})
    assert before == ch['now'] or before in ch['alt_now']
assert len(out) == len(INP) == 17
print(json.dumps(out, ensure_ascii=False))
