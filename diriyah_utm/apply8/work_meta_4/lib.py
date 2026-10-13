"""helpers for apply8 in_meta_4 (read-only parsing, comparison and payload building; no API calls)"""
import json, copy, re, unicodedata
from urllib.parse import urlsplit, parse_qsl

ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
IN = ROOT + '/apply8/in_meta_4.json'
W = ROOT + '/apply8/work_meta_4/'
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
        elif cur is not None and (cur == c['now'] or cur in c['alt_now']):
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
        return json.loads(txt), txt
    return raw, json.dumps(raw)


def truncated(path):
    d, txt = load_persisted(path)
    flags = []
    for m in ('MCP_OUTPUT_TRUNCATED', '__mcp_truncated', 'more items truncated', '[TRUNCATED'):
        if m in txt:
            flags.append(m)
    mb = (d.get('data') or {}).get('meta') if isinstance(d.get('data'), dict) else None
    if isinstance(mb, dict) and (mb.get('mcp_output_budget') or {}).get('truncated'):
        flags.append('mcp_output_budget.truncated')
    mb2 = d.get('meta') or {}
    if isinstance(mb2, dict) and (mb2.get('mcp_output_budget') or {}).get('truncated'):
        flags.append('meta.mcp_output_budget.truncated')
    return flags


def ads_from(path):
    d, _ = load_persisted(path)
    inner = d['data']['data']
    if isinstance(inner, dict) and 'data' in inner and isinstance(inner['data'], list):
        return inner['data']
    return [inner]


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
        if a != b or type(a) != type(b):
            out.append(f'~ {path}: {json.dumps(a, ensure_ascii=False)[:250]} -> {json.dumps(b, ensure_ascii=False)[:250]}')
    return out


# derived / read-only top-level fields that are not sent on create
DROP_TOP = {'id', 'account_id', 'actor_id', 'object_type', 'status', 'effective_object_story_id',
            'effective_instagram_media_id', 'use_page_actor_override', 'body', 'title', 'image_hash',
            'call_to_action', 'call_to_action_type', 'image_crops', 'video_id',
            'object_story_id', 'effective_authorization_category', 'thumbnail_id', 'link_url', 'object_id',
            'object_url', 'instagram_permalink_url', 'image_url'}
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
    return [k for k in creative if k not in DROP_TOP and k not in KEEP_TOP and k != 'instagram_user_id']


def nonascii_report(o):
    s = json.dumps(o, ensure_ascii=False)
    seen = {}
    for ch in s:
        if ord(ch) > 127:
            seen[ch] = seen.get(ch, 0) + 1
    return sorted(('U+%04X' % ord(c), unicodedata.category(c), unicodedata.name(c, '?'), n) for c, n in seen.items())


def build_payload(creative, changes):
    """exact copy of the creative's creatable fields, with only the listed slot(s) set to new.
    top-level instagram_user_id is copied only when object_story_spec has none (proven 12-Oct, apply6 meta_2)."""
    unk = unknown_fields(creative)
    assert not unk, ('unhandled creative fields', unk)
    assert not creative.get('url_tags'), 'creative has url_tags - handle by hand'
    notes = []
    p = {}
    for k in KEEP_TOP:
        if k in creative and creative[k] is not None:
            p[k] = copy.deepcopy(creative[k])
    osp = p.get('object_story_spec') or {}
    if creative.get('instagram_user_id') and 'instagram_user_id' not in osp:
        p['instagram_user_id'] = creative['instagram_user_id']
        notes.append('top-level instagram_user_id copied as read (object_story_spec has page_id only)')
    elif creative.get('instagram_user_id'):
        assert osp.get('instagram_user_id') == creative['instagram_user_id'], 'IG id mismatch top vs osp'
    cfs = (p.get('degrees_of_freedom_spec') or {}).get('creative_features_spec', {})
    if 'standard_enhancements' in cfs:
        raise AssertionError('deprecated standard_enhancements present - handle by hand')
    vd = osp.get('video_data')
    if vd and vd.get('image_hash') and 'image_url' in vd:
        del vd['image_url']
        notes.append('video_data.image_url (derived from image_hash) not sent; image_hash sent')
    for ch in changes:
        old = get_slot(p, ch['slot'])
        assert old == ch['now'] or old in ch['alt_now'], (ch['slot'], old)
        set_slot(p, ch['slot'], ch['new'])
    return p, notes
