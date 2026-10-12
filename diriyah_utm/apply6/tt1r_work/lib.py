import json, sys
from urllib.parse import urlsplit, parse_qsl

ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
IN = ROOT + '/apply6/in_tiktok_1.json'
OUT = ROOT + '/apply6/out_tiktok_1.jsonl'
EXCL = ROOT + '/work/excl_platform_refused_v2.json'
W = ROOT + '/apply6/tt1r_work'
UNITS = {u['unit']: u for u in json.load(open(IN))}
EXCLUDED = {(x['platform'], x.get('ad_id'), x.get('slot')) for x in json.load(open(EXCL))}
PIXELS = {"7347671240183693330", "7610705877289091089"}


def norm(u):
    s = urlsplit(u)
    return (s.scheme, s.netloc, s.path, s.fragment, sorted(parse_qsl(s.query, keep_blank_values=True)))


def ads_from(path):
    d = json.load(open(path))
    return {a['ad_id']: a for a in d['data']['data']['data']['list'] if isinstance(a, dict)}


def cur_of(ad):
    """Full landing URL incl. separately stored utm_params (appended when a key is not in the URL)."""
    url = ad.get('landing_page_url') or ''
    up = ad.get('utm_params') or []
    q = dict(parse_qsl(urlsplit(url).query, keep_blank_values=True))
    extra, conflicts = [], []
    for p in up:
        k, v = p['key'], p['value']
        if k in q:
            if q[k] != v:
                conflicts.append((k, q[k], v))
        else:
            extra.append((k, v))
    full = url
    if extra:
        full = url + ('&' if urlsplit(url).query else '?') + '&'.join(f'{k}={v}' for k, v in extra)
    return full, extra, conflicts


def classify(uid, cur):
    c = UNITS[uid]['changes'][0]
    if norm(cur) == norm(c['new']):
        return 'AlreadyFixed'
    if cur == c['now'] or cur in c['alt_now']:
        return 'write'
    return 'Skipped'


def kind(ad):
    it, iid = ad.get('identity_type'), ad.get('tiktok_item_id')
    if ad.get('campaign_automation_type') == 'UPGRADED_SMART_PLUS':
        return 'smart_plus'
    if it == 'BC_AUTH_TT' and iid:
        return 'spark_push_hold'
    if it == 'BC_AUTH_TT':
        return 'bc_auth_no_item'
    if it == 'CUSTOMIZED_USER':
        return 'customized_user'
    if it == 'AUTH_CODE':
        return 'spark_pull'
    return 'other:' + str(it)


def done():
    s = set()
    try:
        for l in open(OUT):
            l = l.strip()
            if l:
                s.add(json.loads(l)['unit'])
    except FileNotFoundError:
        pass
    return s


def rec(uid, before, after, result, detail, neid=""):
    u = UNITS[uid]
    c = u['changes'][0]
    assert uid not in done(), 'already recorded ' + uid
    if result == 'Fixed':
        assert after == c['new'], 'after_live != new'
    if result == 'AlreadyFixed':
        assert norm(before) == norm(c['new'])
    r = {"platform": "tiktok", "account_id": u['account_id'], "unit_type": u['unit_type'], "unit": uid,
         "ad_ids": u['ad_ids'], "ad_names": u['ad_names'], "slot": c['slot'], "before": before,
         "after_expected": c['new'], "after_live": after, "result": result, "new_entity_ids": neid,
         "detail": detail}
    with open(OUT, 'a') as f:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print('recorded', uid, result,
          'before==now' if before == c['now'] else ('before in alt' if before in c['alt_now'] else 'before other'))


def build(ad, pixel_exact=None):
    """Full /ad/update/ payload for a BC_AUTH_TT carousel with no tiktok_item_id: every creative field as read,
    only landing_page_url = new (utm_params set to the new UTMs only if the ad already has utm_params)."""
    uid = ad['ad_id']
    u = UNITS[uid]
    assert len(u['changes']) == 1 and u['changes'][0]['slot'] == 'ad.landing_page_url'
    assert ad['ad_name'] == u['ad_names'][0], (ad['ad_name'], u['ad_names'])
    assert kind(ad) == 'bc_auth_no_item', kind(ad)
    assert ad['ad_format'] == 'CAROUSEL_ADS', ad['ad_format']
    assert ('platform', uid, 'ad.landing_page_url') not in EXCLUDED and ('tiktok', uid, 'ad.landing_page_url') not in EXCLUDED
    new = u['changes'][0]['new']
    q = parse_qsl(urlsplit(new).query, keep_blank_values=True)
    assert all(k.startswith('utm_') and k != 'utm_id' for k, v in q), q
    assert len(set(k for k, v in q)) == len(q)
    for k in ('video_id', 'card_id', 'page_id', 'deeplink', 'playable_url', 'avatar_icon_web_uri',
              'impression_tracking_url', 'click_tracking_url', 'viewability_vast_url', 'brand_safety_vast_url', 'ad_texts'):
        assert not ad.get(k), (k, ad.get(k))
    for k in ('viewability_postbid_partner', 'brand_safety_postbid_partner'):
        assert ad.get(k) in (None, 'UNSET'), (k, ad.get(k))
    cr = {"ad_id": uid, "ad_name": ad['ad_name'], "identity_type": ad['identity_type'], "identity_id": ad['identity_id']}
    if ad.get('identity_authorized_bc_id'):
        cr['identity_authorized_bc_id'] = ad['identity_authorized_bc_id']
    cr['ad_format'] = ad['ad_format']
    cr['image_ids'] = ad['image_ids']
    if ad.get('music_id'):
        cr['music_id'] = ad['music_id']
    cr['ad_text'] = ad['ad_text']
    if ad.get('call_to_action_id'):
        cr['call_to_action_id'] = ad['call_to_action_id']
    else:
        cr['call_to_action'] = ad['call_to_action']
    cr['landing_page_url'] = new
    if ad.get('utm_params'):
        cr['utm_params'] = [{"key": k, "value": v} for k, v in q]
    cr['dark_post_status'] = ad['dark_post_status']
    if ad.get('creative_auto_enhancement_strategy_list'):
        cr['creative_auto_enhancement_strategy_list'] = ad['creative_auto_enhancement_strategy_list']
    cr['creative_authorized'] = ad['creative_authorized']
    cr['vast_moat_enabled'] = ad['vast_moat_enabled']
    tp = ad.get('tracking_pixel_id') or ad.get('ad_ref_pixel_id')
    if tp:
        assert pixel_exact in PIXELS and float(int(pixel_exact)) == float(tp), (pixel_exact, tp)
        others = [p for p in PIXELS if p != pixel_exact and float(int(p)) == float(tp)]
        assert not others, others
        cr['tracking_pixel_id'] = pixel_exact
    else:
        assert pixel_exact is None
    p = {"advertiser_id": u['account_id'], "adgroup_id": ad['adgroup_id'], "creatives": [cr]}
    return p
