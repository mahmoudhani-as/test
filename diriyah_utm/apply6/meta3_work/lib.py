import json, copy, re, sys, os
from urllib.parse import urlsplit, parse_qsl

ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
IN = ROOT + '/apply6/in_meta_3.json'
OUT = ROOT + '/apply6/out_meta_3.jsonl'
WORK = ROOT + '/apply6/meta3_work'


def units():
    return json.load(open(IN))


def unit(ad_id):
    for u in units():
        if u['unit'] == ad_id:
            return u
    raise KeyError(ad_id)


def same_url(a, b):
    """same scheme/host/path/fragment and the same query params in any order"""
    if a is None or b is None:
        return False
    A, B = urlsplit(a), urlsplit(b)
    return (A.scheme, A.netloc, A.path, A.fragment) == (B.scheme, B.netloc, B.path, B.fragment) and \
        sorted(parse_qsl(A.query, keep_blank_values=True)) == sorted(parse_qsl(B.query, keep_blank_values=True))


def get_slot(creative, slot):
    """slot like creative.asset_feed_spec.link_urls[0].website_url"""
    assert slot.startswith('creative.')
    cur = creative
    for part in slot[len('creative.'):].split('.'):
        m = re.fullmatch(r'(\w+)\[(\d+)\]', part)
        if m:
            cur = cur[m.group(1)][int(m.group(2))]
        else:
            cur = cur[part]
    return cur


def set_slot(creative, slot, value):
    parts = slot[len('creative.'):].split('.')
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


def classify(ad_id, creative):
    """returns list of (change, cur, verdict) where verdict in AlreadyFixed/Write/Skipped"""
    u = unit(ad_id)
    res = []
    for c in u['changes']:
        try:
            cur = get_slot(creative, c['slot'])
        except Exception as e:
            cur = None
        if cur is not None and same_url(cur, c['new']):
            v = 'AlreadyFixed'
        elif cur == c['now'] or cur in c['alt_now']:
            v = 'Write'
        else:
            v = 'Skipped'
        res.append((c, cur, v))
    return res


# creative fields copied into the create payload when present in the read
COPY_KEYS = ['name', 'object_story_spec', 'asset_feed_spec', 'url_tags', 'degrees_of_freedom_spec',
             'contextual_multi_ads', 'creative_sourcing_spec', 'format_transformation_spec',
             'media_sourcing_spec', 'threads_user_id', 'authorization_category', 'interactive_components_spec',
             'platform_customizations', 'portrait_customizations', 'ad_disclaimer_spec',
             'regional_regulation_disclaimer_spec', 'branded_content', 'facebook_branded_content',
             'instagram_branded_content', 'source_instagram_media_id', 'call_to_action', 'applink_treatment',
             'link_destination_display_url', 'omnichannel_link_spec', 'page_welcome_message', 'image_crops']


def build(ad_id, orig):
    u = unit(ad_id)
    p = {}
    notes = []
    for k in COPY_KEYS:
        if k in orig:
            p[k] = copy.deepcopy(orig[k])
    # top-level call_to_action is only an input for boosted IG posts; otherwise it is derived from object_story_spec
    # Meta: "Call to Action field must be used with existing post promotion" (100/2238146) -> only for boosted posts
    if 'source_instagram_media_id' not in orig:
        p.pop('call_to_action', None)
    # deprecated key Meta rejects on create (12-Oct experience)
    cfs = p.get('degrees_of_freedom_spec', {}).get('creative_features_spec', {})
    if 'standard_enhancements' in cfs:
        notes.append('standard_enhancements=' + json.dumps(cfs['standard_enhancements']))
        del cfs['standard_enhancements']
    # site_link_image_url is derived from site_link_image_hash
    for s in p.get('creative_sourcing_spec', {}).get('site_links_spec', []) or []:
        if 'site_link_image_url' in s and 'site_link_image_hash' in s:
            del s['site_link_image_url']
    for c in u['changes']:
        set_slot(p, c['slot'], c['new'])
    if notes:
        print('NOTE dropped:', notes)
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
    print('recorded', ad_id, result, 'after==new:', after_live == c['new'])


def diff(a, b, path=''):
    """structural diff, returns list of strings"""
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
            out.append(f'~ {path}: {json.dumps(a, ensure_ascii=False)[:250]} -> {json.dumps(b, ensure_ascii=False)[:250]}')
    return out
