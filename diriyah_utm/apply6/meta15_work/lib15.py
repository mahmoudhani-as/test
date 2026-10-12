import json, copy, re, os
from urllib.parse import urlsplit, parse_qsl

ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
IN = ROOT + '/apply6/in_meta_15.json'
OUT = ROOT + '/apply6/out_meta_15.jsonl'
W = ROOT + '/apply6/meta15_work/'
EXCL = ROOT + '/work/excl_platform_refused_v2.json'


def units():
    return json.load(open(IN))


def unit(ad_id):
    for u in units():
        if u['unit'] == ad_id:
            return u
    raise KeyError(ad_id)


def excluded(ad_id, slot):
    for x in json.load(open(EXCL)):
        if str(x.get('ad_id')) == str(ad_id) and x.get('slot') == slot:
            return True
    return False


def same_url(a, b):
    if a is None or b is None:
        return False
    A, B = urlsplit(a), urlsplit(b)
    return (A.scheme, A.netloc, A.path, A.fragment) == (B.scheme, B.netloc, B.path, B.fragment) and \
        sorted(parse_qsl(A.query, keep_blank_values=True)) == sorted(parse_qsl(B.query, keep_blank_values=True))


def _walk(obj, part):
    m = re.fullmatch(r'(\w+)\[(\d+)\]', part)
    if m:
        return obj[m.group(1)][int(m.group(2))]
    return obj[part]


def get_slot(creative, slot):
    assert slot.startswith('creative.')
    cur = creative
    for part in slot[len('creative.'):].split('.'):
        cur = _walk(cur, part)
    return cur


def set_slot(creative, slot, value):
    parts = slot[len('creative.'):].split('.')
    cur = creative
    for part in parts[:-1]:
        cur = _walk(cur, part)
    last = parts[-1]
    m = re.fullmatch(r'(\w+)\[(\d+)\]', last)
    if m:
        cur[m.group(1)][int(m.group(2))] = value
    else:
        assert last in cur, (slot, 'missing leaf')
        cur[last] = value


def full_url(creative, slot):
    """landing URL incl. url_tags if any"""
    v = get_slot(creative, slot)
    tags = creative.get('url_tags')
    if tags:
        v = v + ('&' if '?' in v else '?') + tags
    return v


def diff(a, b, path=''):
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append(f'+ {path}.{k} = {json.dumps(b[k], ensure_ascii=False)[:300]}')
            elif k not in b:
                out.append(f'- {path}.{k} = {json.dumps(a[k], ensure_ascii=False)[:300]}')
            else:
                out += diff(a[k], b[k], f'{path}.{k}')
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f'~ {path} len {len(a)} -> {len(b)}')
        for i, (x, y) in enumerate(zip(a, b)):
            out += diff(x, y, f'{path}[{i}]')
    else:
        if a != b:
            out.append(f'~ {path}: {json.dumps(a, ensure_ascii=False)[:300]} -> {json.dumps(b, ensure_ascii=False)[:300]}')
    return out


def load_persisted(path):
    blocks = json.load(open(path))
    txt = ''.join(b['text'] for b in blocks if b.get('type') == 'text')
    return json.loads(txt)


def record(ad_id, change_idx, before, after_live, result, new_ids, detail):
    u = unit(ad_id)
    c = u['changes'][change_idx]
    if result == 'Fixed':
        assert after_live == c['new'], 'after mismatch'
        assert before == c['now'] or before in c['alt_now'], 'before not now/alt_now'
    if result == 'AlreadyFixed':
        assert same_url(before, c['new'])
    rec = {"platform": "meta", "account_id": u['account_id'], "unit_type": u['unit_type'], "unit": u['unit'],
           "ad_ids": u['ad_ids'], "ad_names": u['ad_names'], "slot": c['slot'], "before": before,
           "after_expected": c['new'], "after_live": after_live, "result": result,
           "new_entity_ids": new_ids, "detail": detail}
    with open(OUT, 'a') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print('recorded', ad_id, c['slot'], result, 'after==new:', after_live == c['new'])


import unicodedata


def dumps_safe(o):
    """JSON (compact) with non-ASCII letters kept but every invisible/format char escaped as \\uXXXX"""
    s = json.dumps(o, ensure_ascii=False, separators=(',', ':'))
    out = []
    for ch in s:
        cat = unicodedata.category(ch)
        if ord(ch) > 127 and (cat.startswith('C') or cat.startswith('Z') or cat == 'Mn' and False):
            out.append('\\u%04x' % ord(ch))
        else:
            out.append(ch)
    return ''.join(out)


