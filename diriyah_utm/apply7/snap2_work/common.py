# Helpers for apply7 Snapchat batch 2 (in_snapchat_2.json).
# Raw tool inputs/results are read back from this agent's own transcript, so every comparison is byte-exact.
import json, re, unicodedata, os
from urllib.parse import urlsplit, parse_qsl

BASE = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/'
IN = BASE + 'apply7/in_snapchat_2.json'
OUT = BASE + 'apply7/out_snapchat_2.jsonl'
WD = BASE + 'apply7/snap2_work'
EXCL = BASE + 'work/excl_platform_refused_v2.json'
T = ('/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/'
     'wf_c5081068-a7f/agent-ab9e842266737326c.jsonl')
UPDATE_ACTION = 'snapchat_adaccounts_ad_account_id_creatives_update'
VOLATILE = {'updated_at', 'semantic_id', 'review_status', 'review_status_details', 'packaging_status'}


def units():
    return json.load(open(IN, encoding='utf-8'))


def same_url(a, b):
    if a is None or b is None:
        return False
    if a == b:
        return True
    sa, sb = urlsplit(a), urlsplit(b)
    return ((sa.scheme, sa.netloc, sa.path, sa.fragment) == (sb.scheme, sb.netloc, sb.path, sb.fragment)
            and sorted(parse_qsl(sa.query, keep_blank_values=True)) == sorted(parse_qsl(sb.query, keep_blank_values=True)))


SLOT_RE = re.compile(r'^creative\.composite_properties\.creative_ids\[(\d+)\] \(([0-9a-f-]{36})\)\.web_view_properties\.url$')


def slot_target(u, c):
    """-> (creative id holding the url, index in parent composite or None)"""
    s = c['slot']
    if s == 'creative.web_view_properties.url':
        return u['unit'], None
    m = SLOT_RE.match(s)
    if not m:
        raise SystemExit('unexpected slot shape: ' + s)
    return m.group(2), int(m.group(1))


def classify(cur, c):
    alts = c.get('alt_now') or []
    if cur == c['new']:
        return 'AlreadyFixed', 'cur == new byte for byte'
    if same_url(cur, c['new']):
        return 'AlreadyFixed', 'cur == new (same params, different order)'
    if cur == c['now']:
        return 'WRITE', 'now'
    if cur in alts:
        return 'WRITE', 'alt_now[%d]' % alts.index(cur)
    if same_url(cur, c['now']):
        return 'WRITE', 'now (same params, different order)'
    for i, a in enumerate(alts):
        if same_url(cur, a):
            return 'WRITE', 'alt_now[%d] (same params, different order)' % i
    return 'Skipped', 'changed since plan'


def excluded(u, c):
    ex = json.load(open(EXCL, encoding='utf-8'))
    ids = set(u['ad_ids']) | {u['unit'], u.get('creative_id')}
    sub, _ = slot_target(u, c)
    ids.add(sub)
    return [e for e in ex if e.get('platform') == 'snapchat' and (e.get('ad_id') in ids or e.get('unit') in ids)]


def flat(d, p=''):
    r = {}
    for k, v in d.items():
        kp = p + k
        if isinstance(v, dict) and v:
            r.update(flat(v, kp + '.'))
        else:
            r[kp] = v
    return r


def calls():
    """All snapchat_native_action calls of this agent, in order: {seq, id, input, result, raw, is_error}."""
    inputs, out, seq = {}, [], 0
    for line in open(T, encoding='utf-8'):
        try:
            m = json.loads(line)
        except Exception:
            continue
        content = (m.get('message') or {}).get('content')
        if not isinstance(content, list):
            continue
        for it in content:
            if not isinstance(it, dict):
                continue
            if it.get('type') == 'tool_use' and 'snapchat_native_action' in (it.get('name') or ''):
                inputs[it['id']] = it.get('input') or {}
            elif it.get('type') == 'tool_result' and it.get('tool_use_id') in inputs:
                cc = it.get('content')
                txt = ''.join(x.get('text', '') for x in cc if isinstance(x, dict)) if isinstance(cc, list) else (cc or '')
                try:
                    res = json.loads(txt)
                except Exception:
                    res = None
                seq += 1
                out.append({'seq': seq, 'id': it['tool_use_id'], 'input': inputs[it['tool_use_id']], 'result': res,
                            'raw': txt, 'is_error': it.get('is_error')})
    return out


