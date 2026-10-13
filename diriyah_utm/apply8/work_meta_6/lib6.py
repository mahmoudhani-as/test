import json, copy, re
from urllib.parse import urlsplit, parse_qsl

ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
IN = ROOT + '/apply8/in_meta_6.json'
W = ROOT + '/apply8/work_meta_6/'
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


def load_persisted(path):
    blocks = json.load(open(path))
    txt = ''.join(b['text'] for b in blocks if b.get('type') == 'text')
    return txt, json.loads(txt)


def trunc_markers(txt):
    return [m for m in ('__mcp_truncated_keys', 'MCP_OUTPUT_TRUNCATED', 'more items truncated') if m in txt]


def ads_from(path):
    txt, d = load_persisted(path)
    bad = trunc_markers(txt)
    assert not bad, ('truncated read', path, bad)
    assert d['success'] and d['data']['success'], 'read not successful'
    items = d['data']['data']['data']
    assert all(isinstance(a, dict) for a in items)
    return {a['id']: a for a in items}


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


def classify(u, creative):
    res = []
    for c in u['changes']:
        try:
            cur = full_url(creative, c['slot'])
        except Exception:
            cur = None
        if cur is not None and same_url(cur, c['new']):
            v = 'AlreadyFixed'
        elif cur == c['now'] or cur in c['alt_now']:
            v = 'Write'
        else:
            v = 'Skipped'
        res.append((c, cur, v))
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
        if a != b:
            out.append(f'~ {path}: {json.dumps(a, ensure_ascii=False)[:300]} -> {json.dumps(b, ensure_ascii=False)[:300]}')
    return out


# read-only / derived top-level creative fields that are not sent on create
DROP_TOP = {'id', 'account_id', 'actor_id', 'object_type', 'status', 'effective_object_story_id',
            'effective_instagram_media_id', 'use_page_actor_override', 'instagram_user_id',
            'effective_authorization_category', 'enable_direct_install', 'enable_launch_instant_app',
            'instagram_permalink_url', 'thumbnail_id'}
# fields copied as read
KEEP_TOP = ['name', 'object_story_spec', 'asset_feed_spec', 'degrees_of_freedom_spec', 'creative_sourcing_spec',
            'threads_user_id', 'contextual_multi_ads', 'authorization_category', 'url_tags',
            'source_instagram_media_id', 'platform_customizations', 'portrait_customizations', 'branded_content',
            'link_destination_display_url', 'applink_treatment', 'interactive_components_spec', 'product_set_id']


def merged_creative(nodof_ad, dof_creative):
    """creative from the no-DOF read plus the DOF spec of the same creative id from the DOF-only read"""
    c = copy.deepcopy(nodof_ad['creative'])
    assert 'degrees_of_freedom_spec' not in c
    assert dof_creative['id'] == c['id']
    c['degrees_of_freedom_spec'] = copy.deepcopy(dof_creative['degrees_of_freedom_spec'])
    return c


def build_payload(creative, changes):
    unknown = [k for k in creative if k not in DROP_TOP and k not in KEEP_TOP]
    assert not unknown, ('unhandled creative fields', unknown)
    assert not creative.get('url_tags'), 'creative has url_tags - handle by hand'
    p = {}
    for k in KEEP_TOP:
        if k in creative:
            p[k] = copy.deepcopy(creative[k])
    for ch in changes:
        old = get_slot(p, ch['slot'])
        assert old == ch['now'] or old in ch['alt_now'], (ch['slot'], old)
        set_slot(p, ch['slot'], ch['new'])
    return p


IGNORE_DERIVED = {'.id', '.effective_object_story_id', '.effective_instagram_media_id',
                  '.instagram_permalink_url', '.thumbnail_id', '.status'}


def compare_creatives(old, new, changes):
    """expected: new == old with only the slot(s) changed (+ derived ids; name suffix reported separately)."""
    exp = copy.deepcopy(old)
    for ch in changes:
        set_slot(exp, ch['slot'], ch['new'])
    out = []
    for line in diff(exp, new):
        path = line[2:].split(' ')[0].rstrip(':')
        if path in IGNORE_DERIVED:
            continue
        out.append(line)
    return out
