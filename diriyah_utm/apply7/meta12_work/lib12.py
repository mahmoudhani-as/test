import json, copy, re, datetime
from urllib.parse import urlsplit, parse_qsl

ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
IN = ROOT + '/apply7/in_meta_12.json'
OUT = ROOT + '/apply7/out_meta_12.jsonl'
W = ROOT + '/apply7/meta12_work/'
PROG = W + 'progress.jsonl'
EXCL = ROOT + '/work/excl_platform_refused_v2.json'
TR = '/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/tool-results/'


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
    """landing URL = slot value + url_tags (Meta appends url_tags at serve time)"""
    v = get_slot(creative, slot)
    tags = creative.get('url_tags')
    if tags:
        v = v + ('&' if '?' in v else '?') + tags
    return v


def classify(ad_id, creative):
    u = unit(ad_id)
    res = []
    for i, c in enumerate(u['changes']):
        try:
            cur = full_url(creative, c['slot'])
        except Exception:
            cur = None
        if excluded(ad_id, c['slot']):
            v = 'Excluded'
        elif cur is not None and same_url(cur, c['new']):
            v = 'AlreadyFixed'
        elif cur == c['now'] or cur in c['alt_now']:
            v = 'Write'
        else:
            v = 'Skipped'
        res.append((i, c['slot'], cur, v))
    return res


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
            out.append(f'~ {path}: {json.dumps(a, ensure_ascii=False)[:300]} -> {json.dumps(b, ensure_ascii=False)[:300]}')
    return out


def load_persisted(path):
    """persisted MCP result: list of {type,text} blocks (or raw text); refuse truncated output"""
    raw = open(path).read()
    try:
        j = json.loads(raw)
    except Exception:
        j = None
    if isinstance(j, list) and j and isinstance(j[0], dict) and 'text' in j[0]:
        txt = ''.join(b['text'] for b in j if b.get('type') == 'text')
    else:
        txt = raw
    d = json.loads(txt)
    budget = (d.get('meta') or {}).get('mcp_output_budget') or {}
    assert not budget.get('truncated'), ('truncated MCP output', budget)
    assert 'MCP_OUTPUT_TRUNCATED' not in txt and 'more items truncated' not in txt, 'truncated MCP output'
    return d, txt


def records_from(d):
    inner = d['data']['data']
    if isinstance(inner, dict) and 'data' in inner and isinstance(inner['data'], list):
        return inner['data']
    return [inner]


# read-only / derived creative fields that are never sent on create
DERIVED = {'id', 'account_id', 'actor_id', 'object_type', 'status', 'effective_object_story_id',
           'effective_instagram_media_id', 'use_page_actor_override', 'instagram_user_id',
           'effective_authorization_category', 'call_to_action', 'call_to_action_type', 'body', 'title',
           'video_id', 'image_hash', 'link_url', 'object_url', 'thumbnail_url', 'image_url',
           'instagram_permalink_url', 'object_story_id'}
# creatable fields copied as read
KEEP = ['name', 'object_story_spec', 'asset_feed_spec', 'degrees_of_freedom_spec', 'creative_sourcing_spec',
        'media_sourcing_spec', 'format_transformation_spec', 'threads_user_id', 'authorization_category',
        'portrait_customizations', 'contextual_multi_ads', 'url_tags', 'source_instagram_media_id',
        'platform_customizations', 'link_destination_display_url', 'branded_content',
        'regional_regulation_disclaimer_spec', 'ad_disclaimer_spec', 'page_welcome_message',
        'product_set_id', 'template_url', 'template_url_spec', 'applink_treatment',
        'interactive_components_spec', 'categorization_criteria', 'destination_set_id',
        'facebook_branded_content', 'instagram_branded_content', 'dynamic_ad_voice', 'bundle_folder_id',
        'recommender_settings', 'link_og_id', 'place_page_set_id', 'playable_asset_id', 'image_crops',
        'omnichannel_link_spec', 'object_store_url', 'messenger_sponsored_message',
        'photo_album_source_object_story_id', 'source_facebook_post_id', 'object_id']


def unknown_fields(creative):
    return [k for k in creative if k not in DERIVED and k not in KEEP]


def build_payload(creative, ad_id):
    """exact copy of the creative's creatable fields with only the unit's slot(s) set to new"""
    u = unit(ad_id)
    unk = unknown_fields(creative)
    assert not unk, ('unhandled creative fields', unk)
    assert not creative.get('url_tags'), 'creative has url_tags - handle by hand'
    notes = []
    p = {}
    for k in KEEP:
        if k in creative and creative[k] is not None:
            p[k] = copy.deepcopy(creative[k])
    for k in ('object_id', 'source_instagram_media_id', 'source_facebook_post_id', 'photo_album_source_object_story_id'):
        assert k not in p, ('post-based creative - handle by hand', k)
    vd = (p.get('object_story_spec') or {}).get('video_data')
    if vd and vd.get('image_hash') and 'image_url' in vd:
        del vd['image_url']
        notes.append('video_data.image_url (derived from image_hash) not sent; image_hash sent')
    css = p.get('creative_sourcing_spec') or {}
    for sl in css.get('site_links_spec', []) or []:
        if sl.get('site_link_image_hash') and 'site_link_image_url' in sl:
            del sl['site_link_image_url']
            if 'site_link_image_url (derived from site_link_image_hash) not sent' not in notes:
                notes.append('site_link_image_url (derived from site_link_image_hash) not sent')
    for v in (p.get('asset_feed_spec') or {}).get('videos', []) or []:
        assert 'stp=' not in (v.get('thumbnail_url') or ''), 'resized thumbnail rendition in read - handle by hand'
    for c in u['changes']:
        old = get_slot(p, c['slot'])
        assert old == c['now'] or old in c['alt_now'], (c['slot'], old)
        set_slot(p, c['slot'], c['new'])
    return p, notes


def expected_after(creative, ad_id):
    e = copy.deepcopy(creative)
    for c in unit(ad_id)['changes']:
        set_slot(e, c['slot'], c['new'])
    return e


def progress(**kw):
    kw['ts'] = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    with open(PROG, 'a') as f:
        f.write(json.dumps(kw, ensure_ascii=False) + '\n')


def record(ad_id, idx, before, after_live, result, new_ids, detail):
    u = unit(ad_id)
    c = u['changes'][idx]
    if result == 'Fixed':
        assert after_live == c['new'], 'after_live != new'
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


def dumps_tool(o):
    """compact JSON: ASCII and Arabic letters kept literally; every other non-ASCII char escaped as \\uXXXX"""
    s = json.dumps(o, ensure_ascii=False, separators=(',', ':'))
    out = []
    for ch in s:
        n = ord(ch)
        if n < 128:
            out.append(ch)
        elif 0x0600 <= n <= 0x06FF and unicodedata.category(ch) in ('Lo', 'Mn', 'Po', 'Nd', 'Lm'):
            out.append(ch)
        else:
            out.append('\\u%04x' % n)
    return ''.join(out)


def nonascii_report(o):
    s = json.dumps(o, ensure_ascii=False)
    seen = {}
    for ch in s:
        if ord(ch) > 127:
            seen[ch] = seen.get(ch, 0) + 1
    return sorted(('U+%04X' % ord(c), unicodedata.category(c), unicodedata.name(c, '?'), n) for c, n in seen.items())