def by_seq():
    return {o['seq']: o for o in calls()}


def req_id(o):
    r = o['result'] or {}
    return ((r.get('meta') or {}).get('requestId')) or o['id']


def creatives_of(o):
    """creative objects returned by a GET / get_by_ids / PUT result, keyed by id; raises if any sub request failed"""
    r = o['result']
    d = r['data']['data']
    res = {}
    for x in d['creatives']:
        if not isinstance(x, dict):
            continue
        if x.get('sub_request_status') not in (None, 'SUCCESS'):
            raise ValueError('sub_request not SUCCESS: %r' % x)
        if 'creative' in x:
            res[x['creative']['id']] = x['creative']
    return res


def payload_of(o):
    p = o['input'].get('payload')
    if isinstance(p, str):
        p = json.loads(p)
    return p


def account_of(o):
    i = o['input']
    return i.get('ad_account_id') or i.get('account_id') or (i.get('path_params') or {}).get('ad_account_id')


ARABIC_PLAIN = set(range(0x0621, 0x063B)) | set(range(0x0641, 0x064B))


def esc_json(obj):
    """JSON text: ASCII printable and plain Arabic letters raw; every other char as a \\u escape."""
    s = json.dumps(obj, ensure_ascii=False)
    out = []
    for ch in s:
        o = ord(ch)
        if 0x20 <= o < 0x7f or o in ARABIC_PLAIN:
            out.append(ch)
        elif o > 0xffff:
            v = o - 0x10000
            out.append('\\u%04x\\u%04x' % (0xd800 + (v >> 10), 0xdc00 + (v & 0x3ff)))
        else:
            out.append('\\u%04x' % o)
    return ''.join(out)


def special_chars(s):
    if not isinstance(s, str):
        return []
    r = ['U+%04X %s' % (ord(ch), unicodedata.name(ch, '?')) for ch in s if ord(ch) > 0x7e and ord(ch) not in ARABIC_PLAIN]
    if '  ' in s:
        r.append('double-space')
    if s != s.strip():
        r.append('leading/trailing space')
    return r


def nonstr_scalars(obj, p=''):
    """numbers (possible precision issue) anywhere in obj"""
    r = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            r += nonstr_scalars(v, p + '.' + k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            r += nonstr_scalars(v, p + '[%d]' % i)
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        r.append((p, obj))
    return r


def recorded():
    done = set()
    try:
        for line in open(OUT, encoding='utf-8'):
            line = line.strip()
            if line:
                r = json.loads(line)
                done.add((r['unit'], r['slot']))
    except FileNotFoundError:
        pass
    return done


def append(u, c, before, after, result, detail, new_ids=''):
    if (u['unit'], c['slot']) in recorded():
        raise SystemExit('duplicate record refused: %s %s' % (u['unit'], c['slot']))
    line = {"platform": "snapchat", "account_id": u['account_id'], "unit_type": u['unit_type'], "unit": u['unit'],
            "ad_ids": u['ad_ids'], "ad_names": u['ad_names'], "slot": c['slot'], "before": before,
            "after_expected": c['new'], "after_live": after, "result": result, "new_entity_ids": new_ids,
            "detail": detail}
    with open(OUT, 'a', encoding='utf-8') as f:
        f.write(json.dumps(line, ensure_ascii=False) + '\n')


def save(name, obj):
    with open(os.path.join(WD, name), 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def diff(a, b, path=''):
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
