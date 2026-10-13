import json, copy, re, os, unicodedata
from urllib.parse import urlsplit, parse_qsl

ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
IN = ROOT + '/apply7/in_meta_10.json'
OUT = ROOT + '/apply7/out_meta_10.jsonl'
W = ROOT + '/apply7/meta10_work/'
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
    """same scheme/host/path/fragment and the same query params in any order"""
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
    """landing URL = slot value + url_tags (if any)"""
    try:
        base = get_slot(creative, slot)
    except Exception:
        return None
    tags = creative.get('url_tags')
    if tags and base is not None:
        return base + ('&' if '?' in base else '?') + tags
    return base


def classify(ad_id, creative):
    u = unit(ad_id)
    res = []
    for c in u['changes']:
        cur = full_url(creative, c['slot'])
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


def load_persisted(path):
    """MCP output saved by the harness: list of {type,text} blocks, or the raw JSON"""
    raw = json.load(open(path))
    if isinstance(raw, list):
        txt = ''.join(b['text'] for b in raw if b.get('type') == 'text')
        return json.loads(txt)
    return raw


def ads_from(path):
    d = load_persisted(path)
    inner = d['data']['data']
    if isinstance(inner, dict) and 'data' in inner:
        return inner['data']
    return [inner]


def has_trunc(o):
    if isinstance(o, dict):
        return any('mcp_trunc' in k.lower() or k.lower().startswith('_trunc') for k in o) or any(has_trunc(v) for v in o.values())
    if isinstance(o, list):
        return any(has_trunc(v) for v in o)
    if isinstance(o, str):
        return 'MCP_OUTPUT_TRUNCATED' in o or 'more items truncated' in o or '[TRUNCATED' in o
    return False


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


# derived / read-only top-level fields that are not sent on create
DROP_TOP = {'id', 'account_id', 'actor_id', 'object_type', 'status', 'effective_object_story_id',
            'effective_instagram_media_id', 'use_page_actor_override', 'body', 'title', 'image_hash',
            'call_to_action', 'call_to_action_type', 'image_crops', 'instagram_user_id', 'video_id',
            'object_story_id', 'effective_authorization_category', 'thumbnail_id', 'link_url', 'object_id',
            'object_url', 'instagram_permalink_url'}
KEEP_TOP = ['name', 'object_story_spec', 'asset_feed_spec', 'degrees_of_freedom_spec', 'contextual_multi_ads',
            'creative_sourcing_spec', 'media_sourcing_spec', 'format_transformation_spec', 'threads_user_id',
            'authorization_category', 'portrait_customizations', 'url_tags', 'source_instagram_media_id',
            'platform_customizations', 'branded_content', 'ad_disclaimer_spec', 'regional_regulation_disclaimer_spec',
            'link_destination_display_url', 'page_welcome_message', 'applink_treatment',
            'interactive_components_spec', 'template_url', 'template_url_spec', 'product_set_id',
            'recommender_settings', 'facebook_branded_content', 'instagram_branded_content', 'bundle_folder_id',
            'categorization_criteria', 'place_page_set_id', 'destination_set_id', 'dynamic_ad_voice',
            'playable_asset_id', 'link_og_id']


def unknown_fields(creative):
    return [k for k in creative if k not in DROP_TOP and k not in KEEP_TOP]


def dumps_tool(o):
    """compact JSON: ASCII and Arabic letters kept literally; every other non-ASCII char escaped as \\uXXXX"""
    s = json.dumps(o, ensure_ascii=False, separators=(',', ':'))
    out = []
    for ch in s:
        o_ = ord(ch)
        if o_ < 128:
            out.append(ch)
        elif 0x0600 <= o_ <= 0x06FF and unicodedata.category(ch) in ('Lo', 'Mn', 'Po', 'Nd', 'Lm'):
            out.append(ch)
        else:
            out.append('\\u%04x' % o_)
    return ''.join(out)


def nonascii_report(o):
    s = json.dumps(o, ensure_ascii=False)
    seen = {}
    for ch in s:
        if ord(ch) > 127:
            seen[ch] = seen.get(ch, 0) + 1
    return sorted(('U+%04X' % ord(c), unicodedata.category(c), unicodedata.name(c, '?'), n) for c, n in seen.items())


def build_payload(creative, changes):
    """exact copy of the creative's creatable fields, with only the listed slot(s) set to new"""
    unk = unknown_fields(creative)
    assert not unk, ('unhandled creative fields', unk)
    assert not creative.get('url_tags'), 'creative has url_tags - handle by hand'
    notes = []
    p = {}
    for k in KEEP_TOP:
        if k in creative and creative[k] is not None:
            p[k] = copy.deepcopy(creative[k])
    cfs = (p.get('degrees_of_freedom_spec') or {}).get('creative_features_spec', {})
    assert 'standard_enhancements' not in cfs, 'deprecated standard_enhancements present - handle by hand'
    vd = (p.get('object_story_spec') or {}).get('video_data')
    if vd and vd.get('image_hash') and 'image_url' in vd:
        del vd['image_url']
        notes.append('video_data.image_url (derived from image_hash) not sent; image_hash sent')
    for v in (p.get('asset_feed_spec') or {}).get('videos', []) or []:
        assert 'stp=' not in v.get('thumbnail_url', ''), 'resized thumbnail rendition in read - handle by hand'
    for ch in changes:
        old = get_slot(p, ch['slot'])
        assert old == ch['now'] or old in ch['alt_now'], (ch['slot'], old)
        set_slot(p, ch['slot'], ch['new'])
    return p, notes


def expected_after(payload_or_creative, changes):
    e = copy.deepcopy(payload_or_creative)
    for ch in changes:
        set_slot(e, ch['slot'], ch['new'])
    return e
