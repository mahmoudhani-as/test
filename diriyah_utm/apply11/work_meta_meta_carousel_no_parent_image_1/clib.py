"""Read-only helpers for apply11 in_meta_meta_carousel_no_parent_image_1 (agent a071bd55d3dc9f863).
Parses this agent's own Whathead tool results from its transcript (exact bytes), classifies slots,
builds the recipe payload (exact copy without link_data.image_hash / link_data.picture) and diffs reads.
Nothing here calls an API."""
import json, copy, re
from urllib.parse import urlsplit, parse_qsl

ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
IN = ROOT + '/apply11/in_meta_meta_carousel_no_parent_image_1.json'
W = ROOT + '/apply11/work_meta_meta_carousel_no_parent_image_1/'
EXCL = ROOT + '/work/excl_platform_refused_v2.json'
TRANSCRIPT = ('/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/'
              'wf_3ea65700-94c/agent-a071bd55d3dc9f863.jsonl')


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


def _rt(cc):
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
            if b.get('type') == 'tool_use':
                if b['id'] not in uses:
                    order.append(b['id'])
                uses[b['id']] = (b['name'], b.get('input') or {})
            elif b.get('type') == 'tool_result':
                results[b['tool_use_id']] = _rt(b.get('content'))
    return [(i, uses[i][0], uses[i][1], results.get(i)) for i in order]


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


def find(action, pred=None):
    out = []
    for cid, name, inp, res in calls():
        if 'Whathed' in name and inp.get('action') == action and (pred is None or pred(inp)):
            out.append((cid, inp, res))
    return out


TRUNC_KEYS = {'mcp_output_budget', 'truncated', '_truncated', 'mcp_truncated', 'truncation', '_mcp_truncated'}


def has_trunc(o):
    if isinstance(o, dict):
        return any(str(k).lower() in TRUNC_KEYS for k in o) or any(has_trunc(v) for v in o.values())
    if isinstance(o, list):
        return any(has_trunc(v) for v in o)
    if isinstance(o, str):
        return 'MCP_OUTPUT_TRUNCATED' in o or 'more items truncated' in o or '[TRUNCATED' in o
    return False


def _data(res):
    d = parse_result(res)
    assert not has_trunc(d), 'truncated read'
    assert d.get('success') and d['data'].get('success'), json.dumps(d)[:800]
    return d['data']['data']


def req_id(res):
    d = parse_result(res)
    try:
        return d.get('meta', {}).get('requestId')
    except Exception:
        return None


def creative(cid, idx=-1):
    hits = find('meta_creative_id_get', lambda i: (i.get('path_params') or {}).get('creative_id') == cid)
    assert hits, ('no read for', cid)
    return _data(hits[idx][2])


def creative_req(cid, idx=-1):
    hits = find('meta_creative_id_get', lambda i: (i.get('path_params') or {}).get('creative_id') == cid)
    assert hits, ('no read for', cid)
    return req_id(hits[idx][2])


def ad(ad_id, idx=-1):
    hits = find('meta_ad_id_get', lambda i: (i.get('path_params') or {}).get('ad_id') == ad_id)
    assert hits, ('no ad read for', ad_id)
    return _data(hits[idx][2])


def ad_req(ad_id, idx=-1):
    hits = find('meta_ad_id_get', lambda i: (i.get('path_params') or {}).get('ad_id') == ad_id)
    assert hits, ('no ad read for', ad_id)
    return req_id(hits[idx][2])


# ------------------------------------------------------------ slots / urls
def same_url(a, b):
    if not isinstance(a, str) or not isinstance(b, str):
        return False
    A, B = urlsplit(a), urlsplit(b)
    return (A.scheme, A.netloc, A.path, A.fragment) == (B.scheme, B.netloc, B.path, B.fragment) and \
        sorted(parse_qsl(A.query, keep_blank_values=True)) == sorted(parse_qsl(B.query, keep_blank_values=True))


def _parts(slot):
    assert slot.startswith('creative.')
    return slot[len('creative.'):].split('.')


def get_slot(cr, slot):
    cur = cr
    for part in _parts(slot):
        m = re.fullmatch(r'(\w+)\[(\d+)\]', part)
        if m:
            cur = cur[m.group(1)][int(m.group(2))]
        else:
            cur = cur[part]
    return cur


