"""Helpers for apply10 in_meta_1: local parsing of this agent's own Whathead tool results (never calls an API)."""
import json, copy, re
from urllib.parse import urlsplit, parse_qsl

ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
IN = ROOT + '/apply10/in_meta_1.json'
W = ROOT + '/apply10/work_meta_1/'
EXCL = ROOT + '/work/excl_platform_refused_v2.json'
TRANSCRIPT = ('/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/'
              'wf_8287eab6-a70/agent-a600e5cd6fa5e513b.jsonl')

SEND_KEYS = ['name', 'object_story_spec', 'asset_feed_spec', 'degrees_of_freedom_spec', 'contextual_multi_ads',
             'creative_sourcing_spec', 'media_sourcing_spec', 'format_transformation_spec', 'threads_user_id',
             'authorization_category', 'portrait_customizations', 'url_tags', 'source_instagram_media_id',
             'platform_customizations', 'branded_content', 'ad_disclaimer_spec',
             'regional_regulation_disclaimer_spec', 'link_destination_display_url', 'page_welcome_message',
             'applink_treatment', 'interactive_components_spec', 'template_url', 'template_url_spec',
             'product_set_id', 'recommender_settings', 'facebook_branded_content', 'instagram_branded_content',
             'bundle_folder_id', 'categorization_criteria', 'place_page_set_id', 'destination_set_id',
             'dynamic_ad_voice', 'playable_asset_id', 'link_og_id']
DERIVED = {'id', 'account_id', 'actor_id', 'object_type', 'status', 'effective_object_story_id',
           'effective_instagram_media_id', 'use_page_actor_override', 'body', 'title', 'image_hash',
           'call_to_action', 'image_crops', 'instagram_user_id', 'video_id', 'call_to_action_type',
           'effective_authorization_category', 'link_url', 'object_url', 'object_id', 'object_story_id',
           'thumbnail_id', 'thumbnail_url', 'instagram_permalink_url', 'enable_direct_install',
           'enable_launch_instant_app', 'image_url'}


def units():
    return json.load(open(IN))


def unit(ad_id):
    for u in units():
        if u['unit'] == str(ad_id):
            return u
    raise KeyError(ad_id)


def excluded(ad_id, slot):
    return any(str(x.get('ad_id')) == str(ad_id) and x.get('slot') == slot for x in json.load(open(EXCL)))


# ---------------------------------------------------------------- own transcript: exact tool inputs/results
def _result_text(cc):
    if isinstance(cc, list):
        return ''.join(x.get('text', '') for x in cc if isinstance(x, dict) and x.get('type') == 'text')
    if isinstance(cc, str):
        return cc
    return json.dumps(cc)


def calls():
    uses, order, results = {}, [], {}
    for line in open(TRANSCRIPT):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        c = (r.get('message') or {}).get('content')
        if not isinstance(c, list):
            continue
        for b in c:
            if not isinstance(b, dict):
                continue
            if b.get('type') == 'tool_use':
                if b['id'] not in uses:
                    order.append(b['id'])
                uses[b['id']] = (b['name'], b.get('input') or {})
            elif b.get('type') == 'tool_result':
                results[b['tool_use_id']] = _result_text(b.get('content'))
    return [(i, uses[i][0], uses[i][1], results.get(i)) for i in order]


def whathead_calls():
    return [c for c in calls() if 'Whathed' in c[1]]


def parse_result(txt):
    if txt is None:
        return None
    t = txt.strip()
    try:
        return json.loads(t)
    except Exception:
        pass
    m = re.search(r'(/root/\.claude/projects/\S+?\.(?:txt|json))', t)
    if m:
        raw = open(m.group(1)).read()
        try:
            d = json.loads(raw)
        except Exception:
            return {'_unparsed': raw[:500], '_file': m.group(1)}
        if isinstance(d, list) and d and isinstance(d[0], dict) and 'text' in d[0]:
            return json.loads(''.join(x.get('text', '') for x in d))
        return d
    return {'_unparsed': t[:800]}


def find_calls(action, pred=None):
    out = []
    for cid, name, inp, res in whathead_calls():
        if inp.get('action') == action and (pred is None or pred(inp)):
            out.append((cid, inp, res))
    return out


def last_call(action, pred=None):
    x = find_calls(action, pred)
    return x[-1] if x else None


TRUNC_MARKS = ('MCP_OUTPUT_TRUNCATED', 'more items truncated', '[TRUNCATED', 'mcp_output_budget')


def has_trunc(o):
    s = json.dumps(o, ensure_ascii=False)
    return any(m in s for m in TRUNC_MARKS) or '"truncated": true' in s or '"_truncated"' in s


def data_of(res_text):
    d = parse_result(res_text)
    assert isinstance(d, dict), d
    assert not has_trunc(d), 'truncated read'
    assert d.get('success') and d['data'].get('success'), json.dumps(d, ensure_ascii=False)[:1200]
    return d['data']['data']


def last_ad_read(ad_id):
    hit = last_call('meta_ad_id_get', lambda i: str((i.get('path_params') or {}).get('ad_id')) == str(ad_id))
    assert hit, ('no ad read for', ad_id)
    return data_of(hit[2])


def last_creative_read(cid):
    hit = last_call('meta_creative_id_get', lambda i: str((i.get('path_params') or {}).get('creative_id')) == str(cid))
    assert hit, ('no creative read for', cid)
    return data_of(hit[2])


