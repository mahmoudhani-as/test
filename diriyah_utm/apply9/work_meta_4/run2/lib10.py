"""helpers for apply9 in_meta_4 (second run). Reads this agent's own transcript for exact tool inputs/results."""
import json, copy, re
from urllib.parse import urlsplit, parse_qsl

ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
IN = ROOT + '/apply9/in_meta_4.json'
W = ROOT + '/apply9/work_meta_4/run2/'
EXCL = ROOT + '/work/excl_platform_refused_v2.json'
TRANSCRIPT = ('/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/'
              'wf_f76d0421-984/agent-a2705c54a46a64bf3.jsonl')
PREV_TRANSCRIPT = ('/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/'
                   'wf_4c644ce9-3b9/agent-a464c63c2c8f672fd.jsonl')


def units():
    return json.load(open(IN))


def unit(ad_id):
    for u in units():
        if u['unit'] == ad_id:
            return u
    raise KeyError(ad_id)


def excluded(ad_id, slot):
    for x in json.load(open(EXCL)):
        if x.get('platform') == 'meta' and str(x.get('ad_id')) == str(ad_id) and x.get('slot') == slot:
            return True
    return False


def _result_text(cc):
    if isinstance(cc, list):
        return ''.join(x.get('text', '') for x in cc if isinstance(x, dict) and x.get('type') == 'text')
    if isinstance(cc, str):
        return cc
    return json.dumps(cc)


def calls(transcript=TRANSCRIPT):
    """[(tool_use_id, tool_name, input, result_text, is_error)] in call order"""
    uses, order, results = {}, [], {}
    for line in open(transcript):
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
            if b.get('type') == 'tool_use':
                if b['id'] not in uses:
                    order.append(b['id'])
                uses[b['id']] = (b['name'], b.get('input') or {})
            elif b.get('type') == 'tool_result':
                results[b['tool_use_id']] = (_result_text(b.get('content')), b.get('is_error'))
    out = []
    for i in order:
        res, err = results.get(i, (None, None))
        out.append((i, uses[i][0], uses[i][1], res, err))
    return out


def whathead_calls(transcript=TRANSCRIPT):
    return [c for c in calls(transcript) if 'Whathed' in c[1]]


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
            return {'_unparsed': raw[:500]}
        if isinstance(d, list) and d and isinstance(d[0], dict) and 'text' in d[0]:
            return json.loads(''.join(x.get('text', '') for x in d))
        return d
    return {'_unparsed': t[:500]}


def find_calls(action, pred=None, transcript=TRANSCRIPT):
    out = []
    for cid, name, inp, res, err in whathead_calls(transcript):
        if inp.get('action') == action and (pred is None or pred(inp)):
            out.append((cid, inp, res, err))
    return out


def last_call(action, pred=None, transcript=TRANSCRIPT):
    out = find_calls(action, pred, transcript)
    return out[-1] if out else None


TRUNC_MARKERS = ('MCP_OUTPUT_TRUNCATED', 'more items truncated', '[TRUNCATED')
TRUNC_KEYS = {'mcp_output_budget', 'truncated', '_truncated', 'mcp_truncated', 'truncation', '_mcp_truncated'}


def has_trunc(o):
    if isinstance(o, dict):
        return any(str(k).lower() in TRUNC_KEYS for k in o) or any(has_trunc(v) for v in o.values())
    if isinstance(o, list):
        return any(has_trunc(v) for v in o)
    if isinstance(o, str):
        return any(m in o for m in TRUNC_MARKERS)
    return False


def ok_data(res_text):
    d = parse_result(res_text)
    assert d and d.get('success') and d['data'].get('success'), str(d)[:500]
    assert not has_trunc(d), 'truncated result'
    return d['data']['data'], d


def read_creative(creative_id, transcript=TRANSCRIPT):
    hit = last_call('meta_creative_id_get', lambda i: (i.get('path_params') or {}).get('creative_id') == creative_id,
                    transcript)
    assert hit, ('no read for', creative_id)
    data, d = ok_data(hit[2])
    return data, d['meta']['requestId']


def read_ad(ad_id, transcript=TRANSCRIPT, nth=-1):
    hits = find_calls('meta_ad_id_get', lambda i: (i.get('path_params') or {}).get('ad_id') == ad_id, transcript)
    assert hits, ('no ad read for', ad_id)
    data, d = ok_data(hits[nth][2])
    return data, d['meta']['requestId']


# ------------------------------------------------------------ urls / slots
def same_url(a, b):
    if a is None or b is None:
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


def full_landing(creative, slot):
    url = get_slot(creative, slot)
    tags = creative.get('url_tags')
    if tags:
        url = url + ('&' if '?' in url else '?') + tags
    return url


def classify(u, creative):
    res = []
    for c in u['changes']:
        try:
            cur = full_landing(creative, c['slot'])
        except Exception:
            cur = None
        if cur is not None and same_url(cur, c['new']):
            v = 'AlreadyFixed'
        elif cur == c['now'] or cur in c.get('alt_now', []):
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
    elif isinstance(o, str) and o.startswith('http') and ('utm_' in o or 'diriyah' in o):
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