DROP_TOP = {'id', 'account_id', 'actor_id', 'object_type', 'status', 'effective_object_story_id',
            'effective_instagram_media_id', 'use_page_actor_override', 'body', 'title', 'image_hash',
            'call_to_action', 'image_crops', 'instagram_user_id', 'video_id', 'object_story_id'}
KEEP_TOP = ['name', 'object_story_spec', 'asset_feed_spec', 'degrees_of_freedom_spec', 'contextual_multi_ads',
            'creative_sourcing_spec', 'media_sourcing_spec', 'threads_user_id', 'authorization_category',
            'portrait_customizations', 'url_tags', 'source_instagram_media_id', 'platform_customizations',
            'branded_content', 'ad_disclaimer_spec', 'regional_regulation_disclaimer_spec',
            'link_destination_display_url', 'page_welcome_message', 'applink_treatment',
            'interactive_components_spec', 'template_url', 'product_set_id', 'recommender_settings',
            'facebook_branded_content', 'instagram_branded_content', 'bundle_folder_id',
            'categorization_criteria', 'place_page_set_id', 'object_id', 'link_url', 'object_url']


def build_payload(creative, changes):
    unknown = [k for k in creative if k not in DROP_TOP and k not in KEEP_TOP]
    assert not unknown, ('unhandled creative fields', unknown)
    p = {}
    for k in KEEP_TOP:
        if k in creative:
            p[k] = copy.deepcopy(creative[k])
    css = p.get('creative_sourcing_spec')
    if css and 'site_links_spec' in css:
        for sl in css['site_links_spec']:
            if 'site_link_image_hash' in sl:
                sl.pop('site_link_image_url', None)
    vd = p.get('object_story_spec', {}).get('video_data')
    if vd and 'image_hash' in vd:
        vd.pop('image_url', None)
    # apply URL changes on a creative-shaped view
    view = {'object_story_spec': p.get('object_story_spec'), 'asset_feed_spec': p.get('asset_feed_spec')}
    for ch in changes:
        old = get_slot(view, ch['slot'])
        assert old == ch['now'] or old in ch['alt_now'], (ch['slot'], old)
        set_slot(view, ch['slot'], ch['new'])
    return p


def expected_new_view(creative, changes):
    """the old creative with only the slot(s) changed - for comparison with the read-back"""
    c = copy.deepcopy(creative)
    for ch in changes:
        set_slot(c, ch['slot'], ch['new'])
    return c


def has_trunc(o):
    if isinstance(o, dict):
        return any('mcp_trunc' in k.lower() for k in o) or any(has_trunc(v) for v in o.values())
    if isinstance(o, list):
        return any(has_trunc(v) for v in o)
    if isinstance(o, str):
        return 'TRUNCATED' in o or 'more items truncated' in o
    return False


IGNORE_DERIVED = ('.creative.id', '.creative.name', '.creative.effective_object_story_id',
                  '.creative.effective_instagram_media_id', '.updated_time', '.effective_status')


def verify_ad(old_ad, new_ad, changes):
    """compare the new ad read-back with the old ad read, expecting only the slot(s) to change"""
    exp = copy.deepcopy(old_ad)
    for ch in changes:
        set_slot(exp['creative'], ch['slot'], ch['new'])
    d = diff(exp, new_ad)
    keep = []
    for line in d:
        path = line[2:].split(' ')[0].rstrip(':')
        if path in IGNORE_DERIVED:
            continue
        if '.site_link_image_url' in path or path.endswith('.image_url'):
            continue  # signed CDN URLs regenerate on every read
        keep.append(line)
    return keep


def env_size(ads):
    r = {'success': True, 'data': {'success': True, 'action': 'meta_ad_account_id_ads_get', 'method': 'GET', 'host': 'graph.facebook.com', 'path': '/v25.0/act_2194833637927644/ads', 'dryRun': False, 'data': {'data': ads}, 'meta': {'requestId': None, 'waitedMs': 826, 'throttled': False, 'warnings': [], 'compatibility': None, 'compatibilitySkipped': True}}, 'meta': {'requestId': '58c56e1a-437a-40e5-ab6a-8212a211e7e8', 'latencyMs': 3743}}
    t = json.dumps(r, ensure_ascii=False, indent=2)
    return len(t), len(t.encode())
