import json, copy, re
from urllib.parse import urlsplit, parse_qsl

ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
IN = ROOT + '/apply8/in_meta_1.json'
W = ROOT + '/apply8/work_meta_1/'
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


def load_persisted(path):
    blocks = json.load(open(path))
    txt = ''.join(b['text'] for b in blocks if b.get('type') == 'text')
    return json.loads(txt)


def find_trunc(o, path=''):
    out = []
    if isinstance(o, dict):
        for k, v in o.items():
            if 'trunc' in k.lower():
                out.append((path + '.' + k, str(v)[:200]))
            out += find_trunc(v, path + '.' + k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            out += find_trunc(v, f'{path}[{i}]')
    elif isinstance(o, str):
        if 'TRUNCATED' in o or 'more items truncated' in o:
            out.append((path, o[:200]))
    return out


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
        if excluded(u['unit'], c['slot']):
            v = 'Excluded'
        elif cur is not None and same_url(cur, c['new']):
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


# derived / read-only top-level fields that are not sent on create
DROP_TOP = {'id', 'account_id', 'actor_id', 'object_type', 'status', 'effective_object_story_id',
            'effective_instagram_media_id', 'use_page_actor_override', 'body', 'title', 'image_hash',
            'call_to_action', 'call_to_action_type', 'instagram_user_id', 'video_id',
            'object_story_id', 'effective_authorization_category', 'instagram_permalink_url', 'thumbnail_id'}
KEEP_TOP = ['name', 'object_story_spec', 'asset_feed_spec', 'degrees_of_freedom_spec', 'contextual_multi_ads',
            'creative_sourcing_spec', 'media_sourcing_spec', 'format_transformation_spec', 'threads_user_id',
            'authorization_category', 'portrait_customizations', 'url_tags', 'source_instagram_media_id',
            'platform_customizations', 'branded_content', 'ad_disclaimer_spec', 'regional_regulation_disclaimer_spec',
            'link_destination_display_url', 'page_welcome_message', 'applink_treatment',
            'interactive_components_spec', 'template_url', 'product_set_id', 'recommender_settings',
            'facebook_branded_content', 'instagram_branded_content', 'bundle_folder_id',
            'categorization_criteria', 'place_page_set_id', 'object_id', 'link_url', 'object_url', 'image_crops']


def build_payload(creative, changes):
    unknown = [k for k in creative if k not in DROP_TOP and k not in KEEP_TOP]
    assert not unknown, ('unhandled creative fields', unknown)
    assert not creative.get('url_tags'), 'creative has url_tags - handle by hand'
    dof = creative.get('degrees_of_freedom_spec', {}).get('creative_features_spec', {})
    assert 'standard_enhancements' not in dof, 'standard_enhancements present - handle by hand'
    p = {}
    for k in KEEP_TOP:
        if k in creative:
            p[k] = copy.deepcopy(creative[k])
    view = {'object_story_spec': p.get('object_story_spec'), 'asset_feed_spec': p.get('asset_feed_spec')}
    for ch in changes:
        old = get_slot(view, ch['slot'])
        assert old == ch['now'] or old in ch['alt_now'], (ch['slot'], old)
        set_slot(view, ch['slot'], ch['new'])
    return p


def ad_from_reads(ad_id, files):
    for f in files:
        d = load_persisted(f)
        for a in d['data']['data']['data']:
            if isinstance(a, dict) and a.get('id') == ad_id:
                return a
    return None
