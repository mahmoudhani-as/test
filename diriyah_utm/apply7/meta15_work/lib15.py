import json, re, copy
from urllib.parse import urlsplit, parse_qsl

ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
IN = ROOT + '/apply7/in_meta_15.json'
OUT = ROOT + '/apply7/out_meta_15.jsonl'
WORK = ROOT + '/apply7/meta15_work'
EXCL = ROOT + '/work/excl_platform_refused_v2.json'


def units():
    return json.load(open(IN))


def unit(ad_id):
    for u in units():
        if u['unit'] == ad_id:
            return u
    raise KeyError(ad_id)


def excluded(ad_id, slot):
    return any(str(x.get('ad_id')) == str(ad_id) and x.get('slot') == slot for x in json.load(open(EXCL)))


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
    """landing URL incl. url_tags if the creative has them"""
    u = get_slot(creative, slot)
    tags = creative.get('url_tags')
    if tags:
        u = u + ('&' if '?' in u else '?') + tags
    return u


def classify(ad_id, slot, cur):
    u = unit(ad_id)
    c = [c for c in u['changes'] if c['slot'] == slot][0]
    if excluded(ad_id, slot):
        return 'Excluded'
    if same_url(cur, c['new']):
        return 'AlreadyFixed'
    if cur == c['now'] or cur in c['alt_now']:
        return 'Write'
    return 'Skipped'


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
        if a != b or type(a) != type(b):
            out.append(f'~ {path}: {json.dumps(a, ensure_ascii=False)[:400]} -> {json.dumps(b, ensure_ascii=False)[:400]}')
    return out


# settable creative fields copied from the live read (read-only / derived fields are not sent)
COPY_KEYS = ['name', 'object_story_spec', 'asset_feed_spec', 'url_tags', 'degrees_of_freedom_spec',
             'creative_sourcing_spec', 'media_sourcing_spec', 'contextual_multi_ads', 'threads_user_id',
             'authorization_category', 'format_transformation_spec', 'platform_customizations',
             'portrait_customizations', 'interactive_components_spec', 'regional_regulation_disclaimer_spec',
             'ad_disclaimer_spec', 'branded_content', 'facebook_branded_content', 'instagram_branded_content',
             'source_instagram_media_id', 'call_to_action', 'object_id', 'object_story_id', 'template_url_spec',
             'product_set_id', 'applink_treatment', 'page_welcome_message', 'recommender_settings',
             'categorization_criteria', 'category_media_source', 'dynamic_ad_voice', 'image_crops',
             'playable_asset_id', 'destination_set_id', 'omnichannel_link_spec', 'bundle_folder_id']
SKIP_KEYS = ['id', 'account_id', 'status', 'actor_id', 'object_type', 'effective_authorization_category',
             'effective_object_story_id', 'effective_instagram_media_id', 'thumbnail_url', 'use_page_actor_override',
             'instagram_user_id', 'image_url', 'instagram_permalink_url', 'body', 'title', 'link_url', 'image_hash',
             'video_id', 'call_to_action_type', 'object_url', 'link_destination_display_url', 'template_url',
             'link_og_id', 'object_store_url', 'adlabels']


def build_payload(orig, unit_obj, write_slots):
    unknown = [k for k in orig if k not in COPY_KEYS and k not in SKIP_KEYS]
    assert not unknown, ('unknown creative keys, review before copying', unknown)
    p = {k: copy.deepcopy(orig[k]) for k in COPY_KEYS if k in orig}
    for c in unit_obj['changes']:
        if c['slot'] in write_slots:
            parts = c['slot'][len('creative.'):]
            set_slot_plain(p, parts, c['new'])
    return p


def set_slot_plain(obj, path, value):
    parts = path.split('.')
    cur = obj
    for part in parts[:-1]:
        cur = _walk(cur, part)
    last = parts[-1]
    m = re.fullmatch(r'(\w+)\[(\d+)\]', last)
    if m:
        cur[m.group(1)][int(m.group(2))] = value
    else:
        assert last in cur, (path, 'missing leaf')
        cur[last] = value


def record(ad_id, slot, before, after_live, result, new_ids, detail):
    u = unit(ad_id)
    c = [c for c in u['changes'] if c['slot'] == slot][0]
    if result == 'Fixed':
        assert after_live == c['new'], 'after_live != new'
        assert before == c['now'] or before in c['alt_now'], 'before not now/alt_now'
    if result == 'AlreadyFixed':
        assert same_url(before, c['new'])
    rec = {"platform": "meta", "account_id": u['account_id'], "unit_type": u['unit_type'], "unit": u['unit'],
           "ad_ids": u['ad_ids'], "ad_names": u['ad_names'], "slot": slot, "before": before,
           "after_expected": c['new'], "after_live": after_live, "result": result,
           "new_entity_ids": new_ids, "detail": detail}
    with open(OUT, 'a') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print('recorded', ad_id, slot, result, 'after==new:', after_live == c['new'])
