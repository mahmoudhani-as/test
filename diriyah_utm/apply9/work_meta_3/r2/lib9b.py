"""Helpers for apply9 in_meta_3, second agent (local analysis of saved Whathead results; never calls an API)."""
import json, copy, re, unicodedata, sys
from urllib.parse import urlsplit, parse_qsl

ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
IN = ROOT + '/apply9/in_meta_3.json'
W = ROOT + '/apply9/work_meta_3/r2/'
EXCL = ROOT + '/work/excl_platform_refused_v2.json'
PROJ = '/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/'
TRANSCRIPT = PROJ + 'wf_f76d0421-984/agent-a73eaae9994946b93.jsonl'
PREV_TRANSCRIPT = PROJ + 'wf_4c644ce9-3b9/agent-ac2eb5a8468a43cc0.jsonl'

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


# ------------------------------------------------------------ transcript: exact tool inputs and results
def _result_text(cc):
    if isinstance(cc, list):
        return ''.join(x.get('text', '') for x in cc if isinstance(x, dict) and x.get('type') == 'text')
    if isinstance(cc, str):
        return cc
    return json.dumps(cc)


def calls(path=TRANSCRIPT):
    uses, order, results = {}, [], {}
    for line in open(path):
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


def whathead_calls(path=TRANSCRIPT):
    return [c for c in calls(path) if 'Whathed' in c[1]]


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
    return {'_unparsed': t[:500]}


def find_calls(action, pred=None, path=TRANSCRIPT):
    out = []
    for cid, name, inp, res in whathead_calls(path):
        if inp.get('action') == action and (pred is None or pred(inp)):
            out.append((cid, inp, res))
    return out


def last_call(action, pred=None, path=TRANSCRIPT):
    x = find_calls(action, pred, path)
    return x[-1] if x else None


TRUNC_MARKS = ('MCP_OUTPUT_TRUNCATED', 'more items truncated', '[TRUNCATED', 'mcp_output_budget')


def has_trunc(o):
    s = json.dumps(o, ensure_ascii=False)
    return any(m in s for m in TRUNC_MARKS) or '"truncated": true' in s or '"_truncated"' in s


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


def full_url(creative, slot):
    """landing URL incl. separately stored url_tags (Meta appends url_tags to the link)"""
    try:
        v = get_slot(creative, slot)
    except Exception:
        return None
    tags = creative.get('url_tags')
    if tags and isinstance(v, str):
        v = v + ('&' if '?' in v else '?') + tags
    return v


def classify(u, creative):
    res = []
    for c in u['changes']:
        cur = full_url(creative, c['slot'])
        if cur is not None and same_url(cur, c['new']):
            v = 'AlreadyFixed'
        elif cur == c['now'] or cur in (c.get('alt_now') or []):
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


def dumps_tool(o):
    """compact JSON: ASCII and Arabic letters kept literally; every other non-ASCII char escaped as \\uXXXX"""
    s = json.dumps(o, ensure_ascii=False, separators=(',', ':'))
    out = []
    for ch in s:
        o_ = ord(ch)
        if o_ < 128:
            out.append(ch)
        elif 0x0600 <= o_ <= 0x06FF and unicodedata.category(ch) in ('Lo', 'Nd', 'Lm'):
            out.append(ch)
        elif o_ > 0xFFFF:
            hi = 0xD800 + ((o_ - 0x10000) >> 10)
            lo = 0xDC00 + ((o_ - 0x10000) & 0x3FF)
            out.append('\\u%04x\\u%04x' % (hi, lo))
        else:
            out.append('\\u%04x' % o_)
    return ''.join(out)


# ------------------------------------------------------------ reads
def data_of(res_text):
    d = parse_result(res_text)
    assert isinstance(d, dict), d
    assert not has_trunc(d), 'truncated read'
    assert d.get('success') and d['data'].get('success'), json.dumps(d, ensure_ascii=False)[:1500]
    return d['data']['data']


def last_ad_read(ad_id, path=TRANSCRIPT):
    hit = last_call('meta_ad_id_get', lambda i: str((i.get('path_params') or {}).get('ad_id')) == str(ad_id), path)
    assert hit, ('no ad read for', ad_id)
    return data_of(hit[2])


def last_creative_read(cid, path=TRANSCRIPT):
    hit = last_call('meta_creative_id_get', lambda i: str((i.get('path_params') or {}).get('creative_id')) == str(cid), path)
    assert hit, ('no creative read for', cid)
    return data_of(hit[2])


