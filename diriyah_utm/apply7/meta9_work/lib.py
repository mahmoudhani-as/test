import json, copy, re, sys, os
from urllib.parse import urlsplit, parse_qsl

ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
IN = ROOT + '/apply7/in_meta_9.json'
OUT = ROOT + '/apply7/out_meta_9.jsonl'
WORK = ROOT + '/apply7/meta9_work'
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


def classify(ad_id, creative):
    u = unit(ad_id)
    res = []
    for c in u['changes']:
        try:
            cur = get_slot(creative, c['slot'])
        except Exception:
            cur = None
        if cur is not None and same_url(cur, c['new']):
            v = 'AlreadyFixed'
        elif cur == c['now'] or cur in c['alt_now']:
            v = 'Write'
        else:
            v = 'Skipped'
        if excluded(ad_id, c['slot']):
            v = 'Excluded'
        res.append((c, cur, v))
    return res


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


def load_persisted(path):
    blocks = json.load(open(path))
    txt = ''.join(b['text'] for b in blocks if b.get('type') == 'text')
    return json.loads(txt)


def has_trunc(o):
    if isinstance(o, dict):
        return any('mcp_trunc' in k.lower() or k.lower().startswith('_trunc') for k in o) or any(has_trunc(v) for v in o.values())
    if isinstance(o, list):
        return any(has_trunc(v) for v in o)
    if isinstance(o, str):
        return 'MCP_OUTPUT_TRUNCATED' in o or 'more items truncated' in o or '[TRUNCATED' in o
    return False


DROP_TOP = {'id', 'account_id', 'actor_id', 'object_type', 'status', 'effective_object_story_id',
            'effective_instagram_media_id', 'use_page_actor_override', 'body', 'title', 'image_hash',
            'call_to_action', 'image_crops', 'instagram_user_id', 'video_id', 'object_story_id'}
KEEP_TOP = ['name', 'object_story_spec', 'asset_feed_spec', 'degrees_of_freedom_spec', 'contextual_multi_ads',
            'creative_sourcing_spec', 'media_sourcing_spec', 'threads_user_id', 'authorization_category',
            'portrait_customizations', 'url_tags', 'source_instagram_media_id', 'platform_customizations',
            'branded_content', 'ad_disclaimer_spec', 'regional_regulation_disclaimer_spec',
            'link_destination_display_url', 'page_welcome_message', 'applink_treatment',
            'interactive_components_spec', 'template_url', 'product_set_id', 'recommender_settings',
            'object_id', 'link_url', 'object_url']


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
    for ch in changes:
        old = get_slot(p, ch['slot'])
        assert old == ch['now'] or old in ch['alt_now'], (ch['slot'], old)
        set_slot(p, ch['slot'], ch['new'])
    return p


def dumps_tool(o):
    """compact JSON: ASCII and Arabic letters kept literally; every other non-ASCII char (punctuation like U+2019,
    zero-width/format chars, etc.) escaped as \\uXXXX so it can be reproduced exactly in a tool call"""
    s = json.dumps(o, ensure_ascii=False, separators=(',', ':'))
    out = []
    import unicodedata
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
    import unicodedata
    s = json.dumps(o, ensure_ascii=False)
    seen = {}
    for ch in s:
        if ord(ch) > 127:
            seen[ch] = seen.get(ch, 0) + 1
    return sorted(('U+%04X' % ord(c), unicodedata.category(c), unicodedata.name(c, '?'), n) for c, n in seen.items())


IGNORE_DERIVED = ('.creative.id', '.creative.name', '.creative.effective_object_story_id',
                  '.creative.effective_instagram_media_id', '.updated_time', '.effective_status',
                  '.creative.video_id', '.creative.status')


def verify_ad(old_ad, new_ad, changes):
    """compare new ad read-back with the old ad read; expect only the slot(s) (and derived fields) to change"""
    exp = copy.deepcopy(old_ad)
    for ch in changes:
        set_slot(exp['creative'], ch['slot'], ch['new'])
    # derived mirrors of the CTA link
    d = diff(exp, new_ad)
    keep = []
    for line in d:
        path = line[2:].split(' ')[0].rstrip(':')
        if path in IGNORE_DERIVED:
            continue
        if '.site_link_image_url' in path or path.endswith('.image_url') or path.endswith('.thumbnail_url'):
            continue  # signed CDN URLs regenerate on every read
        keep.append(line)
    return keep


def build_payload_afs(creative, changes):
    """build_payload + drop derived thumbnail_url from asset_feed_spec videos when thumbnail_hash is present"""
    p = build_payload(creative, changes)
    afs = p.get('asset_feed_spec')
    if afs:
        for v in afs.get('videos', []):
            if 'thumbnail_hash' in v:
                v.pop('thumbnail_url', None)
    return p
