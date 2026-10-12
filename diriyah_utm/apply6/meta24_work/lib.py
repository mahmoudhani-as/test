import json, copy, re, os, unicodedata
from urllib.parse import urlsplit, parse_qsl

ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
IN = ROOT + '/apply6/in_meta_24.json'
OUT = ROOT + '/apply6/out_meta_24.jsonl'
W = ROOT + '/apply6/meta24_work/'
EXCL = ROOT + '/work/excl_platform_refused_v2.json'
TR = '/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/tool-results/'


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
    if a is None or b is None:
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
    """landing URL incl. url_tags if any"""
    v = get_slot(creative, slot)
    tags = creative.get('url_tags')
    if tags:
        v = v + ('&' if '?' in v else '?') + tags
    return v


def classify(u, creative):
    """per change: (change, cur, verdict) with verdict AlreadyFixed / Write / Skipped / Excluded"""
    res = []
    for c in u['changes']:
        try:
            cur = full_url(creative, c['slot'])
        except Exception:
            cur = None
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
        if a != b:
            out.append(f'~ {path}: {json.dumps(a, ensure_ascii=False)[:300]} -> {json.dumps(b, ensure_ascii=False)[:300]}')
    return out


def load_tool(p):
    """load a persisted MCP tool result file; returns the gateway envelope dict"""
    if not p.startswith('/'):
        p = TR + p
    raw = json.load(open(p))
    if isinstance(raw, list):
        txt = ''.join(b.get('text', '') for b in raw if b.get('type') == 'text')
    else:
        txt = raw
    d = json.loads(txt) if isinstance(txt, str) else txt
    budget = (d.get('meta') or {}).get('mcp_output_budget')
    if budget:
        raise RuntimeError('TRUNCATED %s' % budget)
    return d


def dumps_safe(o):
    """compact JSON with non-ASCII letters kept but every invisible/format/control char escaped as \\uXXXX"""
    s = json.dumps(o, ensure_ascii=False, separators=(',', ':'))
    out = []
    for ch in s:
        cat = unicodedata.category(ch)
        if ord(ch) > 127 and (cat.startswith('C') or cat.startswith('Z')):
            out.append('\\u%04x' % ord(ch))
        else:
            out.append(ch)
    return ''.join(out)


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
    print('recorded', u['unit'], c['slot'], result, 'after==new:', after_live == c['new'])


CREATIVE_FIELDS = ("id,name,account_id,status,object_type,object_story_spec,asset_feed_spec,url_tags,"
                   "degrees_of_freedom_spec,contextual_multi_ads,creative_sourcing_spec,format_transformation_spec,"
                   "media_sourcing_spec,threads_user_id,authorization_category,interactive_components_spec,"
                   "platform_customizations,portrait_customizations,ad_disclaimer_spec,"
                   "regional_regulation_disclaimer_spec,branded_content,facebook_branded_content,"
                   "instagram_branded_content,source_instagram_media_id,call_to_action,call_to_action_type,"
                   "applink_treatment,link_destination_display_url,omnichannel_link_spec,page_welcome_message,"
                   "image_crops,object_story_id,effective_object_story_id,object_id,actor_id,instagram_user_id,"
                   "effective_instagram_media_id,link_url,object_url,title,body,image_hash,video_id,product_set_id,"
                   "template_url_spec,use_page_actor_override,categorization_criteria,dynamic_ad_voice,"
                   "place_page_set_id,recommender_settings,bundle_folder_id,destination_set_id,link_og_id")


# ---- payload building (copy of the live creative; only the listed URL slot(s) changed) ----
DROP_TOP = {'id', 'account_id', 'actor_id', 'object_type', 'status', 'effective_object_story_id',
            'effective_instagram_media_id', 'use_page_actor_override', 'object_story_id'}
KEEP_TOP = ['name', 'object_story_spec', 'asset_feed_spec', 'degrees_of_freedom_spec', 'portrait_customizations',
            'format_transformation_spec', 'contextual_multi_ads', 'creative_sourcing_spec', 'media_sourcing_spec',
            'threads_user_id', 'authorization_category', 'url_tags', 'platform_customizations',
            'interactive_components_spec', 'ad_disclaimer_spec', 'regional_regulation_disclaimer_spec',
            'branded_content', 'facebook_branded_content', 'instagram_branded_content',
            'link_destination_display_url', 'applink_treatment', 'page_welcome_message', 'omnichannel_link_spec']


def build_payload(creative, changes):
    notes = []
    unknown = [k for k in creative if k not in DROP_TOP and k not in KEEP_TOP and k != 'instagram_user_id']
    assert not unknown, ('unhandled creative fields', unknown)
    # top-level instagram_user_id is derived; it must equal the one in object_story_spec
    if 'instagram_user_id' in creative:
        assert creative.get('object_story_spec', {}).get('instagram_user_id') == creative['instagram_user_id'], \
            'top-level instagram_user_id differs from object_story_spec'
    if creative.get('use_page_actor_override') not in (None, False):
        raise AssertionError('use_page_actor_override is not false')
    p = {}
    for k in KEEP_TOP:
        if k in creative:
            p[k] = copy.deepcopy(creative[k])
    for ch in changes:
        old = full_url(creative, ch['slot'])
        assert old == ch['now'] or old in ch['alt_now'], (ch['slot'], old)
        set_slot(p, ch['slot'], ch['new'])
    if p.get('url_tags'):
        raise AssertionError('url_tags present: handle by hand')
    return p, notes


def expected_new(creative, changes):
    """old creative with only the slot(s) changed - for comparison with the read-back"""
    c = copy.deepcopy(creative)
    for ch in changes:
        set_slot(c, ch['slot'], ch['new'])
    return c


def my_transcript():
    return ('/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/'
            'wf_1fef16cf-fba/agent-ace94e9bd62974289.jsonl')


def transcript_calls(action=None):
    """(tool_use input, tool_result text) pairs for Whathead calls in this agent's own transcript"""
    uses, results = {}, {}
    order = []
    for line in open(my_transcript()):
        try:
            r = json.loads(line)
        except Exception:
            continue
        msg = r.get('message') or {}
        content = msg.get('content') if isinstance(msg, dict) else None
        if not isinstance(content, list):
            continue
        for c in content:
            if c.get('type') == 'tool_use' and 'Whathed' in c.get('name', ''):
                uses[c['id']] = c.get('input', {})
                order.append(c['id'])
            elif c.get('type') == 'tool_result':
                cc = c.get('content')
                if isinstance(cc, list):
                    txt = ''.join(x.get('text', '') for x in cc if x.get('type') == 'text')
                else:
                    txt = cc
                results[c.get('tool_use_id')] = txt
    out = []
    for i in order:
        if action is None or uses[i].get('action') == action:
            out.append((i, uses[i], results.get(i)))
    return out
