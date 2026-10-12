#!/usr/bin/env python3
"""Helpers for apply6 in_tiktok_5: classify live URL, build ad/update payloads, check read-backs, append results."""
import json, sys, os
from urllib.parse import urlsplit, parse_qsl

ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
INP = ROOT + '/apply6/in_tiktok_5.json'
OUT = ROOT + '/apply6/out_tiktok_5.jsonl'
WORK = ROOT + '/apply6/tt5_work'
PIXELS = {7347671240183693000: '7347671240183693330'}  # ad/get shows the Base Pixel rounded; exact id from pixel/list

def units():
    return {u['unit']: u for u in json.load(open(INP))}

def norm(u):
    s = urlsplit(u)
    return (s.scheme, s.netloc, s.path, s.fragment, sorted(parse_qsl(s.query, keep_blank_values=True)))

def same(a, b):
    return a == b or norm(a) == norm(b)

def classify(unit, cur):
    ch = units()[unit]['changes'][0]
    if same(cur, ch['new']):
        return 'AlreadyFixed', 'exact' if cur == ch['new'] else 'param-order'
    if cur == ch['now'] or same(cur, ch['now']):
        return 'write', 'now'
    for i, a in enumerate(ch.get('alt_now', [])):
        if cur == a or same(cur, a):
            return 'write', 'alt_now[%d]' % i
    return 'Skipped', 'changed since plan'

def new_utms(new):
    return [{'key': k, 'value': v} for k, v in parse_qsl(urlsplit(new).query, keep_blank_values=True) if k.startswith('utm_')]

def build(unit, rec):
    """rec = full ad/get record (as read). Returns ad/update payload."""
    ch = units()[unit]['changes'][0]
    c = {'ad_id': rec['ad_id'], 'ad_name': rec['ad_name'], 'identity_type': rec['identity_type'], 'identity_id': rec['identity_id']}
    if rec.get('identity_authorized_bc_id'):
        c['identity_authorized_bc_id'] = rec['identity_authorized_bc_id']
    c['ad_format'] = rec['ad_format']
    if rec.get('video_id'):
        c['video_id'] = rec['video_id']
    if rec.get('image_ids'):
        c['image_ids'] = rec['image_ids']
    if rec['identity_type'] != 'CUSTOMIZED_USER' and not rec.get('video_id') and not rec.get('image_ids') and rec.get('tiktok_item_id'):
        c['tiktok_item_id'] = rec['tiktok_item_id']   # pure Spark Pull: only documented shape
    if rec.get('promotional_music_disabled') is not None and 'tiktok_item_id' in c:
        c['promotional_music_disabled'] = rec['promotional_music_disabled']
    c['ad_text'] = rec['ad_text']
    if rec.get('call_to_action_id'):
        c['call_to_action_id'] = rec['call_to_action_id']
    elif rec.get('call_to_action'):
        c['call_to_action'] = rec['call_to_action']
    c['landing_page_url'] = ch['new']
    if rec.get('utm_params') is not None:
        c['utm_params'] = new_utms(ch['new'])
    px = rec.get('tracking_pixel_id')
    if px:
        if px not in PIXELS:
            raise SystemExit('unknown pixel %r' % px)
        c['tracking_pixel_id'] = PIXELS[px]
    if rec['identity_type'] == 'CUSTOMIZED_USER':
        if rec.get('display_name'):
            c['display_name'] = rec['display_name']
        if rec.get('avatar_icon_web_uri'):
            c['avatar_icon_web_uri'] = rec['avatar_icon_web_uri']
    if rec.get('dark_post_status'):
        c['dark_post_status'] = rec['dark_post_status']
    if rec.get('creative_authorized') is not None:
        c['creative_authorized'] = rec['creative_authorized']
    if rec.get('vast_moat_enabled') is not None:
        c['vast_moat_enabled'] = rec['vast_moat_enabled']
    return {'advertiser_id': rec['advertiser_id'], 'adgroup_id': rec['adgroup_id'], 'creatives': [c]}

COMPARE_SKIP = {'landing_page_url', 'utm_params', 'modify_time', 'video_id'}

def compare(pre, post, unit):
    ch = units()[unit]['changes'][0]
    out = {'url_equal_new': post.get('landing_page_url') == ch['new'],
           'utm_params_ok': sorted((p['key'], p['value']) for p in (post.get('utm_params') or [])) == sorted((p['key'], p['value']) for p in new_utms(ch['new'])),
           'utm_id_present': any(p['key'] == 'utm_id' for p in (post.get('utm_params') or []))}
    diffs = {}
    for k in sorted(set(pre) | set(post)):
        if k in COMPARE_SKIP:
            continue
        if pre.get(k) != post.get(k):
            diffs[k] = [pre.get(k), post.get(k)]
    out['other_diffs'] = diffs
    out['video_id'] = [pre.get('video_id'), post.get('video_id')]
    out['modify_time'] = [pre.get('modify_time'), post.get('modify_time')]
    return out

def append(row):
    u = units()[row['unit']]
    base = {'platform': 'tiktok', 'account_id': u['account_id'], 'unit_type': u['unit_type'], 'unit': u['unit'],
            'ad_ids': u['ad_ids'], 'ad_names': u['ad_names'], 'slot': u['changes'][0]['slot'],
            'after_expected': u['changes'][0]['new']}
    base.update(row)
    keys = ['platform', 'account_id', 'unit_type', 'unit', 'ad_ids', 'ad_names', 'slot', 'before', 'after_expected', 'after_live', 'result', 'new_entity_ids', 'detail']
    line = {k: base.get(k, '') for k in keys}
    with open(OUT, 'a') as f:
        f.write(json.dumps(line, ensure_ascii=False) + '\n')
    print('appended', line['unit'], line['result'])

if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'classify':
        print(classify(sys.argv[2], sys.argv[3]))
    elif cmd == 'build':
        rec = json.load(open(sys.argv[3]))
        p = build(sys.argv[2], rec)
        json.dump(p, open(WORK + '/payload_%s.json' % sys.argv[2], 'w'), ensure_ascii=False, indent=1)
        print(json.dumps(p, ensure_ascii=False))
    elif cmd == 'compare':
        print(json.dumps(compare(json.load(open(sys.argv[3])), json.load(open(sys.argv[4])), sys.argv[2]), ensure_ascii=False, indent=1))
    elif cmd == 'append':
        append(json.load(open(sys.argv[2])))
