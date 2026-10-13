import json, copy, re, os, unicodedata
from urllib.parse import urlsplit, parse_qsl

ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
IN = ROOT + '/apply7/in_meta_2.json'
OUT = ROOT + '/apply7/out_meta_2.jsonl'
W = ROOT + '/apply7/meta2_work/'
EXCL = ROOT + '/work/excl_platform_refused_v2.json'
TRANSCRIPT = ('/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/'
              'wf_5a03c5af-d08/agent-addb17809a7463432.jsonl')


# ---------------------------------------------------------------- input / exclusions
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


# ---------------------------------------------------------------- transcript (exact tool results)
def _result_text(cc):
    if isinstance(cc, list):
        return ''.join(x.get('text', '') for x in cc if x.get('type') == 'text')
    if isinstance(cc, str):
        return cc
    return json.dumps(cc)


def calls():
    """[(tool_use_id, tool_name, input, result_text)] in call order, from this agent's transcript"""
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


def load_text(t):
    """parse a gateway result text; follow a persisted-output file path if the result was saved to disk"""
    try:
        return json.loads(t)
    except Exception:
        m = re.search(r'(/root/\.claude/projects/\S+?\.(?:json|txt))', t or '')
        if m:
            raw = open(m.group(1)).read()
            obj = json.loads(raw)
            if isinstance(obj, list) and obj and isinstance(obj[0], dict) and 'type' in obj[0]:
                return json.loads(''.join(b.get('text', '') for b in obj if b.get('type') == 'text'))
            return obj
        raise


def find(action=None, pred=None, nth=-1, tool_suffix='meta_native_action'):
    """the nth (default last) Whathead call with this action whose input satisfies pred -> (id, input, parsed result)"""
    hits = []
    for i, n, inp, res in calls():
        if not n.endswith(tool_suffix):
            continue
        if action and inp.get('action') != action:
            continue
        if pred and not pred(inp):
            continue
        hits.append((i, inp, res))
    if not hits:
        return None
    i, inp, res = hits[nth]
    return i, inp, (load_text(res) if res is not None else None)


def graph(parsed):
    """Graph response body inside the gateway envelope"""
    return parsed['data']['data']


# ---------------------------------------------------------------- URL slots
def same_url(a, b):
    """same scheme/host/path/fragment and the same query params in any order"""
    if a is None or b is None:
        return False
    A, B = urlsplit(a), urlsplit(b)
    return (A.scheme, A.netloc, A.path, A.fragment) == (B.scheme, B.netloc, B.path, B.fragment) and \
        sorted(parse_qsl(A.query, keep_blank_values=True)) == sorted(parse_qsl(B.query, keep_blank_values=True))


def _step(obj, part):
    m = re.fullmatch(r'(\w+)\[(\d+)\]', part)
    if m:
        return obj[m.group(1)][int(m.group(2))]
    return obj[part]


def get_slot(creative, slot):
    assert slot.startswith('creative.')
    cur = creative
    for part in slot[len('creative.'):].split('.'):
        cur = _step(cur, part)
    return cur


def set_slot(creative, slot, value):
    parts = slot[len('creative.'):].split('.')
    cur = creative
    for part in parts[:-1]:
        cur = _step(cur, part)
    last = parts[-1]
    m = re.fullmatch(r'(\w+)\[(\d+)\]', last)
    if m:
        cur[m.group(1)][int(m.group(2))] = value
    else:
        assert last in cur, (slot, 'missing leaf')
        cur[last] = value


def full_url(creative, slot):
    """landing URL of the slot incl. the creative's url_tags, if any"""
    try:
        v = get_slot(creative, slot)
    except Exception:
        return None
    tags = creative.get('url_tags')
    if tags and v is not None:
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
        elif cur is not None and (cur == c['now'] or cur in c.get('alt_now', [])):
            v = 'Write'
        else:
            v = 'Skipped'
        res.append((c, cur, v))
    return res