# ------------------------------------------------------------ payload
DROP_TOP = {'id', 'account_id', 'actor_id', 'object_type', 'status', 'effective_object_story_id',
            'effective_instagram_media_id', 'use_page_actor_override', 'body', 'title', 'image_hash', 'image_url',
            'call_to_action', 'call_to_action_type', 'instagram_user_id', 'video_id', 'thumbnail_url', 'thumbnail_id',
            'object_story_id', 'effective_authorization_category', 'link_url', 'object_id',
            'object_url', 'instagram_permalink_url', 'enable_direct_install', 'enable_launch_instant_app'}
KEEP_TOP = ['name', 'object_story_spec', 'asset_feed_spec', 'degrees_of_freedom_spec', 'contextual_multi_ads',
            'creative_sourcing_spec', 'media_sourcing_spec', 'format_transformation_spec', 'threads_user_id',
            'authorization_category', 'portrait_customizations', 'url_tags', 'source_instagram_media_id',
            'platform_customizations', 'branded_content', 'ad_disclaimer_spec', 'regional_regulation_disclaimer_spec',
            'link_destination_display_url', 'page_welcome_message', 'applink_treatment',
            'interactive_components_spec', 'template_url', 'template_url_spec', 'product_set_id',
            'recommender_settings', 'facebook_branded_content', 'instagram_branded_content', 'bundle_folder_id',
            'categorization_criteria', 'place_page_set_id', 'destination_set_id', 'dynamic_ad_voice',
            'playable_asset_id', 'link_og_id', 'image_crops', 'omnichannel_link_spec']


def unknown_fields(creative):
    return [k for k in creative if k not in DROP_TOP and k not in KEEP_TOP]


def build_payload(creative, changes):
    unk = unknown_fields(creative)
    assert not unk, ('unhandled creative fields', unk)
    notes = []
    p = {}
    for k in KEEP_TOP:
        if k in creative and creative[k] is not None:
            p[k] = copy.deepcopy(creative[k])
    oss = p.get('object_story_spec') or {}
    if 'instagram_user_id' not in oss and creative.get('instagram_user_id'):
        p['instagram_user_id'] = creative['instagram_user_id']
        notes.append('top-level instagram_user_id sent')
    cfs = (p.get('degrees_of_freedom_spec') or {}).get('creative_features_spec', {})
    if 'standard_enhancements' in cfs:
        notes.append('deprecated standard_enhancements not sent')
        del cfs['standard_enhancements']
        if not cfs and set((p.get('degrees_of_freedom_spec') or {}).keys()) <= {'creative_features_spec'}:
            del p['degrees_of_freedom_spec']
    vd = oss.get('video_data')
    if vd and vd.get('image_hash') and 'image_url' in vd:
        del vd['image_url']
        notes.append('video_data.image_url not sent; image_hash sent')
    ld = oss.get('link_data')
    if ld and ld.get('image_hash') and 'picture' in ld:
        del ld['picture']
        notes.append('link_data.picture not sent; image_hash sent')
    for v in (p.get('asset_feed_spec') or {}).get('videos', []) or []:
        assert 'stp=' not in v.get('thumbnail_url', ''), 'resized thumbnail rendition in read - handle by hand'
    for ch in changes:
        old = get_slot(p, ch['slot'])
        assert old == ch['now'] or old in ch.get('alt_now', []), (ch['slot'], old)
        set_slot(p, ch['slot'], ch['new'])
    for path, url in all_urls(p):
        if 'utm_' in url:
            assert any(url == ch['new'] for ch in changes), ('other UTM url in payload', path, url)
    return p, notes


DERIVED = {'id', 'name', 'status', 'effective_object_story_id', 'effective_instagram_media_id', 'instagram_permalink_url',
           'thumbnail_url', 'object_story_id', 'link_og_id', 'link_url', 'object_id', 'video_id', 'call_to_action'}


def compare_new(orig, new, changes):
    """differences between (orig with the slot(s) set to new) and the new creative, ignoring derived fields"""
    exp = copy.deepcopy(orig)
    for ch in changes:
        set_slot(exp, ch['slot'], ch['new'])
    a = {k: v for k, v in exp.items() if k not in DERIVED}
    b = {k: v for k, v in new.items() if k not in DERIVED}
    return diff(a, b)


def split_dof(d):
    """split diff lines into (Meta-default degrees_of_freedom_spec additions, everything else)"""
    dof = [x for x in d if x.startswith('+ .degrees_of_freedom_spec')]
    other = [x for x in d if not x.startswith('+ .degrees_of_freedom_spec')]
    return dof, other


def dof_summary(creative):
    cfs = ((creative.get('degrees_of_freedom_spec') or {}).get('creative_features_spec') or {})
    vals = sorted(set(json.dumps(v, sort_keys=True) for v in cfs.values()))
    return len(cfs), vals
