import json, copy, re, unicodedata
from urllib.parse import urlsplit, parse_qsl

ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
IN = ROOT + '/apply8/in_meta_3.json'
W = ROOT + '/apply8/work_meta_3/'
EXCL = ROOT + '/work/excl_platform_refused_v2.json'

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
           'thumbnail_id', 'instagram_permalink_url'}


def units():
    return json.load(open(IN))


def unit(ad_id):
    for u in units():
        if u['unit'] == ad_id:
            return u
    raise KeyError(ad_id)


def excluded(ad_id, slot):
    return any(str(x.get('ad_id')) == str(ad_id) and x.get('slot') == slot for x in json.load(open(EXCL)))


def same_url(a, b):
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
        if excluded(u['unit'], c['slot']):
            v = 'Excluded'
        elif cur is not None and same_url(cur, c['new']):
            v = 'AlreadyFixed'
        elif cur is not None and (cur == c['now'] or cur in c['alt_now']):
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


def invisible(o, path=''):
    out = []
    if isinstance(o, dict):
        for k, v in o.items():
            out += invisible(v, f'{path}.{k}')
    elif isinstance(o, list):
        for i, v in enumerate(o):
            out += invisible(v, f'{path}[{i}]')
    elif isinstance(o, str):
        for i, ch in enumerate(o):
            cat = unicodedata.category(ch)
            if ord(ch) > 127 and (cat.startswith('C') or cat.startswith('Z')):
                out.append((path, i, 'U+%04X' % ord(ch), unicodedata.name(ch, '?')))
    return out
