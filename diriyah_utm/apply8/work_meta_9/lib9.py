"""Read-only helpers for apply8 lane in_meta_9 (local parsing of this agent's own Whathead results).
Nothing here calls an API; it only reads the input file, the exclusions list and this agent's transcript,
and writes small work files into work_meta_9/."""
import json, copy, re, os, unicodedata
from urllib.parse import urlsplit, parse_qsl

ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
IN = ROOT + '/apply8/in_meta_9.json'
W = ROOT + '/apply8/work_meta_9/'
EXCL = ROOT + '/work/excl_platform_refused_v2.json'
TRANSCRIPT = ('/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/'
              'wf_68a96956-5be/agent-a5198b087501a4ec1.jsonl')


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
        except Exception:
            return None
        if isinstance(j, list) and j and isinstance(j[0], dict) and 'text' in j[0]:
            return json.loads(''.join(b['text'] for b in j if b.get('type') == 'text'))
        return j
    return None


def last_ad_read(ad_id, k=1):
    """k-th last meta_ad_id_get result for ad_id -> (ad dict, input, request id)"""
    calls = [c for c in transcript_calls('meta_ad_id_get')
             if str((c[1].get('path_params') or {}).get('ad_id')) == str(ad_id) and c[2]]
    i, inp, txt = calls[-k]
    r = parse_result(txt)
    return r['data']['data'], inp, (r.get('meta') or {}).get('requestId')


def last_creative_read(cid, k=1):
    calls = [c for c in transcript_calls('meta_creative_id_get')
             if str((c[1].get('path_params') or {}).get('creative_id')) == str(cid) and c[2]]
    i, inp, txt = calls[-k]
    r = parse_result(txt)
    return r['data']['data'], inp, (r.get('meta') or {}).get('requestId')


def last_call(action, k=1):
    calls = [c for c in transcript_calls(action) if c[2]]
    i, inp, txt = calls[-k]
    return inp, parse_result(txt), txt


# ---------- payload ----------
DROP_TOP = {'id', 'account_id', 'actor_id', 'object_type', 'status', 'effective_object_story_id',
            'effective_instagram_media_id', 'use_page_actor_override', 'object_story_id', 'instagram_user_id',
            'effective_authorization_category'}
# derived mirrors of object_story_spec / asset_feed_spec (never sent)
DERIVED_MIRRORS = {'body', 'title', 'image_hash', 'call_to_action', 'image_crops', 'video_id', 'link_url',
                   'object_url', 'call_to_action_type', 'object_id'}
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
    for k in DERIVED_MIRRORS:
        if k in creative:
            notes.append('derived top-level %s not sent' % k)
    dof = p.get('degrees_of_freedom_spec', {}).get('creative_features_spec', {})
    if 'standard_enhancements' in dof:
        raise AssertionError('deprecated standard_enhancements present: handle by hand')
    css = p.get('creative_sourcing_spec')
    if css and 'site_links_spec' in css:
        raise AssertionError('site_links_spec present: handle by hand')
    vd = p.get('object_story_spec', {}).get('video_data')
    if vd and 'image_hash' in vd and 'image_url' in vd:
        vd.pop('image_url', None)
        notes.append('video_data.image_url (derived signed copy of image_hash) not sent')
    for ch in changes:
        old = full_url(creative, ch['slot'])
        assert old == ch['now'] or old in ch['alt_now'], (ch['slot'], old)
        set_slot(p, ch['slot'], ch['new'])
    if p.get('url_tags'):
        raise AssertionError('url_tags present: handle by hand')
    return p, notes


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
        if a != b or type(a) != type(b):
            out.append('~ %s: %s -> %s' % (path, json.dumps(a, ensure_ascii=False)[:300], json.dumps(b, ensure_ascii=False)[:300]))
    return out


def has_invisible(o):
    s = json.dumps(o, ensure_ascii=False)
    return sorted({'U+%04X' % ord(ch) for ch in s if ord(ch) > 127 and unicodedata.category(ch)[0] in 'CZ'})


def big_ints(o, path=''):
    """numbers (not strings) larger than 2**53 anywhere in o"""
    out = []
    if isinstance(o, dict):
        for k, v in o.items():
            out += big_ints(v, path + '.' + k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            out += big_ints(v, '%s[%d]' % (path, i))
    elif isinstance(o, (int, float)) and not isinstance(o, bool) and abs(o) > 2 ** 53:
        out.append((path, o))
    return out


def dumps_safe(o):
    """compact JSON; non-ASCII letters kept, every combining/invisible/format/space char escaped as \\uXXXX"""
    s = json.dumps(o, ensure_ascii=False, separators=(',', ':'))
    out = []
    for ch in s:
        cat = unicodedata.category(ch)
        if ord(ch) > 127 and (cat.startswith('C') or cat.startswith('Z') or cat.startswith('M')):
            out.append('\\u%04x' % ord(ch))
        else:
            out.append(ch)
    return ''.join(out)


# ---------- label-keyed comparison (Meta may return asset_feed_spec arrays in a different order) ----------
def _lab(x):
    if isinstance(x, dict) and x.get('adlabels'):
        return ','.join(sorted(str(l.get('id')) for l in x['adlabels']))
    return json.dumps(x, sort_keys=True, ensure_ascii=False)


def canon(cr):
    c = copy.deepcopy(cr)
    afs = c.get('asset_feed_spec')
    if isinstance(afs, dict):
        for k in ('images', 'videos', 'bodies', 'titles', 'descriptions', 'link_urls', 'carousels'):
            if isinstance(afs.get(k), list):
                afs[k] = sorted(afs[k], key=_lab)
        if isinstance(afs.get('asset_customization_rules'), list):
            afs['asset_customization_rules'] = sorted(afs['asset_customization_rules'],
                                                      key=lambda r: (r.get('priority', 0), json.dumps(r, sort_keys=True)))
    return c


def url_by_label(cr):
    out = {}
    for l in (cr.get('asset_feed_spec') or {}).get('link_urls', []) or []:
        out[_lab(l)] = l.get('website_url')
    return out
