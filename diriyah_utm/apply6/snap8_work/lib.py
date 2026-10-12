import json, os, sys, unicodedata, copy
from urllib.parse import urlsplit, parse_qsl

T = '/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/wf_22c449ac-41f/agent-a639731d613f797e3.jsonl'
BASE = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6'
WD = BASE + '/snap8_work'
IN = BASE + '/in_snapchat_8.json'
OUT = BASE + '/out_snapchat_8.jsonl'


def units():
    return json.load(open(IN))


def raw_result(marker):
    """Return the parsed JSON text of the tool_result in this transcript that contains marker (last one wins)."""
    found = None
    with open(T) as f:
        for line in f:
            if marker not in line:
                continue
            o = json.loads(line)
            c = (o.get('message') or {}).get('content')
            if not isinstance(c, list):
                continue
            for x in c:
                if x.get('type') != 'tool_result':
                    continue
                cc = x.get('content')
                texts = [y.get('text', '') for y in cc] if isinstance(cc, list) else [cc or '']
                for t in texts:
                    if marker in t:
                        found = json.loads(t)
    if found is None:
        raise KeyError(marker)
    return found


def creatives_from(res):
    d = res['data']['data']
    out = []
    for x in d['creatives']:
        if x.get('sub_request_status') != 'SUCCESS':
            raise ValueError('sub_request not SUCCESS: %r' % x)
        out.append(x['creative'])
    return out


def url_same(a, b):
    """same scheme/host/path/fragment and same query params in any order"""
    if a is None or b is None:
        return False
    A, B = urlsplit(a), urlsplit(b)
    return ((A.scheme, A.netloc, A.path, A.fragment) == (B.scheme, B.netloc, B.path, B.fragment)
            and sorted(parse_qsl(A.query, keep_blank_values=True)) == sorted(parse_qsl(B.query, keep_blank_values=True)))


def classify(cur, ch):
    if cur == ch['new'] or url_same(cur, ch['new']):
        return 'AlreadyFixed'
    if cur == ch['now'] or any(cur == a for a in ch['alt_now']):
        return 'Write'
    if url_same(cur, ch['now']) or any(url_same(cur, a) for a in ch['alt_now']):
        return 'Write'
    return 'Skipped'


def esc_dump(obj):
    """JSON with non-ASCII letters kept readable but invisible / format / control chars escaped."""
    s = json.dumps(obj, ensure_ascii=False, separators=(',', ':'))
    out = []
    for ch in s:
        cat = unicodedata.category(ch)
        if ord(ch) > 127 and (cat[0] in ('C', 'Z') or cat in ('Mn', 'Me', 'Mc')):
            out.append('\\u%04x' % ord(ch))
        else:
            out.append(ch)
    return ''.join(out)


def invisible_report(obj):
    rep = []
    def walk(o, path):
        if isinstance(o, dict):
            for k, v in o.items():
                walk(v, path + '.' + k)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, path + '[%d]' % i)
        elif isinstance(o, str):
            for i, ch in enumerate(o):
                cat = unicodedata.category(ch)
                if ord(ch) > 127 and (cat[0] in ('C', 'Z') or cat in ('Mn', 'Me', 'Mc')):
                    rep.append((path, i, 'U+%04X' % ord(ch), unicodedata.name(ch, '?')))
    walk(obj, '')
    return rep


def build_payload(creative, new_url):
    c = copy.deepcopy(creative)
    c['web_view_properties']['url'] = new_url
    return {'creatives': [c]}


def diff(a, b, path=''):
    """list of (path, a, b) differences"""
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append((path + '.' + k, '<absent>', b[k]))
            elif k not in b:
                out.append((path + '.' + k, a[k], '<absent>'))
            else:
                out += diff(a[k], b[k], path + '.' + k)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            out += diff(x, y, path + '[%d]' % i)
    else:
        if a != b or type(a) != type(b):
            out.append((path, a, b))
    return out


def record(row):
    keys = ['platform', 'account_id', 'unit_type', 'unit', 'ad_ids', 'ad_names', 'slot', 'before',
            'after_expected', 'after_live', 'result', 'new_entity_ids', 'detail']
    for k in keys:
        if k not in row:
            raise KeyError(k)
    with open(OUT, 'a') as f:
        f.write(json.dumps({k: row[k] for k in keys}, ensure_ascii=False) + '\n')


def save(name, obj):
    with open(os.path.join(WD, name), 'w') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