# ---------------------------------------------------------------- slots / urls
def same_url(a, b):
    if not isinstance(a, str) or not isinstance(b, str):
        return False
    A, B = urlsplit(a), urlsplit(b)
    return (A.scheme, A.netloc, A.path, A.fragment) == (B.scheme, B.netloc, B.path, B.fragment) and \
        sorted(parse_qsl(A.query, keep_blank_values=True)) == sorted(parse_qsl(B.query, keep_blank_values=True))


def _parts(slot):
    assert slot.startswith('creative.')
    return slot[len('creative.'):].split('.')


def get_slot(creative, slot):
    cur = creative
    for part in _parts(slot):
        m = re.fullmatch(r'(\w+)\[(\d+)\]', part)
        if m:
            cur = cur[m.group(1)][int(m.group(2))]
        else:
            cur = cur[part]
    return cur


def set_slot(creative, slot, value):
    parts = _parts(slot)
    cur = creative
    for part in parts[:-1]:
        m = re.fullmatch(r'(\w+)\[(\d+)\]', part)
        if m:
            cur = cur[m.group(1)][int(m.group(2))]
        else:
            cur = cur[part]
    last = parts[-1]
    m = re.fullmatch(r'(\w+)\[(\d+)\]', last)
    if m:
        cur[m.group(1)][int(m.group(2))] = value
    else:
        assert last in cur, (slot, 'missing leaf')
        cur[last] = value


def classify(u, creative):
    res = []
    for c in u['changes']:
        try:
            cur = get_slot(creative, c['slot'])
        except Exception:
            cur = None
        if cur is not None and same_url(cur, c['new']):
            v = 'AlreadyFixed'
        elif cur is not None and (cur == c['now'] or cur in (c.get('alt_now') or [])):
            v = 'Write'
        else:
            v = 'Skipped'
        res.append((c, cur, v))
    return res


def all_urls(o, path=''):
    out = []
    if isinstance(o, dict):
        for k, v in o.items():
            out += all_urls(v, f'{path}.{k}')
    elif isinstance(o, list):
        for i, v in enumerate(o):
            out += all_urls(v, f'{path}[{i}]')
    elif isinstance(o, str) and o.startswith('http'):
        out.append((path, o))
    return out


def diff(a, b, path=''):
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append(f'+ {path}.{k} = {json.dumps(b[k], ensure_ascii=False)[:220]}')
            elif k not in b:
                out.append(f'- {path}.{k} = {json.dumps(a[k], ensure_ascii=False)[:220]}')
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


# ---------------------------------------------------------------- payload
def build_payload(creative, changes):
    """exact copy of the creative's creatable fields as read, with only the listed slot(s) set to new.
    deprecated degrees_of_freedom_spec.creative_features_spec.standard_enhancements (Meta rejects it on create)
    is dropped only when it is plain OPT_OUT; any other value -> AssertionError (do not write)."""
    notes = []
    unknown = [k for k in creative if k not in SEND_KEYS and k not in DERIVED]
    assert not unknown, ('unhandled creative fields', unknown)
    assert not creative.get('source_instagram_media_id'), 'boosted IG post: not handled by this builder'
    p = {}
    for k in SEND_KEYS:
        if k in creative and creative[k] is not None:
            p[k] = copy.deepcopy(creative[k])
    dof = (p.get('degrees_of_freedom_spec') or {}).get('creative_features_spec')
    if dof and 'standard_enhancements' in dof:
        se = dof['standard_enhancements']
        assert se == {'enroll_status': 'OPT_OUT'}, ('standard_enhancements not plain OPT_OUT', se)
        notes.append('deprecated standard_enhancements OPT_OUT not sent')
        dof.pop('standard_enhancements')
    for ch in changes:
        old = get_slot(p, ch['slot'])
        assert old == ch['now'] or old in (ch.get('alt_now') or []), (ch['slot'], old)
        set_slot(p, ch['slot'], ch['new'])
    for path, url in all_urls(p):
        if 'utm_' in url or 'fbclid' in url:
            assert any(url == ch['new'] for ch in changes), ('other UTM url in payload', path, url)
    if p.get('url_tags'):
        notes.append('url_tags present: %s' % p['url_tags'])
    return p, notes


def norm(o):
    if isinstance(o, dict):
        return {k: norm(v) for k, v in o.items()}
    if isinstance(o, list):
        items = [norm(v) for v in o]
        return sorted(items, key=lambda x: json.dumps(x, sort_keys=True, ensure_ascii=False))
    return o


SANITY_SKIP = {'id', 'name', 'status', 'effective_object_story_id', 'effective_instagram_media_id',
               'instagram_permalink_url'}


def sanity(orig, new, changes, extra_skip=()):
    exp = copy.deepcopy(orig)
    for c in changes:
        set_slot(exp, c['slot'], c['new'])
    skip = SANITY_SKIP | set(extra_skip)
    a = norm({k: v for k, v in exp.items() if k not in skip})
    b = norm({k: v for k, v in new.items() if k not in skip})
    d = diff(a, b)
    return {'n_diff': len(d), 'diff': d, 'name_orig': orig.get('name'), 'name_new': new.get('name'),
            'name_kept_as_prefix': (new.get('name') or '').startswith(orig.get('name') or '\x00')}