# ---------------------------------------------------------------- payload
# creation params copied from the creative read when present (same list the proven 11/12-Oct recipes used)
COPY_KEYS = ['name', 'object_story_spec', 'asset_feed_spec', 'url_tags', 'degrees_of_freedom_spec',
             'contextual_multi_ads', 'creative_sourcing_spec', 'format_transformation_spec',
             'media_sourcing_spec', 'threads_user_id', 'authorization_category', 'interactive_components_spec',
             'platform_customizations', 'portrait_customizations', 'ad_disclaimer_spec',
             'regional_regulation_disclaimer_spec', 'branded_content', 'facebook_branded_content',
             'instagram_branded_content', 'source_instagram_media_id', 'call_to_action', 'applink_treatment',
             'link_destination_display_url', 'omnichannel_link_spec', 'page_welcome_message', 'image_crops',
             'product_set_id', 'template_url', 'object_url', 'link_url', 'dynamic_ad_voice',
             'recommender_settings', 'playable_asset_id', 'destination_set_id', 'categorization_criteria',
             'category_media_source', 'bundle_folder_id', 'branded_content_sponsor_page_id', 'link_og_id']


def build(u, orig):
    """new-creative payload = the read creative, only the unit's URL slot(s) set to new"""
    notes = []
    p = {}
    for k in COPY_KEYS:
        if k in orig and orig[k] is not None:
            p[k] = copy.deepcopy(orig[k])
    boosted = 'source_instagram_media_id' in orig
    if boosted:
        # boosted IG post (proven recipe): page as object_id, IG identity, same media, CTA with the link
        p['object_id'] = orig['actor_id']
        if orig.get('instagram_user_id'):
            p['instagram_user_id'] = orig['instagram_user_id']
        notes.append('boosted IG post: object_id=actor page %s, instagram_user_id %s, source_instagram_media_id %s' % (
            orig.get('actor_id'), orig.get('instagram_user_id'), orig.get('source_instagram_media_id')))
    else:
        # top-level call_to_action is only an input for existing-post promotion (Meta 100/2238146 otherwise);
        # the serving CTA lives in object_story_spec / asset_feed_spec
        if 'call_to_action' in p:
            p.pop('call_to_action')
            notes.append('top-level call_to_action (read-only, derived) not sent')
    # deprecated key Meta rejects on create
    cfs = (p.get('degrees_of_freedom_spec') or {}).get('creative_features_spec') or {}
    if 'standard_enhancements' in cfs:
        notes.append('deprecated standard_enhancements %s left out (Meta rejects it on create)' %
                     cfs['standard_enhancements'].get('enroll_status'))
        del cfs['standard_enhancements']
    # derived image URLs: the hash is sent
    for sl in (p.get('creative_sourcing_spec') or {}).get('site_links_spec', []) or []:
        if sl.get('site_link_image_hash') and 'site_link_image_url' in sl:
            del sl['site_link_image_url']
    vd = (p.get('object_story_spec') or {}).get('video_data')
    if vd and vd.get('image_hash') and 'image_url' in vd:
        del vd['image_url']
        notes.append('video_data.image_url (derived from image_hash) not sent')
    for c in u['changes']:
        set_slot(p, c['slot'], c['new'])
    return p, notes


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


def dumps_safe(o):
    """compact JSON; non-ASCII letters kept, invisible/format/space chars escaped as \\uXXXX"""
    s = json.dumps(o, ensure_ascii=False, separators=(',', ':'))
    out = []
    for ch in s:
        cat = unicodedata.category(ch)
        if ord(ch) > 127 and (cat.startswith('C') or cat.startswith('Z')):
            out.append('\\u%04x' % ord(ch))
        else:
            out.append(ch)
    return ''.join(out)


# ---------------------------------------------------------------- results
def record(ad_id, change_idx, before, after_live, result, new_ids, detail):
    u = unit(ad_id)
    c = u['changes'][change_idx]
    if result == 'Fixed':
        assert after_live == c['new'], 'after mismatch'
        assert before == c['now'] or before in c.get('alt_now', []), 'before not now/alt_now'
    if result == 'AlreadyFixed':
        assert same_url(before, c['new'])
    rec = {"platform": "meta", "account_id": u['account_id'], "unit_type": u['unit_type'], "unit": u['unit'],
           "ad_ids": u['ad_ids'], "ad_names": u['ad_names'], "slot": c['slot'], "before": before,
           "after_expected": c['new'], "after_live": after_live, "result": result,
           "new_entity_ids": new_ids, "detail": detail}
    with open(OUT, 'a') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print('recorded', ad_id, c['slot'], result, 'after==new:', after_live == c['new'])
