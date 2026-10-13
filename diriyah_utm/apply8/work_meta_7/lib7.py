import json, copy, re, os, sys, unicodedata
from urllib.parse import urlsplit, parse_qsl

ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
IN = ROOT + '/apply8/in_meta_7.json'
W = ROOT + '/apply8/work_meta_7/'
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
    raw = json.load(open(path))
    if isinstance(raw, list):
        txt = ''.join(b['text'] for b in raw if b.get('type') == 'text')
        return json.loads(txt)
    return raw


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


DROP_TOP = {'id', 'account_id', 'actor_id', 'object_type', 'status', 'effective_object_story_id',
            'effective_instagram_media_id', 'use_page_actor_override', 'body', 'title', 'image_hash',
            'call_to_action_type', 'image_crops', 'instagram_user_id', 'video_id',
            'object_story_id', 'effective_authorization_category', 'thumbnail_id', 'link_url', 'object_id',
            'object_url', 'instagram_permalink_url', 'thumbnail_url', 'image_url'}
KEEP_TOP = ['name', 'object_story_spec', 'asset_feed_spec', 'degrees_of_freedom_spec', 'contextual_multi_ads',
            'creative_sourcing_spec', 'media_sourcing_spec', 'format_transformation_spec', 'threads_user_id',
            'authorization_category', 'portrait_customizations', 'url_tags', 'source_instagram_media_id',
            'platform_customizations', 'branded_content', 'ad_disclaimer_spec', 'regional_regulation_disclaimer_spec',
            'link_destination_display_url', 'page_welcome_message', 'applink_treatment',
            'interactive_components_spec', 'template_url', 'template_url_spec', 'product_set_id',
            'recommender_settings', 'facebook_branded_content', 'instagram_branded_content', 'bundle_folder_id',
            'categorization_criteria', 'place_page_set_id', 'destination_set_id', 'dynamic_ad_voice',
            'playable_asset_id', 'link_og_id', 'call_to_action']


def unknown_fields(creative):
    return [k for k in creative if k not in DROP_TOP and k not in KEEP_TOP]


def dumps_tool(o):
    return json.dumps(o, ensure_ascii=False, separators=(',', ':'))


def nonascii_report(o):
    s = json.dumps(o, ensure_ascii=False)
    seen = {}
    for ch in s:
        if ord(ch) > 127:
            seen[ch] = seen.get(ch, 0) + 1
    return sorted(('U+%04X' % ord(c), unicodedata.category(c), unicodedata.name(c, '?'), n) for c, n in seen.items()
                  if not (0x0600 <= ord(c) <= 0x06FF))


def expected_after(obj, changes):
    e = copy.deepcopy(obj)
    for ch in changes:
        set_slot(e, ch['slot'], ch['new'])
    return e


def build_payload(creative, changes):
    unk = unknown_fields(creative)
    assert not unk, ('unhandled creative fields', unk)
    assert not creative.get('url_tags'), 'creative has url_tags - handle by hand'
    notes = []
    p = {}
    for k in KEEP_TOP:
        if k in creative and creative[k] is not None:
            p[k] = copy.deepcopy(creative[k])
    if 'call_to_action' in p and not p.get('source_instagram_media_id'):
        del p['call_to_action']
        notes.append('top-level call_to_action (derived) not sent')
    cfs = (p.get('degrees_of_freedom_spec') or {}).get('creative_features_spec', {})
    if 'standard_enhancements' in cfs:
        del cfs['standard_enhancements']
        notes.append('deprecated standard_enhancements key not sent')
        if not cfs:
            del p['degrees_of_freedom_spec']
    for ch in changes:
        old = get_slot({'x': 1, **p} if False else p, ch['slot'].replace('creative.', 'creative.', 1)) if False else None
    for ch in changes:
        old = get_slot(p, ch['slot'])
        assert old == ch['now'] or old in ch['alt_now'], (ch['slot'], old)
        set_slot(p, ch['slot'], ch['new'])
    return p, notes


def dumps_tool(o):
    """compact JSON; ASCII and Arabic letters literal; any other non-ASCII char escaped as \\uXXXX"""
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


def build_payload2(creative, changes):
    p, notes = build_payload(creative, changes)
    css = p.get('creative_sourcing_spec') or {}
    for sl in css.get('site_links_spec', []) or []:
        if 'site_link_image_url' in sl and sl.get('site_link_image_hash'):
            del sl['site_link_image_url']
            if 'derived site_link_image_url not sent (image_hash sent)' not in notes:
                notes.append('derived site_link_image_url not sent (image_hash sent)')
    return p, notes


def ascii_payload(p):
    s = json.dumps(p, ensure_ascii=True, separators=(', ', ': '))
    assert json.loads(s) == p
    return s
