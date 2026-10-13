import json, copy, re, unicodedata, datetime
from urllib.parse import urlsplit, parse_qsl

ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
IN = ROOT + '/apply7/in_meta_16.json'
OUT = ROOT + '/apply7/out_meta_16.jsonl'
W = ROOT + '/apply7/meta16_work/'
EXCL = ROOT + '/work/excl_platform_refused_v2.json'

# creative fields copied into the new creative when present on the live creative
SEND_KEYS = ['name', 'object_story_spec', 'asset_feed_spec', 'degrees_of_freedom_spec', 'contextual_multi_ads',
             'creative_sourcing_spec', 'media_sourcing_spec', 'format_transformation_spec', 'threads_user_id',
             'authorization_category', 'portrait_customizations', 'url_tags', 'source_instagram_media_id',
             'platform_customizations', 'branded_content', 'ad_disclaimer_spec',
             'regional_regulation_disclaimer_spec', 'link_destination_display_url', 'page_welcome_message',
             'applink_treatment', 'interactive_components_spec', 'template_url', 'template_url_spec',
             'product_set_id', 'recommender_settings', 'facebook_branded_content', 'instagram_branded_content',
             'bundle_folder_id', 'categorization_criteria', 'place_page_set_id', 'destination_set_id',
             'dynamic_ad_voice', 'playable_asset_id', 'link_og_id']
# read-only / derived fields that are never sent
DERIVED = {'id', 'account_id', 'actor_id', 'object_type', 'status', 'effective_object_story_id',
           'effective_instagram_media_id', 'use_page_actor_override', 'body', 'title', 'image_hash',
           'call_to_action', 'image_crops', 'instagram_user_id', 'video_id', 'call_to_action_type',
           'effective_authorization_category', 'link_url', 'object_url', 'object_id', 'object_story_id',
           'thumbnail_id', 'instagram_permalink_url'}

CREATIVE_FIELDS = ('id,name,account_id,actor_id,object_type,status,object_story_spec,asset_feed_spec,'
                   'degrees_of_freedom_spec,contextual_multi_ads,creative_sourcing_spec,media_sourcing_spec,'
                   'format_transformation_spec,threads_user_id,authorization_category,portrait_customizations,'
                   'url_tags,source_instagram_media_id,platform_customizations,branded_content,ad_disclaimer_spec,'
                   'regional_regulation_disclaimer_spec,link_destination_display_url,page_welcome_message,'
                   'applink_treatment,interactive_components_spec,template_url,template_url_spec,product_set_id,'
                   'recommender_settings,facebook_branded_content,instagram_branded_content,bundle_folder_id,'
                   'categorization_criteria,place_page_set_id,object_id,link_url,object_url,'
                   'effective_object_story_id,effective_instagram_media_id,use_page_actor_override,body,title,'
                   'image_hash,call_to_action,image_crops,instagram_user_id,video_id,object_story_id,'
                   'destination_set_id,dynamic_ad_voice,playable_asset_id,link_og_id,call_to_action_type,'
                   'effective_authorization_category')


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
    if not isinstance(a, str) or not isinstance(b, str):
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
    """landing URL incl. url_tags (Meta appends url_tags at serve time)"""
    v = get_slot(creative, slot)
    tags = creative.get('url_tags')
    if tags:
        v = v + ('&' if '?' in v else '?') + tags
    return v


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
        if a != b or type(a) != type(b):
            out.append(f'~ {path}: {json.dumps(a, ensure_ascii=False)[:300]} -> {json.dumps(b, ensure_ascii=False)[:300]}')
    return out


def load_saved(path):
    """MCP output saved by the harness: list of {type,text} blocks, or the raw JSON"""
    raw = json.load(open(path))
    if isinstance(raw, list):
        txt = ''.join(b['text'] for b in raw if isinstance(b, dict) and b.get('type') == 'text')
        return json.loads(txt)
    return raw


def has_trunc(o):
    if isinstance(o, dict):
        return any('trunc' in str(k).lower() for k in o) or any(has_trunc(v) for v in o.values())
    if isinstance(o, list):
        return any(has_trunc(v) for v in o)
    if isinstance(o, str):
        return 'MCP_OUTPUT_TRUNCATED' in o or 'more items truncated' in o or '[TRUNCATED' in o
    return False


def nonascii_report(o):
    s = json.dumps(o, ensure_ascii=False)
    seen = {}
    for ch in s:
        if ord(ch) > 127:
            seen[ch] = seen.get(ch, 0) + 1
    return sorted(('U+%04X' % ord(c), unicodedata.category(c), unicodedata.name(c, '?'), n) for c, n in seen.items())


def classify(ad_id, creative):
    u = unit(ad_id)
    res = []
    for c in u['changes']:
        try:
            cur = full_url(creative, c['slot'])
        except Exception:
            cur = None
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


def build_payload(creative, changes):
    """exact copy of the live creative (creation params only) with only the listed slots set to new"""
    unknown = [k for k in creative if k not in SEND_KEYS and k not in DERIVED]
    assert not unknown, ('unhandled creative keys', unknown)
    assert not creative.get('url_tags'), 'creative has url_tags - handle by hand'
    p = {k: copy.deepcopy(creative[k]) for k in SEND_KEYS if k in creative}
    for ch in changes:
        old = get_slot(p, ch['slot'])
        assert old == ch['now'] or old in ch['alt_now'], (ch['slot'], old)
        set_slot(p, ch['slot'], ch['new'])
    return p


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
    print('recorded', ad_id, c['slot'], result, 'after==new:', after_live == c['new'])


def progress(**kw):
    kw['ts'] = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    with open(W + 'progress.jsonl', 'a') as f:
        f.write(json.dumps(kw, ensure_ascii=False) + "\n")