def set_slot(cr, slot, value):
    parts = _parts(slot)
    cur = cr
    for part in parts[:-1]:
        m = re.fullmatch(r'(\w+)\[(\d+)\]', part)
        cur = cur[m.group(1)][int(m.group(2))] if m else cur[part]
    last = parts[-1]
    m = re.fullmatch(r'(\w+)\[(\d+)\]', last)
    if m:
        cur[m.group(1)][int(m.group(2))] = value
    else:
        assert last in cur, (slot, 'missing leaf')
        cur[last] = value


def full_url(cr, slot):
    """landing URL incl. url_tags (Meta appends url_tags to the link at click time)"""
    try:
        v = get_slot(cr, slot)
    except Exception:
        return None
    tags = cr.get('url_tags')
    if tags and isinstance(v, str):
        v = v + ('&' if '?' in v else '?') + tags
    return v


def classify(u, cr):
    res = []
    for c in u['changes']:
        cur = full_url(cr, c['slot'])
        if cur is not None and same_url(cur, c['new']):
            v = 'AlreadyFixed'
        elif cur == c['now'] or cur in c['alt_now']:
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
            out.append(f'~ {path}: {json.dumps(a, ensure_ascii=False)[:220]} -> {json.dumps(b, ensure_ascii=False)[:220]}')
    return out


# fields that are read-only / derived on a creative read (never sent on create)
DERIVED = {'id', 'account_id', 'status', 'object_type', 'effective_object_story_id', 'effective_instagram_media_id',
           'effective_authorization_category', 'thumbnail_url', 'thumbnail_id', 'instagram_permalink_url',
           'link_og_id', 'actor_id', 'enable_direct_install', 'enable_launch_instant_app', 'use_page_actor_override',
           'image_url', 'video_id', 'object_id', 'link_url', 'body', 'title', 'image_hash', 'call_to_action_type'}


def expected_new(orig, changes):
    """what the new creative should look like: orig with the listed slots = new and (recipe) no parent
    link_data.image_hash / link_data.picture"""
    exp = copy.deepcopy(orig)
    for ch in changes:
        set_slot(exp, ch['slot'], ch['new'])
    ld = (exp.get('object_story_spec') or {}).get('link_data') or {}
    ld.pop('image_hash', None)
    ld.pop('picture', None)
    return exp


def compare_new(orig, new, changes):
    """diff of a new creative vs expected_new(orig), ignoring derived top-level fields"""
    exp = expected_new(orig, changes)
    a = {k: v for k, v in exp.items() if k not in DERIVED}
    b = {k: v for k, v in new.items() if k not in DERIVED}
    return diff(a, b)


# ------------------------------------------------------------ payload (exact copy of the creatable fields)
DROP_TOP = {'id', 'account_id', 'actor_id', 'object_type', 'status', 'effective_object_story_id',
            'effective_instagram_media_id', 'use_page_actor_override', 'body', 'title', 'image_hash', 'image_url',
            'call_to_action', 'call_to_action_type', 'video_id', 'thumbnail_url', 'thumbnail_id',
            'effective_authorization_category', 'link_url', 'object_id', 'object_url', 'instagram_permalink_url',
            'enable_direct_install', 'enable_launch_instant_app', 'link_og_id', 'instagram_user_id'}
KEEP_TOP = ['name', 'object_story_spec', 'asset_feed_spec', 'degrees_of_freedom_spec', 'contextual_multi_ads',
            'creative_sourcing_spec', 'media_sourcing_spec', 'format_transformation_spec', 'threads_user_id',
            'authorization_category', 'portrait_customizations', 'url_tags', 'source_instagram_media_id',
            'platform_customizations', 'branded_content', 'ad_disclaimer_spec', 'regional_regulation_disclaimer_spec',
            'link_destination_display_url', 'page_welcome_message', 'applink_treatment',
            'interactive_components_spec', 'template_url', 'template_url_spec', 'product_set_id',
            'recommender_settings', 'facebook_branded_content', 'instagram_branded_content', 'bundle_folder_id',
            'categorization_criteria', 'place_page_set_id', 'destination_set_id', 'dynamic_ad_voice',
            'playable_asset_id', 'image_crops', 'omnichannel_link_spec']


