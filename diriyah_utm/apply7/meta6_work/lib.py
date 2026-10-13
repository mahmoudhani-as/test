import json, copy, re, os, unicodedata
from urllib.parse import urlsplit, parse_qsl

ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
IN = ROOT + '/apply7/in_meta_6.json'
OUT = ROOT + '/apply7/out_meta_6.jsonl'
W = ROOT + '/apply7/meta6_work/'
EXCL = ROOT + '/work/excl_platform_refused_v2.json'
TRANSCRIPT = ('/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/'
              'wf_5a03c5af-d08/agent-ad2d54d939fb6a58d.jsonl')


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
    try:
        v = get_slot(creative, slot)
    except Exception:
        return None
    tags = creative.get('url_tags')
    if tags and v is not None:
        v = v + ('&' if '?' in v else '?') + tags
    return v


def classify(u, creative):
    out = []
    for c in u['changes']:
        cur = full_url(creative, c['slot'])
        if excluded(u['unit'], c['slot']):
            v = 'EXCLUDED'
        elif cur is not None and same_url(cur, c['new']):
            v = 'AlreadyFixed'
        elif cur == c['now'] or cur in c['alt_now']:
            v = 'Write'
        else:
            v = 'Skipped'
        out.append((c['slot'], v, cur))
    return out


# ---------- transcript access (exact raw tool results, no manual transcription) ----------
def transcript_calls(action=None):
    uses, results, order = {}, {}, []
    for line in open(TRANSCRIPT):
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


def parse_result(txt):
    """tool result text -> JSON (handles results saved to a file)"""
    try:
        return json.loads(txt)
    except Exception:
        pass
    m = re.search(r'(/[^\s"\']+\.(?:json|txt))', txt or '')
    if m and os.path.exists(m.group(1)):
        raw = open(m.group(1)).read()
        try:
            j = json.loads(raw)
            if isinstance(j, list) and j and isinstance(j[0], dict) and 'text' in j[0]:
                return json.loads(''.join(b['text'] for b in j if b.get('type') == 'text'))
            return j
        except Exception:
            pass
    raise ValueError('cannot parse result: %r' % (txt or '')[:300])


def last_ad_read(ad_id, k=1):
    """k-th last meta_ad_id_get result for ad_id -> ad dict"""
    calls = [c for c in transcript_calls('meta_ad_id_get')
             if str((c[1].get('path_params') or {}).get('ad_id')) == str(ad_id) and c[2]]
    i, inp, txt = calls[-k]
    r = parse_result(txt)
    return r['data']['data'], inp


def last_creative_read(cid, k=1):
    calls = [c for c in transcript_calls()
             if c[1].get('action') in ('meta_ad_creative_id_get', 'meta_creative_id_get', 'meta_creative_get',
                                       'meta_ad_creative_get')
             and str((c[1].get('path_params') or {}).get(next(iter(c[1].get('path_params') or {'x': 0})))) == str(cid)
             and c[2]]
    i, inp, txt = calls[-k]
    r = parse_result(txt)
    return r['data']['data'], inp


# ---------- payload ----------
DROP_TOP = {'id', 'account_id', 'actor_id', 'object_type', 'status', 'effective_object_story_id',
            'effective_instagram_media_id', 'use_page_actor_override', 'object_story_id', 'instagram_user_id'}
# derived mirrors of object_story_spec (dropped only when object_story_spec carries them)
DERIVED_MIRRORS = {'body', 'title', 'image_hash', 'call_to_action', 'image_crops', 'video_id', 'link_url',
                   'object_url', 'call_to_action_type'}
KEEP_TOP = ['name', 'object_story_spec', 'asset_feed_spec', 'degrees_of_freedom_spec', 'portrait_customizations',
            'format_transformation_spec', 'contextual_multi_ads', 'creative_sourcing_spec', 'media_sourcing_spec',
            'threads_user_id', 'authorization_category', 'url_tags', 'platform_customizations',
            'interactive_components_spec', 'ad_disclaimer_spec', 'regional_regulation_disclaimer_spec',
            'branded_content', 'facebook_branded_content', 'instagram_branded_content',
            'link_destination_display_url', 'applink_treatment', 'page_welcome_message', 'omnichannel_link_spec',
            'source_instagram_media_id']


