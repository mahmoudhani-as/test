# usage: python3 -I summarize2.py -> concise results array (JSON lines) from THIS agent's transcript. Read-only, writes nothing.
import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply11/work_tiktok_spark_push_1')
from common import *
from build import build, is_update_for

reads = ad_reads()
out = []
for u in INP:
    ad = u['unit']
    b = build(ad, 'video')
    ch, pre = b['ch'], b['a']
    ups = [(i, inp, txt, err) for i, tid, inp, txt, err in calls('tiktok_ad_update') if is_update_for(inp, ad)]
    lives = [x for x in ups if x[1].get('dry_run', True) is False]
    li, linp, ltxt, lerr = lives[-1]
    lj = result_json(ltxt) or {}
    ld = (lj.get('data') or {}).get('data') or {}
    assert lj.get('success') and ld.get('code') == 0 and not diff(linp['payload'], b['payload'])
    vi, vrid, post = [r for r in reads[ad] if r[0] > li][0]
    eff, extra, conflict = eff_url(post.get('landing_page_url'), post.get('utm_params'))
    ok = (eff == ch['new'] and post.get('landing_page_url') == ch['new'] and not extra and not conflict and
          sorted((x['key'], x['value']) for x in post['utm_params']) == sorted((x['key'], x['value']) for x in utm_from(ch['new'])))
    other = sorted(k for k in set(pre) | set(post) if k not in ('landing_page_url', 'utm_params', 'modify_time', 'video_id', 'ad_text',
                                                                  'display_name', 'app_name', 'tracking_pixel_id') and pre.get(k) != post.get(k))
    assert not other and post.get('tiktok_item_id') == pre.get('tiktok_item_id') and b['cur'] == ch['now']
    sent_text = b['payload']['creatives'][0].get('ad_text') or ''
    trim = sent_text != sent_text.rstrip()
    if len(lives) == 2:
        fi, finp, ftxt, ferr = lives[0]
        assert ferr and 'tiktok_item_id' in finp['payload']['creatives'][0] and 'video_id' not in finp['payload']['creatives'][0]
        head = ("spark_push. Attempt 1 = first-choice shape (BC_AUTH_TT identity + same tiktok_item_id %s, no video_id; dry run clean) "
                "REJECTED by TikTok 40002 'The identity of Spark Ads cannot be updated.' (req 202610132054223C7A9212DC129023B1F0; re-read "
                "req 202610132054403661F698A33EF178DE91: ad unchanged). Attempt 2 = OLD shape: " % pre['tiktok_item_id'])
    else:
        head = ("spark_push. Call shape: OLD (first-choice shape not repeated after TikTok rejected it with 40002 on 1838614376695858): ")
    pix = ('pixel sent as exact string 7347671240183693330' if pre.get('tracking_pixel_id') not in (0, None)
           else 'no pixel (tracking_pixel_id %s, not sent%s)' % (pre.get('tracking_pixel_id'),
                                                                 '; reads 0 after' if pre.get('tracking_pixel_id') is None else ''))
    cta = ('call_to_action_id %s' % pre['call_to_action_id']) if pre.get('call_to_action_id') else ('call_to_action %s' % pre.get('call_to_action'))
    detail = (head + "full ad/update with every creative field as read (BC_AUTH_TT identity, the post's video_id %s, image_ids, ad_text, %s, "
              "dark_post_status ON) + landing_page_url = new + utm_params = UTMs of new (utm_id removed), no tiktok_item_id. Pre-read req %s "
              "(cur == now); dry run clean%s; live req %s code 0 (need_audit false), modify_time %s UTC; verify read req %s: URL + "
              "utm_params == new byte for byte. tiktok_item_id right after the write: %s (unchanged; TikTok may re-publish the post 30-60 "
              "min later - accepted by the user). TikTok-side: video_id now %s; %s;%s status %s unchanged, no other field changed."
              % (pre['video_id'], cta, b['rid'], ' (ad_text trailing space trimmed by gateway - accepted)' if trim else '',
                 ld.get('request_id'), post.get('modify_time'), vrid, post.get('tiktok_item_id'), post.get('video_id'), pix,
                 ' ad_text trailing space trimmed by gateway;' if trim else '', post.get('operation_status')))
    out.append({"platform": "tiktok", "account_id": u['account_id'], "unit_type": u['unit_type'], "unit": ad,
                "ad_ids": u['ad_ids'], "ad_names": u['ad_names'], "slot": ch['slot'], "before": b['cur'],
                "after_expected": ch['new'], "after_live": eff, "result": "Fixed" if ok else "Failed", "new_entity_ids": "",
                "detail": detail})
for r in out:
    print(json.dumps(r, ensure_ascii=True))
print('COUNT', len(out), 'Fixed', sum(r['result'] == 'Fixed' for r in out), 'chars', sum(len(r['detail']) for r in out), file=sys.stderr)
