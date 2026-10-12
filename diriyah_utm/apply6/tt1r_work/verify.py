# usage: python3 -I verify.py <post_read_marker> <pre_req> <live_req> <post_req> <uid>
import json, sys, subprocess
W = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/tt1r_work'
sys.path.insert(0, W)
from lib import *
marker, pre_req, live_req, post_req, uid = sys.argv[1:6]
subprocess.run(['python3', '-I', W + '/extract.py', marker, f'{W}/postread_{post_req}.json'], check=True)
post = ads_from(f'{W}/postread_{post_req}.json')[uid]
json.dump(post, open(f'{W}/post_{uid}.json', 'w'), ensure_ascii=False, indent=1)
pre = json.load(open(f'{W}/pre_{uid}.json'))
new = UNITS[uid]['changes'][0]['new']
cur_after, extra, conf = cur_of(post)
diff = [(k, pre.get(k), post.get(k)) for k in sorted(set(pre) | set(post)) if pre.get(k) != post.get(k)]
print('after == new byte for byte:', cur_after == new, '| changed fields:', [x[0] for x in diff], '| keys', len(pre), len(post), '| tiktok_item_id:', post.get('tiktok_item_id'), '| utm_params:', post.get('utm_params'))
pix = 'Pixel 7347671240183693330 (Visit Diriyah - Base Pixel, pixel/list req 2026101222143676C358F66C7086F8D3A2; ad/get shows it rounded) sent as exact string. ' if (pre.get('tracking_pixel_id') or pre.get('ad_ref_pixel_id')) else 'No pixel on the ad (tracking_pixel_id 0); none sent. '
note = ''
if pre.get('modify_time', '').startswith('2026-10-12'):
    note = f"; modify_time {pre['modify_time']} at pre-read: ad-group-wide stamp by an actor outside this session, no visible field changed vs earlier reads"
base = (f"pre-read ad/get req {pre_req}: URL == now ({pre['ad_format']}, {pre['identity_type']} identity {pre['identity_id']} / BC {pre.get('identity_authorized_bc_id')}, no tiktok_item_id, "
        f"music_id {pre.get('music_id')}, {len(pre.get('image_ids') or [])} image, call_to_action {pre.get('call_to_action')} (no CTA id), dark_post {pre.get('dark_post_status')}, creative_authorized {str(pre.get('creative_authorized')).lower()}, "
        f"no utm_params, ad {pre.get('operation_status')} / {pre.get('secondary_status')}{note}). " + pix +
        "dry_run preview == payload (creative fields as read, only landing_page_url = new; no utm_params added). "
        f"Live full ad/update code 0 OK req {live_req} need_audit=false. ")
ok = cur_after == new and post['landing_page_url'] == new and set(x[0] for x in diff) <= {'landing_page_url', 'modify_time'} and not post.get('tiktok_item_id')
if ok:
    detail = base + (f"Re-read req {post_req}: landing_page_url == new byte for byte; still no utm_params, no tiktok_item_id; same {len(post)} keys, every other field unchanged "
                     f"(name/identity/image/music/ad_text/CTA/pixel/dark_post/flags/status); modify_time {post.get('modify_time')}.")
    rec(uid, pre['landing_page_url'], post['landing_page_url'], 'Fixed', detail)
else:
    print('NOT OK -> needs manual handling; diff:', diff)
