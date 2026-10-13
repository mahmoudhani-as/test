# Read-only: assemble one result per change from THIS agent's transcript; prints JSON to stdout (no results file).
import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply11/work_tiktok_spark_push_3')
from common import *

SNAP_RID = '202610132119060D8B006104915C7A5D27'


def snapshot():
    out = {}
    for i, tid, inp, txt, err in calls('tiktok_ad_get'):
        j = result_json(txt)
        if not j or not j.get('success'):
            continue
        d = j['data']['data']
        if d.get('request_id') != SNAP_RID:
            continue
        for a in d['data']['list']:
            out[a['ad_id']] = a
    return out


SNAP = snapshot()
reads = ad_reads()
results = []
for u in INP:
    ad = u['unit']
    ch = u['changes'][0]
    ups = updates(ad)
    live = [x for x in ups if x[1].get('dry_run') is False]
    dry = [x for x in ups if x[1].get('dry_run') is True]
    first_live = min(x[0] for x in live)
    last_live = max(x[0] for x in live)
    pre = [r for r in reads.get(ad, []) if r[0] < first_live][-1]
    post = [r for r in reads.get(ad, []) if r[0] > last_live][-1]
    a, p = pre[2], post[2]
    before, _, _ = eff_url(a.get('landing_page_url'), a.get('utm_params'))
    after, _, _ = eff_url(p.get('landing_page_url'), p.get('utm_params'))
    assert before == ch['now'] or before in ch['alt_now'], ad
    assert not excluded(ad, ch['slot'])
    attempts = []
    ok_shape = None
    ok_rid = None
    for i, inp, j, txt in live:
        cr = inp['payload']['creatives'][0]
        shape = 'item' if 'tiktok_item_id' in cr else 'video'
        if j and j.get('success'):
            d = j['data']['data']
            attempts.append((shape, 'OK', d.get('code'), d.get('message'), d.get('request_id')))
            if d.get('code') == 0:
                ok_shape, ok_rid = shape, d.get('request_id')
        else:
            t = ((j or {}).get('error') or {}).get('details', {}).get('upstream_details', {}).get('tiktok', {})
            attempts.append((shape, 'ERR', t.get('code'), t.get('message'), t.get('request_id')))
    fixed = (p.get('landing_page_url') == ch['new'] and after == ch['new']
             and p.get('utm_params') == utm_from(ch['new']))
    # other field changes (excluding the URL, utm_params, modify_time)
    other = []
    for k in sorted(set(a) | set(p)):
        if k in ('landing_page_url', 'utm_params', 'modify_time'):
            continue
        if a.get(k) != p.get(k):
            other.append(k)
    parts = ['spark_push (BC_AUTH_TT, identity %s, BC %s)' % (a.get('identity_id'), a.get('identity_authorized_bc_id'))]
    parts.append('pre-read req %s: URL==%s, item %s, video_id %s, status %s' % (
        pre[1], 'now' if before == ch['now'] else 'alt_now', a.get('tiktok_item_id'), a.get('video_id'), a.get('operation_status')))
    for shape, st, code, msg, rid in attempts:
        if shape == 'item':
            label = 'shape 1 (same tiktok_item_id %s, no video_id)' % a.get('tiktok_item_id')
        else:
            label = 'shape 2 (old: post video_id %s as read, no tiktok_item_id)' % a.get('video_id')
        if st == 'OK':
            trim = a.get('ad_text') is not None and a.get('ad_text') != a.get('ad_text').rstrip()
            parts.append('%s: dry run = URL + utm_params only%s; live ad/update code %s %s req %s' % (label, ' (+ gateway ad_text trim)' if trim else '', code, msg, rid))
        else:
            parts.append('%s: live REJECTED by TikTok %s "%s" req %s (nothing written)' % (label, code, msg, rid))
    parts.append('read-back req %s: URL == new byte for byte, utm_params = UTMs of new (no utm_id)' % post[1] if fixed else
                 'read-back ad/get req %s: landing_page_url %s' % (post[1], p.get('landing_page_url')))
    parts.append('tiktok_item_id right after the write %s (%s)' % (p.get('tiktok_item_id'),
                 'same post' if p.get('tiktok_item_id') == a.get('tiktok_item_id') else 'CHANGED from %s' % a.get('tiktok_item_id')))
    if ok_shape == 'video':
        if p.get('video_id') != a.get('video_id'):
            parts.append('TikTok now reports video_id %s (not sent by us)' % p.get('video_id'))
        parts.append('old shape: TikTok may re-publish the post 30-60 min later and detach the ad from post %s (accepted by the user)' % a.get('tiktok_item_id'))
    if ad == '1826384400556033':
        parts.append('note: TikTok already moved this ad on 11-Oct from post 7481276898408975624 to 7695385229300600070 (apply2 write, work/spark_check); video_id unchanged now')
    if ok_shape == 'item':
        parts.append('first-choice shape accepted, ad keeps post %s' % a.get('tiktok_item_id'))
    if 'ad_text' in other:
        if p.get('ad_text') == (a.get('ad_text') or '').rstrip():
            parts.append('ad_text trailing space trimmed by gateway')
        else:
            parts.append('ad_text changed: %r -> %r' % (a.get('ad_text'), p.get('ad_text')))
    elif a.get('ad_text') != (a.get('ad_text') or '').rstrip():
        parts.append('ad_text trailing space trimmed by gateway in the request; TikTok kept the post caption (ad_text unchanged)')
    for k in other:
        if k in ('ad_text', 'video_id'):
            continue
        if k == 'tracking_pixel_id' and a.get(k) is None and p.get(k) == 0:
            parts.append('tracking_pixel_id absent before, 0 after (no pixel either way, none sent)')
        else:
            parts.append('other field changed: %s %r -> %r' % (k, a.get(k), p.get(k)))
    s = SNAP.get(ad)
    if s:
        parts.append('snapshot req %s (13:19 UTC): URL %s, item %s, modify_time %s' % (
            SNAP_RID, '== new' if s.get('landing_page_url') == ch['new'] else s.get('landing_page_url'), s.get('tiktok_item_id'), s.get('modify_time')))
    parts.append('status unchanged (%s)' % p.get('operation_status') if p.get('operation_status') == a.get('operation_status') else 'STATUS CHANGED')
    results.append({
        'platform': 'tiktok', 'account_id': u['account_id'], 'unit_type': u['unit_type'], 'unit': ad,
        'ad_ids': u['ad_ids'], 'ad_names': u['ad_names'], 'slot': ch['slot'], 'before': before,
        'after_expected': ch['new'], 'after_live': p.get('landing_page_url'),
        'result': 'Fixed' if fixed else 'Failed', 'new_entity_ids': '', 'detail': '; '.join(parts),
    })
print(json.dumps(results, ensure_ascii=False))
