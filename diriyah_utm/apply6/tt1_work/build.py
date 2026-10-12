"""Build a TikTok /v1.3/ad/update/ payload from transcribed live values.

usage: python3 build.py <live_json_file>
The live json file holds the fields as read with ad/get (transcribed), plus
"pixel" (exact string or null) and "has_utm" (bool).
Prints the payload with ensure_ascii=True so every non-ASCII code point is visible.
"""
import json, sys
from urllib.parse import urlsplit, parse_qsl
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/tt1_work')
from rec import UNITS

PIXELS = {"7347671240183693330": 7347671240183693000, "7610705877289091089": 7610705877289091000}

a = json.load(open(sys.argv[1]))
u = UNITS[a['ad_id']]
assert len(u['changes']) == 1 and u['changes'][0]['slot'] == 'ad.landing_page_url'
assert a['ad_name'] == u['ad_names'][0], (a['ad_name'], u['ad_names'])
new = u['changes'][0]['new']
q = parse_qsl(urlsplit(new).query, keep_blank_values=True)
assert all(k.startswith('utm_') and k != 'utm_id' for k, v in q), q
assert len(set(k for k, v in q)) == len(q)

cr = {"ad_id": a['ad_id'], "ad_name": a['ad_name'],
      "identity_type": a['identity_type'], "identity_id": a['identity_id']}
if a.get('identity_authorized_bc_id'):
    cr['identity_authorized_bc_id'] = a['identity_authorized_bc_id']
cr['ad_format'] = a['ad_format']
if a.get('video_id'):
    cr['video_id'] = a['video_id']
if a.get('image_ids'):
    cr['image_ids'] = a['image_ids']
if a.get('music_id'):
    cr['music_id'] = a['music_id']
cr['ad_text'] = a['ad_text']
if a.get('call_to_action_id'):
    cr['call_to_action_id'] = a['call_to_action_id']
else:
    cr['call_to_action'] = a['call_to_action']
cr['landing_page_url'] = new
if a['has_utm']:
    cr['utm_params'] = [{"key": k, "value": v} for k, v in q]
cr['dark_post_status'] = a['dark_post_status']
if a.get('creative_auto_enhancement_strategy_list'):
    cr['creative_auto_enhancement_strategy_list'] = a['creative_auto_enhancement_strategy_list']
cr['creative_authorized'] = a['creative_authorized']
cr['vast_moat_enabled'] = a['vast_moat_enabled']
if a.get('pixel'):
    assert a['pixel'] in PIXELS and PIXELS[a['pixel']] == a['pixel_rounded'], (a['pixel'], a.get('pixel_rounded'))
    cr['tracking_pixel_id'] = a['pixel']
else:
    assert a.get('pixel_rounded') in (None, 0), a.get('pixel_rounded')
for k in ('brand_safety_postbid_partner',):
    if a.get(k) and a[k] != 'UNSET':
        raise SystemExit('unexpected ' + k)
p = {"advertiser_id": u['account_id'], "adgroup_id": a['adgroup_id'], "creatives": [cr]}
json.dump(p, open(sys.argv[1].replace('live_', 'payload_'), 'w'), ensure_ascii=False, indent=1)
print(json.dumps(p, ensure_ascii=True))
print('ad_text codepoints non-ascii:', [hex(ord(ch)) for ch in a['ad_text'] if ord(ch) > 127 and not (0x600 <= ord(ch) <= 0x6ff)])
print('ad_text len', len(a['ad_text']), 'ends', repr(a['ad_text'][-3:]))
