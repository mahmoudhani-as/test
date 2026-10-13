import json, copy, re, unicodedata
from urllib.parse import urlsplit, parse_qsl

ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
IN = ROOT + '/apply8/in_meta_8.json'
W = ROOT + '/apply8/work_meta_8/'
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


def load_persisted(path):
    raw = json.load(open(path))
    if isinstance(raw, list):
        txt = ''.join(b['text'] for b in raw if b.get('type') == 'text')
    else:
        txt = json.dumps(raw)
    return json.loads(txt), txt


def check_trunc(txt):
    bad = [m for m in ('MCP_OUTPUT_TRUNCATED', 'more items truncated', '__mcp_truncated', '"truncated": true') if m in txt]
    return bad


def records(d):
    inner = d['data']['data']
    if isinstance(inner, dict) and 'data' in inner and isinstance(inner['data'], list):
        return inner['data']
    return [inner]


def classify(ad):
    """per change: (change, cur, verdict)"""
    u = unit(ad['id'])
    c = ad['creative']
    res = []
    for ch in u['changes']:
        cur = full_url(c, ch['slot'])
        if excluded(ad['id'], ch['slot']):
            v = 'Excluded'
        elif ad.get('effective_status') == 'ARCHIVED' or ad.get('status') == 'ARCHIVED':
            v = 'Archived'
        elif cur is not None and same_url(cur, ch['new']):
            v = 'AlreadyFixed'
        elif cur is not None and (cur == ch['now'] or cur in ch.get('alt_now', [])):
            v = 'Write'
        else:
            v = 'Skipped'
        res.append((ch, cur, v))
    return res


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


# read-only / derived creative fields (never sent on create)
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
        'object_id']


def unknown_fields(creative):
    return [k for k in creative if k not in DERIVED and k not in KEEP]


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


TRANSCRIPT = '/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/wf_b623ea88-16c/agent-a2d5924d030f47d5c.jsonl'


def transcript_results(substr):
    """exact text of this agent's inline tool results that contain substr (oldest first)"""
    out = []
    for line in open(TRANSCRIPT, encoding='utf-8'):
        try:
            m = json.loads(line)
        except Exception:
            continue
        msg = m.get('message') or {}
        content = msg.get('content')
        if not isinstance(content, list):
            continue
        for part in content:
            if isinstance(part, dict) and part.get('type') == 'tool_result':
                c = part.get('content')
                if isinstance(c, list):
                    txt = ''.join(x.get('text', '') for x in c if isinstance(x, dict))
                else:
                    txt = c if isinstance(c, str) else ''
                if substr in txt:
                    out.append(txt)
    return out


def nonascii_report(o):
    s = json.dumps(o, ensure_ascii=False)
    seen = {}
    for ch in s:
        if ord(ch) > 127:
            seen[ch] = seen.get(ch, 0) + 1
    return sorted(('U+%04X' % ord(c), unicodedata.category(c), unicodedata.name(c, '?'), n) for c, n in seen.items()
                  if not (0x0600 <= ord(c) <= 0x06FF and unicodedata.category(c) in ('Lo', 'Mn', 'Po', 'Nd', 'Lm')))


def canon(creative):
    """order-insensitive view of label-referenced asset_feed_spec lists (Meta may reorder them)"""
    c = copy.deepcopy(creative)
    afs = c.get('asset_feed_spec')
    if isinstance(afs, dict):
        for k in ('images', 'videos', 'bodies', 'titles', 'descriptions', 'link_urls', 'carousels'):
            if isinstance(afs.get(k), list):
                afs[k] = sorted(afs[k], key=lambda x: json.dumps(x, sort_keys=True, ensure_ascii=False))
        if isinstance(afs.get('asset_customization_rules'), list):
            afs['asset_customization_rules'] = sorted(afs['asset_customization_rules'], key=lambda x: x.get('priority', 0))
    return c


def check_new_creative(ad_id, new_cr_text, ignore=()):
    """diff expected (live pre-read creative with the unit's slots set to new) vs a new creative read"""
    pre = json.load(open(W + 'pre_%s.json' % ad_id))['creative']
    exp = copy.deepcopy(pre)
    for ch in unit(ad_id)['changes']:
        set_slot(exp, ch['slot'], ch['new'])
    if exp.get('creative_sourcing_spec'):
        for sl in exp['creative_sourcing_spec'].get('site_links_spec', []) or []:
            sl.pop('site_link_image_url', None)
    got = copy.deepcopy(new_cr_text)
    if got.get('creative_sourcing_spec'):
        for sl in got['creative_sourcing_spec'].get('site_links_spec', []) or []:
            sl.pop('site_link_image_url', None)
    exp_c, got_c = canon(exp), canon(got)
    exp_c = {k: v for k, v in exp_c.items() if k in got_c or k in KEEP}
    dd = diff(exp_c, got_c)
    meta_set = ('.id:', '.name:', '.effective_object_story_id', '.effective_instagram_media_id', '.status:')
    feats = [x for x in dd if x.startswith('+ .degrees_of_freedom_spec.creative_features_spec.')]
    feats_ok = all(x.endswith('{"enroll_status": "OPT_OUT"}') for x in feats)
    rest = [x for x in dd if x not in feats and not any(x.startswith('~ ' + m) or x.startswith('~ ' + m.rstrip(':')) for m in meta_set)
            and not any(i in x for i in ignore)]
    return feats, feats_ok, rest, dd
