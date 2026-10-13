import json, re, copy, datetime
from urllib.parse import urlsplit, parse_qsl

ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
IN = ROOT + '/apply7/in_meta_11.json'
OUT = ROOT + '/apply7/out_meta_11.jsonl'
WORK = ROOT + '/apply7/meta11_work'
EXCL = ROOT + '/work/excl_platform_refused_v2.json'
PROG = WORK + '/progress.jsonl'


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


def get_path(obj, path):
    cur = obj
    for part in path.split('.'):
        cur = _walk(cur, part)
    return cur


def get_slot(creative, slot):
    assert slot.startswith('creative.')
    return get_path(creative, slot[len('creative.'):])


def full_url(creative, slot):
    """landing URL incl. url_tags if the creative has them"""
    u = get_slot(creative, slot)
    tags = creative.get('url_tags')
    if tags:
        u = u + ('&' if '?' in u else '?') + tags
    return u


def classify(ad_id, slot, cur):
    u = unit(ad_id)
    c = [c for c in u['changes'] if c['slot'] == slot][0]
    if excluded(ad_id, slot):
        return 'Excluded'
    if same_url(cur, c['new']):
        return 'AlreadyFixed'
    if cur == c['now'] or cur in c['alt_now']:
        return 'Write'
    return 'Skipped'


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
            out.append(f'~ {path}: {json.dumps(a, ensure_ascii=False)[:400]} -> {json.dumps(b, ensure_ascii=False)[:400]}')
    return out


# read-only / derived creative fields that are never sent on create
SKIP_KEYS = ['id', 'account_id', 'status', 'actor_id', 'object_type', 'effective_authorization_category',
             'effective_object_story_id', 'effective_instagram_media_id', 'thumbnail_url', 'use_page_actor_override',
             'instagram_user_id', 'image_url', 'instagram_permalink_url', 'link_og_id', 'adlabels']


def settable(creative):
    return {k: v for k, v in creative.items() if k not in SKIP_KEYS}


def check_payload(orig_creative, payload, ad_id):
    """diff of the settable part of the live creative vs the payload; only the unit's URL slot(s) may differ"""
    u = unit(ad_id)
    expect = copy.deepcopy(settable(orig_creative))
    for c in u['changes']:
        path = c['slot'][len('creative.'):]
        parts = path.split('.')
        cur = expect
        for part in parts[:-1]:
            cur = _walk(cur, part)
        last = parts[-1]
        m = re.fullmatch(r'(\w+)\[(\d+)\]', last)
        if m:
            cur[m.group(1)][int(m.group(2))] = c['new']
        else:
            assert last in cur, (path, 'missing leaf')
            cur[last] = c['new']
    return diff(expect, payload)


def progress(**kw):
    kw['ts'] = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    with open(PROG, 'a') as f:
        f.write(json.dumps(kw, ensure_ascii=False) + '\n')


def record(ad_id, slot, before, after_live, result, new_ids, detail):
    u = unit(ad_id)
    c = [c for c in u['changes'] if c['slot'] == slot][0]
    if result == 'Fixed':
        assert after_live == c['new'], 'after_live != new'
        assert before == c['now'] or before in c['alt_now'], 'before not now/alt_now'
    if result == 'AlreadyFixed':
        assert same_url(before, c['new'])
    rec = {"platform": "meta", "account_id": u['account_id'], "unit_type": u['unit_type'], "unit": u['unit'],
           "ad_ids": u['ad_ids'], "ad_names": u['ad_names'], "slot": slot, "before": before,
           "after_expected": c['new'], "after_live": after_live, "result": result,
           "new_entity_ids": new_ids, "detail": detail}
    with open(OUT, 'a') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print('recorded', ad_id, slot, result, 'after==new:', after_live == c['new'])
