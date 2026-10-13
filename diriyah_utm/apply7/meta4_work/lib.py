import json, copy, re, os, sys, unicodedata
from urllib.parse import urlsplit, parse_qsl

ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
IN = ROOT + '/apply7/in_meta_4.json'
OUT = ROOT + '/apply7/out_meta_4.jsonl'
W = ROOT + '/apply7/meta4_work/'
EXCL = ROOT + '/work/excl_platform_refused_v2.json'


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
        if a != b:
            out.append(f'~ {path}: {json.dumps(a, ensure_ascii=False)[:300]} -> {json.dumps(b, ensure_ascii=False)[:300]}')
    return out


def load_raw(path, content_length=None):
    """raw Graph body transcribed from a batch GET; checks UTF-8 byte length against Content-Length"""
    b = open(path, 'rb').read()
    if b.endswith(b'\n'):
        b = b[:-1]
    n = len(b)
    if content_length is not None:
        print(path.split('/')[-1], 'bytes', n, 'Content-Length', content_length, 'MATCH' if n == content_length else 'MISMATCH')
    return json.loads(b.decode('utf-8')), n


def invisible(o, path=''):
    """list non-ASCII format/space/control chars inside strings"""
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


def dumps_safe(o, indent=None):
    """JSON with non-ASCII letters kept but every invisible/format char escaped as \\uXXXX"""
    s = json.dumps(o, ensure_ascii=False, separators=(',', ':') if indent is None else None, indent=indent)
    out = []
    for ch in s:
        cat = unicodedata.category(ch)
        if ord(ch) > 127 and (cat.startswith('C') or cat.startswith('Z')):
            out.append('\\u%04x' % ord(ch))
        else:
            out.append(ch)
    return ''.join(out)


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
    import datetime
    kw['ts'] = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    with open(W + 'progress.jsonl', 'a') as f:
        f.write(json.dumps(kw, ensure_ascii=False) + "\n")
