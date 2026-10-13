# Read-only helpers for apply9 in_tiktok_1 (run 2, agent aaabef7ac47e33c01): parse raw tool inputs/results from
# transcripts (byte-exact), compare URLs, build the expected update payload. No API calls, no result files.
import json, re
from urllib.parse import urlsplit, parse_qsl

ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/'
INP = json.load(open(ROOT + 'apply9/in_tiktok_1.json', encoding='utf-8'))
INPD = {u['unit']: u for u in INP}
EXCL = json.load(open(ROOT + 'work/excl_platform_refused_v2.json', encoding='utf-8'))
WF = '/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/'
MINE = WF + 'wf_9af16efa-e58/agent-aaabef7ac47e33c01.jsonl'
PREV = WF + 'wf_0b1bfc20-cbb/agent-a14343dd39c0d2588.jsonl'
TOOL = 'mcp__Whathed_MCP__tiktok_native_action'
PIXEL = '7347671240183693330'  # exact pixel id from pixel/list; the gateway shows 7347671240183693000


def excluded(ad, slot):
    return any(e.get('platform') == 'tiktok' and str(e.get('ad_id')) == str(ad) and e.get('slot') == slot for e in EXCL)


def parts(u):
    s = urlsplit(u)
    return (s.scheme, s.netloc, s.path, s.fragment), sorted(parse_qsl(s.query, keep_blank_values=True))


def equiv(a, b):
    return a is not None and b is not None and parts(a) == parts(b)


def eff_url(url, utm_params):
    """full landing URL incl. separately stored utm_params (keys missing from the URL are appended)"""
    url = url or ''
    q = dict(parse_qsl(urlsplit(url).query, keep_blank_values=True))
    extra, conflict = [], []
    for x in (utm_params or []):
        k, v = x['key'], x['value']
        if k in q:
            if q[k] != v:
                conflict.append((k, q[k], v))
        else:
            extra.append((k, v))
    eff = url
    if extra:
        eff = url + ('&' if '?' in url else '?') + '&'.join(f'{k}={v}' for k, v in extra)
    return eff, extra, conflict


def utm_from(new):
    q = parse_qsl(urlsplit(new).query, keep_blank_values=True)
    assert all(k.startswith('utm_') and k != 'utm_id' for k, v in q), q
    assert len(set(k for k, v in q)) == len(q)
    return [{"key": k, "value": v} for k, v in q]


def _text(cc):
    if isinstance(cc, list):
        return ''.join(x.get('text', '') for x in cc if isinstance(x, dict) and x.get('type') == 'text')
    return cc if isinstance(cc, str) else ''


def calls(tr=MINE, action=None):
    """[(tool_use_id, input, result_text, is_error, ts_use, ts_result)] for tiktok_native_action calls, in order"""
    uses, res = [], {}
    for line in open(tr, encoding='utf-8'):
        try:
            e = json.loads(line)
        except Exception:
            continue
        content = (e.get('message') or {}).get('content')
        if not isinstance(content, list):
            continue
        for c in content:
            if not isinstance(c, dict):
                continue
            if c.get('type') == 'tool_use' and c.get('name') == TOOL:
                uses.append((c.get('id'), c.get('input') or {}, e.get('timestamp')))
            elif c.get('type') == 'tool_result':
                res[c.get('tool_use_id')] = (_text(c.get('content')), bool(c.get('is_error')), e.get('timestamp'))
    out = []
    for i, inp, ts in uses:
        if action is None or inp.get('action') == action:
            t, err, ts2 = res.get(i, (None, None, None))
            out.append((i, inp, t, err, ts, ts2))
    return out


def rj(txt):
    if not txt:
        return None
    try:
        return json.loads(txt)
    except Exception:
        m = re.search(r'(/[^\s"\']+\.(?:json|txt))', txt)
        if m:
            raw = json.load(open(m.group(1), encoding='utf-8'))
            if isinstance(raw, list) and raw and isinstance(raw[0], dict) and 'text' in raw[0]:
                raw = json.loads(''.join(x.get('text', '') for x in raw if x.get('type') == 'text'))
            return raw
        return None


def ad_reads(tr=MINE):
    """{ad_id: [(request_id, record, ts), ...]} from every successful tiktok_ad_get result, in order"""
    out = {}
    for i, inp, txt, err, ts, ts2 in calls(tr, 'tiktok_ad_get'):
        j = rj(txt)
        if not j or not j.get('success'):
            continue
        d = j['data']['data']
        if d.get('code') != 0:
            continue
        for a in d['data']['list']:
            out.setdefault(a['ad_id'], []).append((d['request_id'], a, ts2))
    return out


def classify(a):
    idt = a.get('identity_type')
    item = a.get('tiktok_item_id')
    if idt == 'BC_AUTH_TT' and item:
        return 'SPARK_PUSH_HOLD'
    if idt == 'AUTH_CODE':
        return 'SPARK_PULL'
    if idt == 'BC_AUTH_TT':
        return 'BC_AUTH_TT_NO_ITEM'
    if idt == 'CUSTOMIZED_USER':
        return 'CUSTOMIZED_USER'
    return 'OTHER:' + str(idt)


# creative fields sent back as read (same lists the 12/13-Oct runs proved), landing_page_url = new, utm_params = UTMs of new
F_SPARK_PULL = ['ad_id', 'ad_name', 'identity_id', 'identity_type', 'ad_format', 'tiktok_item_id', 'promotional_music_disabled',
                'ad_text', 'call_to_action', 'call_to_action_id', 'landing_page_url', 'utm_params', 'tracking_pixel_id',
                'creative_authorized', 'vast_moat_enabled']
EMPTY = (None, '', [], {})


def expected_payload(u, a):
    ch = u['changes'][0]
    assert classify(a) == 'SPARK_PULL'
    cr = {}
    for k in F_SPARK_PULL:
        if k == 'landing_page_url':
            cr[k] = ch['new']
        elif k == 'utm_params':
            if a.get('utm_params'):
                cr[k] = utm_from(ch['new'])
        elif k == 'tracking_pixel_id':
            pv = a.get('tracking_pixel_id')
            if pv not in (None, 0, '0', ''):
                assert float(int(PIXEL)) == float(pv), (PIXEL, pv)
                cr[k] = PIXEL
        elif k == 'ad_text':
            if k in a and a[k] is not None:
                cr[k] = a[k]
        elif k in a and a[k] not in EMPTY:
            cr[k] = a[k]
    return {"advertiser_id": u['account_id'], "adgroup_id": a['adgroup_id'], "creatives": [cr]}


def diff(a, b, p=''):
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append(p + '.' + k + ' missing in first')
            elif k not in b:
                out.append(p + '.' + k + ' extra in first')
            else:
                out += diff(a[k], b[k], p + '.' + k)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            out += diff(x, y, p + '[%d]' % i)
    elif a != b or type(a) != type(b):
        out.append('%s: %r vs %r' % (p, a, b))
    return out


def decide(u, a):
    ch = u['changes'][0]
    cur = eff_url(a.get('landing_page_url'), a.get('utm_params'))[0]
    if equiv(cur, ch['new']):
        return cur, 'AlreadyFixed'
    if cur == ch['now'] or cur in ch['alt_now']:
        return cur, 'Write'
    return cur, 'Skipped'