# ------------------------------------------------------------ payload
def build_payload(creative, changes):
    """exact copy of the creative's creatable fields with only the listed slot(s) set to new"""
    notes = []
    unknown = [k for k in creative if k not in SEND_KEYS and k not in DERIVED]
    assert not unknown, ('unhandled creative fields', unknown)
    boosted = bool(creative.get('source_instagram_media_id')) and not creative.get('object_story_spec') \
        and not creative.get('asset_feed_spec')
    p = {}
    if boosted:
        p['name'] = creative['name']
        p['object_id'] = creative.get('object_id') or creative['actor_id']
        if creative.get('instagram_user_id'):
            p['instagram_user_id'] = creative['instagram_user_id']
        p['source_instagram_media_id'] = creative['source_instagram_media_id']
        p['call_to_action'] = copy.deepcopy(creative['call_to_action'])
        for k in ['contextual_multi_ads', 'threads_user_id', 'authorization_category', 'degrees_of_freedom_spec',
                  'creative_sourcing_spec', 'media_sourcing_spec', 'url_tags', 'branded_content',
                  'ad_disclaimer_spec', 'regional_regulation_disclaimer_spec', 'portrait_customizations',
                  'platform_customizations', 'format_transformation_spec', 'interactive_components_spec']:
            if k in creative and creative[k] is not None:
                p[k] = copy.deepcopy(creative[k])
        other = [k for k in creative if k in SEND_KEYS and k not in p and creative[k] is not None]
        assert not other, ('boosted creative has other creatable fields', other)
        notes.append('boosted IG post recipe')
    else:
        for k in SEND_KEYS:
            if k in creative and creative[k] is not None:
                p[k] = copy.deepcopy(creative[k])
    dof = (p.get('degrees_of_freedom_spec') or {}).get('creative_features_spec')
    if dof and 'standard_enhancements' in dof:
        notes.append('deprecated degrees_of_freedom_spec standard_enhancements %s not sent'
                     % json.dumps(dof['standard_enhancements']))
        dof.pop('standard_enhancements')
        if not dof:
            p['degrees_of_freedom_spec'].pop('creative_features_spec')
            if not p['degrees_of_freedom_spec']:
                p.pop('degrees_of_freedom_spec')
    oss = p.get('object_story_spec') or {}
    vd = oss.get('video_data')
    if vd and vd.get('image_hash') and 'image_url' in vd:
        del vd['image_url']
        notes.append('video_data.image_url (derived from image_hash) not sent; image_hash sent')
    ld = oss.get('link_data')
    if ld and ld.get('image_hash') and 'picture' in ld:
        del ld['picture']
        notes.append('link_data.picture (derived from image_hash) not sent; image_hash sent')
    for sl in (p.get('creative_sourcing_spec') or {}).get('site_links_spec', []) or []:
        if sl.get('site_link_image_hash') and 'site_link_image_url' in sl:
            del sl['site_link_image_url']
            if 'site_links_spec: derived site_link_image_url not sent' not in notes:
                notes.append('site_links_spec: derived site_link_image_url not sent')
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


SANITY_SKIP = {'id', 'name', 'status', 'video_id', 'effective_object_story_id', 'link_url', 'object_id',
               'effective_instagram_media_id', 'instagram_permalink_url'}


def strip_labels(o):
    """drop adlabels ids/names and *_label refs (Meta re-issues label ids on a new creative)"""
    if isinstance(o, dict):
        return {k: strip_labels(v) for k, v in o.items() if k != 'adlabels' and not k.endswith('_label')}
    if isinstance(o, list):
        return [strip_labels(v) for v in o]
    return o


def sanity(orig, new, changes, extra_skip=(), labels=True):
    exp = copy.deepcopy(orig)
    for c in changes:
        set_slot(exp, c['slot'], c['new'])
    skip = SANITY_SKIP | set(extra_skip)
    A = {k: v for k, v in exp.items() if k not in skip}
    B = {k: v for k, v in new.items() if k not in skip}
    if not labels:
        A, B = strip_labels(A), strip_labels(B)
    d = diff(norm(A), norm(B))
    added_defaults = [x for x in d if re.match(r'\+ \.(degrees_of_freedom_spec\.creative_features_spec\.\w+|creative_sourcing_spec(\.destination_screenshot_spec)?|degrees_of_freedom_spec) = ', x)]
    dof_vals = set()
    for k, v in ((new.get('degrees_of_freedom_spec') or {}).get('creative_features_spec') or {}).items():
        dof_vals.add(v.get('enroll_status'))
    other = [x for x in d if x not in added_defaults]
    return {'n_diff': len(d), 'meta_added_defaults': len(added_defaults), 'dof_values_new': sorted(dof_vals),
            'other': other, 'name_orig': orig.get('name'), 'name_new': new.get('name'),
            'name_kept_as_prefix': (new.get('name') or '').startswith(orig.get('name') or '\x00')}


def save(name, obj):
    with open(W + name, 'w') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