def unknown_fields(cr):
    return [k for k in cr if k not in DROP_TOP and k not in KEEP_TOP]


def build_payload(cr, changes):
    """recipe meta_carousel_no_parent_image: exact copy of the creatable fields, listed URL slots = new,
    object_story_spec.link_data.image_hash and link_data.picture NOT sent; child_attachments exactly as read."""
    unk = unknown_fields(cr)
    assert not unk, ('unhandled creative fields', unk)
    assert not cr.get('url_tags'), 'creative has url_tags - handle by hand'
    assert not cr.get('object_story_id') and not cr.get('source_instagram_media_id'), 'post-based creative - handle by hand'
    assert not cr.get('asset_feed_spec'), 'asset_feed_spec creative - not this recipe'
    assert not cr.get('interactive_components_spec'), 'creative has interactive_components_spec - handle by hand'
    notes = []
    p = {}
    for k in KEEP_TOP:
        if k in cr and cr[k] is not None:
            p[k] = copy.deepcopy(cr[k])
    oss = p.get('object_story_spec') or {}
    if 'instagram_user_id' not in oss and cr.get('instagram_user_id'):
        p['instagram_user_id'] = cr['instagram_user_id']
        notes.append('top-level instagram_user_id sent as read (object_story_spec has no instagram_user_id)')
    elif cr.get('instagram_user_id') and oss.get('instagram_user_id') != cr.get('instagram_user_id'):
        raise AssertionError('instagram_user_id differs top-level vs object_story_spec')
    cfs = (p.get('degrees_of_freedom_spec') or {}).get('creative_features_spec', {})
    if 'standard_enhancements' in cfs:
        notes.append('deprecated standard_enhancements=%s not sent' % cfs['standard_enhancements'].get('enroll_status'))
        del cfs['standard_enhancements']
    ld = oss.get('link_data')
    assert ld and isinstance(ld.get('child_attachments'), list) and ld['child_attachments'], 'not a carousel'
    removed = []
    for k in ('image_hash', 'picture'):
        if k in ld:
            removed.append('%s=%s' % (k, ld[k]))
            del ld[k]
    notes.append('recipe: parent link_data %s not sent' % (', '.join(removed) if removed else '(image_hash/picture absent)'))
    for ch in changes:
        old = get_slot(p, ch['slot'])
        assert old == ch['now'] or old in ch['alt_now'], (ch['slot'], old)
        set_slot(p, ch['slot'], ch['new'])
    news = {ch['new'] for ch in changes}
    for path, url in all_urls(p):
        if 'utm_' in url:
            assert url in news, ('other UTM url in payload', path, url)
    # sanity: the payload differs from the read only in the listed slots and the removed parent image fields
    exp = {k: v for k, v in expected_new(cr, changes).items()
           if k in KEEP_TOP or (k == 'instagram_user_id' and 'instagram_user_id' in p)}
    d = diff(exp, p)
    assert not d, ('payload differs from expected', d)
    return p, notes


def check_create_calls(payload_file, dry):
    """compare this agent's create calls (dry_run==dry) with the payload file: tool input and (for dry) the echoed body"""
    p = json.load(open(W + payload_file))
    out = []
    for cid, inp, res in find('meta_ad_account_id_adcreatives_create', lambda i: bool(i.get('dry_run')) == dry):
        d = parse_result(res)
        row = {'tool_use': cid[-8:], 'input_equals_payload': inp.get('payload') == p,
               'path_params': inp.get('path_params'), 'dry_run': inp.get('dry_run')}
        if inp.get('payload') != p:
            row['diff_input'] = diff(p, inp.get('payload'))[:10]
        try:
            if dry:
                body = d['data']['data']['request']['body']
                row['body_equals_payload'] = body == p
                row['url'] = d['data']['data']['request']['url']
                if body != p:
                    row['diff_body'] = diff(p, body)[:10]
            else:
                row['result'] = d['data'].get('data') if d.get('success') else d
                row['requestId'] = d.get('meta', {}).get('requestId')
        except Exception as e:
            row['err'] = repr(e)[:300]
            row['raw'] = json.dumps(d)[:600]
        out.append(row)
    return out
