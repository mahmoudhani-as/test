import json, copy, re, os
from urllib.parse import urlsplit, parse_qsl

ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
IN = ROOT + '/apply6/in_meta_22.json'
OUT = ROOT + '/apply6/out_meta_22.jsonl'
WORK = ROOT + '/apply6/meta22_work'
EXCL = ROOT + '/work/excl_platform_refused_v2.json'

# creative fields copied into the new creative (when present on the live creative)
SEND_KEYS = ['name', 'object_story_spec', 'asset_feed_spec', 'degrees_of_freedom_spec', 'threads_user_id',
             'authorization_category', 'format_transformation_spec', 'portrait_customizations',
             'contextual_multi_ads', 'creative_sourcing_spec', 'media_sourcing_spec', 'url_tags',
             'call_to_action', 'source_instagram_media_id', 'object_id', 'body', 'title', 'link_url',
             'image_hash', 'video_id', 'platform_customizations', 'link_destination_display_url',
             'regional_regulation_disclaimer_spec', 'ad_disclaimer_spec', 'branded_content',
             'page_welcome_message', 'product_set_id', 'template_url_spec', 'image_crops', 'object_url',
             'applink_treatment', 'interactive_components_spec', 'categorization_criteria',
             'destination_set_id', 'omnichannel_link_spec', 'facebook_branded_content',
             'instagram_branded_content', 'dynamic_ad_voice', 'bundle_folder_id', 'recommender_settings',
             'product_data', 'link_og_id', 'place_page_set_id', 'object_store_url',
             'messenger_sponsored_message', 'playable_asset_id', 'source_facebook_post_id']
# read-only / derived fields that are never sent
DERIVED = ['id', 'status', 'actor_id', 'object_type', 'effective_object_story_id',
           'effective_instagram_media_id', 'use_page_actor_override', 'instagram_user_id']


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
    """same scheme/host/path/fragment and the same query params in any order"""
    if not isinstance(a, str) or not isinstance(b, str):
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
    """landing URL incl. url_tags (url_tags are appended by Meta at serve time)"""
    v = get_slot(creative, slot)
    tags = creative.get('url_tags')
    if tags:
        v = v + ('&' if '?' in v else '?') + tags
    return v


def classify(ad_id, creative):
    u = unit(ad_id)
    res = []
    for c in u['changes']:
        try:
            cur = full_url(creative, c['slot'])
        except Exception as e:
            cur = None
        if excluded(ad_id, c['slot']):
            v = 'Excluded'
        elif cur is not None and same_url(cur, c['new']):
            v = 'AlreadyFixed'
        elif cur == c['now'] or cur in c['alt_now']:
            v = 'Write'
        else:
            v = 'Skipped'
        res.append((c, cur, v))
    return res


def build_payload(creative, ad_id):
    """exact copy of the live creative with only the listed slots set to new"""
    u = unit(ad_id)
    unknown = [k for k in creative if k not in SEND_KEYS and k not in DERIVED]
    assert not unknown, ('unhandled creative keys', unknown)
    assert not creative.get('url_tags'), 'creative has url_tags - handle manually'
    p = {k: copy.deepcopy(creative[k]) for k in SEND_KEYS if k in creative}
    for c in u['changes']:
        set_slot(p, c['slot'], c['new'])
    return p


def diff(a, b, path=''):
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append(f'+ {path}.{k} = {json.dumps(b[k], ensure_ascii=False)[:200]}')
            elif k not in b:
                out.append(f'- {path}.{k} = {json.dumps(a[k], ensure_ascii=False)[:200]}')
            else:
                out += diff(a[k], b[k], f'{path}.{k}')
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f'~ {path} len {len(a)} -> {len(b)}')
        for i, (x, y) in enumerate(zip(a, b)):
            out += diff(x, y, f'{path}[{i}]')
    else:
        if a != b:
            out.append(f'~ {path}: {json.dumps(a, ensure_ascii=False)[:250]} -> {json.dumps(b, ensure_ascii=False)[:250]}')
    return out


def load_mcp(path):
    """parse a persisted MCP tool result; refuse truncated output"""
    raw = json.load(open(path))
    txt = raw[0]['text'] if isinstance(raw, list) else json.dumps(raw)
    assert 'MCP_OUTPUT_TRUNCATED' not in txt and 'more items truncated' not in txt, 'truncated MCP output'
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
    print('recorded', ad_id, change_idx, result, 'after==new:', after_live == c['new'])
