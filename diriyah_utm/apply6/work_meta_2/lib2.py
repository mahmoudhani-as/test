import json, copy, re, sys, os
from urllib.parse import urlsplit, parse_qsl

ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
IN = ROOT + '/apply6/in_meta_2.json'
OUT = ROOT + '/apply6/out_meta_2.jsonl'
WORK = ROOT + '/apply6/work_meta_2'
TR = '/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/tool-results/'


def units():
    return json.load(open(IN))


def unit(ad_id):
    for u in units():
        if u['unit'] == ad_id:
            return u
    raise KeyError(ad_id)


def preread():
    return {a['id']: a for a in json.load(open(WORK + '/preread_ads.json'))}


def load_tool(p):
    """load a persisted MCP tool result; returns the inner gateway 'data' object; raises if truncated"""
    if not p.startswith('/'):
        p = TR + p
    raw = json.load(open(p))
    txt = raw[0]['text'] if isinstance(raw, list) else raw
    d = json.loads(txt) if isinstance(txt, str) else txt
    budget = (d.get('meta') or {}).get('mcp_output_budget')
    if budget:
        raise RuntimeError('TRUNCATED %s' % budget)
    return d['data']


def same_url(a, b):
    if a is None or b is None:
        return False
    A, B = urlsplit(a), urlsplit(b)
    return (A.scheme, A.netloc, A.path, A.fragment) == (B.scheme, B.netloc, B.path, B.fragment) and \
        sorted(parse_qsl(A.query, keep_blank_values=True)) == sorted(parse_qsl(B.query, keep_blank_values=True))


def _walk(obj, slot):
    assert slot.startswith('creative.')
    parts = slot[len('creative.'):].split('.')
    return parts


def get_slot(creative, slot):
    cur = creative
    for part in _walk(creative, slot):
        m = re.fullmatch(r'(\w+)\[(\d+)\]', part)
        if m:
            cur = cur[m.group(1)][int(m.group(2))]
        else:
            cur = cur[part]
    return cur


def set_slot(creative, slot, value):
    parts = _walk(creative, slot)
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
        elif cur == c['now'] or cur in c['alt_now']:
            v = 'Write'
        else:
            v = 'Skipped'
        res.append((c, cur, v))
    return res


# creation params copied from the read when present
COPY_KEYS = ['name', 'object_story_spec', 'asset_feed_spec', 'url_tags', 'degrees_of_freedom_spec',
             'contextual_multi_ads', 'creative_sourcing_spec', 'format_transformation_spec',
             'media_sourcing_spec', 'threads_user_id', 'authorization_category', 'interactive_components_spec',
             'platform_customizations', 'portrait_customizations', 'ad_disclaimer_spec',
             'regional_regulation_disclaimer_spec', 'branded_content', 'facebook_branded_content',
             'instagram_branded_content', 'source_instagram_media_id', 'applink_treatment',
             'link_destination_display_url', 'omnichannel_link_spec', 'page_welcome_message', 'image_crops',
             'product_set_id', 'template_url', 'object_url', 'link_url', 'dynamic_ad_voice',
             'recommender_settings', 'playable_asset_id', 'destination_set_id', 'categorization_criteria',
             'category_media_source', 'bundle_folder_id', 'branded_content_sponsor_page_id', 'link_og_id']

THUMBS = json.load(open(WORK + '/thumbs_fullres.json'))


def base_file(url):
    return urlsplit(url).path.rsplit('/', 1)[-1]


def build(u, orig):
    notes = []
    p = {}
    for k in COPY_KEYS:
        if k in orig and orig[k] is not None:
            p[k] = copy.deepcopy(orig[k])
    oss = p.get('object_story_spec', {})
    # Instagram identity: keep it where the read has it. When object_story_spec has no instagram_user_id
    # but the creative carries a top-level instagram_user_id, send that top-level field as read.
    if 'instagram_user_id' not in oss and orig.get('instagram_user_id'):
        p['instagram_user_id'] = orig['instagram_user_id']
        notes.append('top-level instagram_user_id %s kept as read (object_story_spec has page_id only)' % orig['instagram_user_id'])
    # deprecated key Meta rejects on create
    cfs = p.get('degrees_of_freedom_spec', {}).get('creative_features_spec', {})
    if 'standard_enhancements' in cfs:
        notes.append('deprecated standard_enhancements %s left out (Meta rejects it on create)' % cfs['standard_enhancements'].get('enroll_status'))
        del cfs['standard_enhancements']
    # video_data: image_url is derived from image_hash; send the hash only
    vd = oss.get('video_data')
    if vd and vd.get('image_hash') and 'image_url' in vd:
        del vd['image_url']
        notes.append('video_data.image_url (derived from image_hash) not sent; image_hash sent')
    # site links: image url is derived from the hash
    for sl in (p.get('creative_sourcing_spec') or {}).get('site_links_spec', []) or []:
        if sl.get('site_link_image_hash') and 'site_link_image_url' in sl:
            del sl['site_link_image_url']
    # asset_feed_spec video thumbnails: the read returns a small rendition URL of the video's own preferred
    # thumbnail; send the full-resolution URI of the same image file instead
    for v in (p.get('asset_feed_spec') or {}).get('videos', []) or []:
        if 'thumbnail_url' in v:
            bf = base_file(v['thumbnail_url'])
            if bf in THUMBS:
                v['thumbnail_url'] = THUMBS[bf]['uri']
                notes.append('video %s thumbnail: full-res URI of the same image file %s' % (v['video_id'], bf))
            else:
                notes.append('video %s thumbnail: NO full-res match for %s, read URL kept' % (v['video_id'], bf))
    for c in u['changes']:
        set_slot(p, c['slot'], c['new'])
    return p, notes


def record(u, change_idx, before, after_live, result, new_ids, detail):
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
    print('recorded', u['unit'], result, 'after==new:', after_live == c['new'])


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
