# Build exact ad/update payloads for the writable units of in_tiktok_2.json from the raw pre-read
# (pre3_raw.json = ad/get req 20261012221356ECB9FB7D5149FC5F3BA8, extracted byte-exact from the transcript).
# usage: python3 -I build.py            -> summary + checks
#        python3 -I build.py <ad_id>    -> escaped payload JSON for the tool call
import json
import sys
import unicodedata
from urllib.parse import urlsplit, parse_qsl

W = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/'
X = W + 'tt2_work/'
PIX = '7347671240183693330'  # pixel/list req 20261012221544D0BB3223DE62981F1C34: "Visit Diriyah - Base Pixel"
assert int(float(PIX)) == int(float(7347671240183693000))
assert int(float('7610705877289091089')) != int(float(7347671240183693000))  # the other pixel does not match

raw = json.load(open(X + 'pre3_raw.json'))
assert raw['data']['data']['code'] == 0
REQ = raw['data']['data']['request_id']
pre = {a['ad_id']: a for a in raw['data']['data']['data']['list']}
units = {u['unit']: u for u in json.load(open(W + 'in_tiktok_2.json'))}
excl = json.load(open('/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/work/excl_platform_refused_v2.json'))
EXCL = {(e['platform'], str(e['ad_id']), e['slot']) for e in excl}

payloads = {}
for ad, a in pre.items():
    u = units[ad]
    assert len(u['changes']) == 1
    ch = u['changes'][0]
    assert ch['slot'] == 'ad.landing_page_url'
    assert ('tiktok', ad, ch['slot']) not in EXCL
    assert a['advertiser_id'] == u['account_id'] and a['ad_name'] == u['ad_names'][0]
    assert a['landing_page_url'] == ch['now'], ad
    new = ch['new']
    sp = urlsplit(new)
    q = parse_qsl(sp.query, keep_blank_values=True)
    assert all(k.startswith('utm_') and k != 'utm_id' for k, v in q) and len({k for k, v in q}) == len(q)
    assert sp.fragment == '' and '+' not in sp.query and '%' not in sp.query
    assert a['campaign_automation_type'] == 'MANUAL' and a['is_aco'] is False and a['ad_format'] == 'SINGLE_VIDEO'
    for k in ('card_id', 'page_id', 'music_id', 'impression_tracking_url', 'click_tracking_url', 'creative_type',
              'ad_texts', 'carousel_image_labels', 'landing_page_urls', 'viewability_vast_url', 'brand_safety_vast_url'):
        assert a.get(k) in (None, ''), (ad, k, a.get(k))
    assert a.get('deeplink') in (None, '') and a.get('playable_url') in (None, '') and a.get('deeplink_type') in (None, 'NORMAL')
    assert a.get('viewability_postbid_partner') in (None, 'UNSET') and a.get('brand_safety_postbid_partner') in (None, 'UNSET')
    for k in ('vertical_video_strategy', 'fallback_type', 'dynamic_destination'):
        assert a.get(k) in (None, 'UNSET'), (ad, k)
    assert a.get('shopping_ads_fallback_type') in (None, 'DEFAULT')
    assert not a.get('dark_post_status') and not a.get('identity_authorized_bc_id')
    tp = a.get('tracking_pixel_id')
    assert tp in (0, None) or int(tp) == 7347671240183693000, tp
    it = a['identity_type']
    item = a.get('tiktok_item_id')
    cr = {"ad_id": ad, "ad_name": a['ad_name'], "identity_id": a['identity_id'], "identity_type": it,
          "ad_format": a['ad_format']}
    if it == 'CUSTOMIZED_USER':
        assert a['video_id'] and a['image_ids'] and not item
        cr["video_id"] = a['video_id']
        cr["image_ids"] = a['image_ids']
        cr["ad_text"] = a['ad_text']
    elif it == 'AUTH_CODE':
        assert item and not a.get('video_id') and a['image_ids'] == []
        cr["tiktok_item_id"] = item          # SAME post, never a video_id
        cr["promotional_music_disabled"] = a['promotional_music_disabled']
        if a.get('ad_text'):
            cr["ad_text"] = a['ad_text']      # = the post caption (empty -> left out, as read)
    else:
        raise SystemExit('unexpected identity ' + it)
    if a.get('call_to_action_id'):
        assert a.get('call_to_action') in (None, '')
        cr["call_to_action_id"] = a['call_to_action_id']
    else:
        assert a['call_to_action']
        cr["call_to_action"] = a['call_to_action']
    cr["landing_page_url"] = new
    cr["utm_params"] = [{"key": k, "value": v} for k, v in q]
    if tp not in (0, None):
        cr["tracking_pixel_id"] = PIX
    if it == 'CUSTOMIZED_USER':
        cr["display_name"] = a['display_name']
        cr["avatar_icon_web_uri"] = a['avatar_icon_web_uri']
        cr["aigc_disclosure_type"] = a['aigc_disclosure_type']
    if a.get('creative_auto_enhancement_strategy_list'):
        cr["creative_auto_enhancement_strategy_list"] = a['creative_auto_enhancement_strategy_list']
    cr["creative_authorized"] = a['creative_authorized']
    cr["vast_moat_enabled"] = a['vast_moat_enabled']
    payloads[ad] = {"advertiser_id": u['account_id'], "adgroup_id": a['adgroup_id'], "creatives": [cr]}

json.dump(payloads, open(X + 'payloads.json', 'w'), ensure_ascii=False, indent=1)


def safe_dumps(o):
    s = json.dumps(o, ensure_ascii=False)
    r = []
    for c in s:
        cat = unicodedata.category(c)
        if ord(c) > 0xFFFF:
            v = ord(c) - 0x10000
            r.append('\\u%04x\\u%04x' % (0xD800 + (v >> 10), 0xDC00 + (v & 0x3FF)))
        elif ord(c) > 127:
            r.append('\\u%04x' % ord(c))
        else:
            r.append(c)
    t = ''.join(r)
    assert json.loads(t) == o
    return t


if len(sys.argv) > 1:
    print(safe_dumps(payloads[sys.argv[1]]))
else:
    print('pre-read req', REQ)
    for ad, p in payloads.items():
        cr = p['creatives'][0]
        t = cr.get('ad_text', '')
        print(ad, cr['identity_type'], sorted(cr.keys()))
        print('   ad_text trailing_ws=', t != t.rstrip(), 'leading_ws=', t != t.lstrip(), 'double_space=', '  ' in t,
              'special=', sorted({'U+%04X' % ord(c) for c in t if unicodedata.category(c) in ('Cf', 'Cc', 'Zs', 'Mn') and c != ' '}))