def build_payload(creative, changes):
    notes = []
    unknown = [k for k in creative if k not in DROP_TOP and k not in KEEP_TOP and k not in DERIVED_MIRRORS]
    assert not unknown, ('unhandled creative fields', unknown)
    if 'instagram_user_id' in creative and creative.get('object_story_spec'):
        oss_ig = creative['object_story_spec'].get('instagram_user_id')
        if oss_ig is not None:
            assert oss_ig == creative['instagram_user_id'], 'top-level instagram_user_id differs from object_story_spec'
        else:
            notes.append('top-level instagram_user_id %s not in object_story_spec' % creative['instagram_user_id'])
    if creative.get('use_page_actor_override') not in (None, False):
        raise AssertionError('use_page_actor_override is not false')
    if 'source_instagram_media_id' in creative:
        raise AssertionError('boosted IG post: handle by hand')
    p = {}
    for k in KEEP_TOP:
        if k in creative:
            p[k] = copy.deepcopy(creative[k])
    # check that top-level mirrors are really mirrors of object_story_spec
    oss = creative.get('object_story_spec', {})
    ld = oss.get('link_data') or oss.get('video_data') or {}
    mirror_map = {'call_to_action': ld.get('call_to_action'), 'image_hash': ld.get('image_hash'),
                  'image_crops': ld.get('image_crops'), 'video_id': ld.get('video_id')}
    for k in DERIVED_MIRRORS:
        if k in creative:
            if k in mirror_map and mirror_map[k] is not None:
                assert creative[k] == mirror_map[k] or k == 'call_to_action', ('mirror differs', k, creative[k], mirror_map[k])
            notes.append('derived top-level %s not sent' % k)
    # deprecated key rejected on create
    dof = p.get('degrees_of_freedom_spec', {}).get('creative_features_spec', {})
    if 'standard_enhancements' in dof:
        dof.pop('standard_enhancements')
        notes.append('deprecated standard_enhancements key left out (Meta rejects it on create)')
    css = p.get('creative_sourcing_spec')
    if css and 'site_links_spec' in css:
        for sl in css['site_links_spec']:
            if 'site_link_image_hash' in sl and 'site_link_image_url' in sl:
                sl.pop('site_link_image_url', None)
    vd = p.get('object_story_spec', {}).get('video_data')
    if vd and 'image_hash' in vd and 'image_url' in vd:
        vd.pop('image_url', None)
        notes.append('video_data.image_url (signed CDN copy of image_hash) not sent')
    for ch in changes:
        old = full_url(creative, ch['slot'])
        assert old == ch['now'] or old in ch['alt_now'], (ch['slot'], old)
        set_slot(p, ch['slot'], ch['new'])
    if p.get('url_tags'):
        raise AssertionError('url_tags present: handle by hand')
    return p, notes


def expected_new(creative, changes):
    c = copy.deepcopy(creative)
    for ch in changes:
        set_slot(c, ch['slot'], ch['new'])
    return c


def diff(a, b, path=''):
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append('+ %s.%s = %s' % (path, k, json.dumps(b[k], ensure_ascii=False)[:300]))
            elif k not in b:
                out.append('- %s.%s = %s' % (path, k, json.dumps(a[k], ensure_ascii=False)[:300]))
            else:
                out += diff(a[k], b[k], '%s.%s' % (path, k))
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append('~ %s len %d -> %d' % (path, len(a), len(b)))
        for i, (x, y) in enumerate(zip(a, b)):
            out += diff(x, y, '%s[%d]' % (path, i))
    else:
        if a != b:
            out.append('~ %s: %s -> %s' % (path, json.dumps(a, ensure_ascii=False)[:300], json.dumps(b, ensure_ascii=False)[:300]))
    return out


def dumps_safe(o):
    """compact JSON; non-ASCII letters kept, every invisible/format/space char escaped as \\uXXXX"""
    s = json.dumps(o, ensure_ascii=False, separators=(',', ':'))
    out = []
    for ch in s:
        cat = unicodedata.category(ch)
        if ord(ch) > 127 and (cat.startswith('C') or cat.startswith('Z') or cat == 'Mn'):
            out.append('\\u%04x' % ord(ch))
        else:
            out.append(ch)
    return ''.join(out)


def has_invisible(o):
    s = json.dumps(o, ensure_ascii=False)
    return sorted({'U+%04X' % ord(ch) for ch in s if ord(ch) > 127 and unicodedata.category(ch)[0] in 'CZ'})


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
    print('recorded', u['unit'], c['slot'], result, 'after==new:', after_live == c['new'])


def progress(**kw):
    import datetime
    kw['ts'] = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    with open(W + 'progress.jsonl', 'a') as f:
        f.write(json.dumps(kw, ensure_ascii=False) + '\n')


def last_create_call(k=1):
    calls = [c for c in transcript_calls('meta_ad_account_id_adcreatives_create') if c[2]]
    i, inp, txt = calls[-k]
    return inp, parse_result(txt)


def check_dry(ad_id):
    """compare the last dry-run create call (sent payload and previewed body) with payload_<ad>.json"""
    p = json.load(open(W + 'payload_%s.json' % ad_id))
    inp, r = last_create_call()
    assert inp.get('dry_run') is True, 'last create call was not a dry run'
    sent = inp['payload']
    body = r['data']['data']['request']['body']
    d1 = diff(p, sent)
    d2 = diff(p, body)
    print('sent == payload file:', not d1, d1[:5])
    print('dry-run body == payload file:', not d2, d2[:5])
    print('dry-run url:', r['data']['data']['request']['url'], '| warnings:', r['data']['data'].get('warnings'))
    return not d1 and not d2
