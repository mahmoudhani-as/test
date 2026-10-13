import json, copy, re, unicodedata
from urllib.parse import urlsplit, parse_qsl

ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
IN = ROOT + '/apply9/in_meta_4.json'
W = ROOT + '/apply9/work_meta_4/'
EXCL = ROOT + '/work/excl_platform_refused_v2.json'
TRANSCRIPT = ('/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/'
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


# ------------------------------------------------------------ transcript: exact tool inputs and results
def _result_text(cc):
    if isinstance(cc, list):
        return ''.join(x.get('text', '') for x in cc if isinstance(x, dict) and x.get('type') == 'text')
    if isinstance(cc, str):
        return cc
    return json.dumps(cc)


def calls():
    """[(tool_use_id, tool_name, input, result_text)] in call order"""
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
                results[b['tool_use_id']] = _result_text(b.get('content'))
    return [(i, uses[i][0], uses[i][1], results.get(i)) for i in order]


def whathead_calls():
    return [c for c in calls() if 'Whathed' in c[1]]


def parse_result(txt):
    """parsed gateway JSON. If the harness saved the output to a file, load that file."""
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


def find_call(action, pred=None, last=True):
    out = []
    for cid, name, inp, res in whathead_calls():
        if inp.get('action') == action and (pred is None or pred(inp)):
            out.append((cid, inp, res))
    if not out:
        return None
    return out[-1] if last else out


TRUNC_KEYS = {'mcp_output_budget', 'truncated', '_truncated', 'mcp_truncated', 'truncation', '_mcp_truncated'}


def has_trunc(o):
    if isinstance(o, dict):
        return any(str(k).lower() in TRUNC_KEYS for k in o) or any(has_trunc(v) for v in o.values())
    if isinstance(o, list):
        return any(has_trunc(v) for v in o)
    if isinstance(o, str):
        return 'MCP_OUTPUT_TRUNCATED' in o or 'more items truncated' in o or '[TRUNCATED' in o
    return False


# ------------------------------------------------------------ slots / urls
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
    """slot URL plus the creative's url_tags, if any (what the click lands on)"""
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
        if a != b:
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

READ_FIELDS = ('id,name,status,account_id,actor_id,object_type,object_story_spec,object_story_id,effective_object_story_id,'
               'object_id,object_url,asset_feed_spec,url_tags,degrees_of_freedom_spec,contextual_multi_ads,creative_sourcing_spec,'
               'format_transformation_spec,media_sourcing_spec,threads_user_id,authorization_category,effective_authorization_category,'
               'interactive_components_spec,platform_customizations,portrait_customizations,ad_disclaimer_spec,'
               'regional_regulation_disclaimer_spec,branded_content,facebook_branded_content,instagram_branded_content,'
               'source_instagram_media_id,call_to_action,call_to_action_type,applink_treatment,link_destination_display_url,'
               'omnichannel_link_spec,page_welcome_message,image_crops,instagram_user_id,instagram_permalink_url,'
               'effective_instagram_media_id,link_url,template_url,product_set_id,image_hash,image_url,video_id,thumbnail_url,'
               'title,body,destination_set_id,dynamic_ad_voice,recommender_settings,playable_asset_id,categorization_criteria,'
               'category_media_source,bundle_folder_id,branded_content_sponsor_page_id,link_og_id,use_page_actor_override,'
               'enable_direct_install,enable_launch_instant_app,photo_album_source_object_story_id,place_page_set_id,'
               'messenger_sponsored_message,object_store_url')


def unknown_fields(creative):
    return [k for k in creative if k not in DROP_TOP and k not in KEEP_TOP]


def dumps_tool(o):
    """compact JSON: ASCII and Arabic letters kept literally; every other non-ASCII char escaped as \\uXXXX"""
    s = json.dumps(o, ensure_ascii=False, separators=(',', ':'))
    out = []
    for ch in s:
        o_ = ord(ch)
        if o_ < 128:
            out.append(ch)
        elif 0x0600 <= o_ <= 0x06FF and unicodedata.category(ch) in ('Lo', 'Mn', 'Nd', 'Lm'):
            out.append(ch)
        else:
            out.append('\\u%04x' % o_)
    return ''.join(out)


def nonascii_report(o):
    s = json.dumps(o, ensure_ascii=False)
    seen = {}
    for ch in s:
        if ord(ch) > 127:
            seen[ch] = seen.get(ch, 0) + 1
    return sorted(('U+%04X' % ord(c), unicodedata.category(c), unicodedata.name(c, '?'), n) for c, n in seen.items())


def read_creative(creative_id, last=True):
    """the exact creative object from the last meta_creative_id_get of this id"""
    hit = find_call('meta_creative_id_get', lambda i: (i.get('path_params') or {}).get('creative_id') == creative_id)
    assert hit, ('no read for', creative_id)
    d = parse_result(hit[2])
    assert not has_trunc(d), 'truncated read'
    assert d.get('success') and d['data'].get('success'), d
    return d['data']['data']


def read_ad(ad_id):
    hit = find_call('meta_ad_id_get', lambda i: (i.get('path_params') or {}).get('ad_id') == ad_id)
    assert hit, ('no ad read for', ad_id)
    d = parse_result(hit[2])
    assert not has_trunc(d), 'truncated read'
    assert d.get('success') and d['data'].get('success'), d
    return d['data']['data'], d


def build_payload(creative, changes):
    """exact copy of the creative's creatable fields, with only the listed slot(s) set to new"""
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
        notes.append('top-level instagram_user_id %s sent as read (object_story_spec has page_id only)' % creative['instagram_user_id'])
    cfs = (p.get('degrees_of_freedom_spec') or {}).get('creative_features_spec', {})
    if 'standard_enhancements' in cfs:
        notes.append('deprecated standard_enhancements %s not sent (Meta rejects it on create)' % cfs['standard_enhancements'].get('enroll_status'))
        del cfs['standard_enhancements']
        if not cfs and set((p.get('degrees_of_freedom_spec') or {}).keys()) <= {'creative_features_spec'}:
            del p['degrees_of_freedom_spec']
            notes.append('standard_enhancements was the only degrees_of_freedom_spec key, so degrees_of_freedom_spec was not sent')
    vd = oss.get('video_data')
    if vd and vd.get('image_hash') and 'image_url' in vd:
        del vd['image_url']
        notes.append('video_data.image_url (derived from image_hash) not sent; image_hash sent')
    ld = oss.get('link_data')
    if ld and ld.get('image_hash') and 'picture' in ld:
        del ld['picture']
        notes.append('link_data.picture (derived from image_hash) not sent; image_hash sent')
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
    exp = copy.deepcopy(orig)
    for ch in changes:
        set_slot(exp, ch['slot'], ch['new'])
    a = {k: v for k, v in exp.items() if k not in DERIVED}
    b = {k: v for k, v in new.items() if k not in DERIVED}
    return diff(a, b)
