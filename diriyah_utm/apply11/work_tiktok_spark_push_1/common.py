# Read-only helpers for apply11 in_tiktok_spark_push_1: parse THIS agent's own transcript (byte-exact tool inputs/results),
# compare URLs, build the spark_push ad/update payload. No API calls, no result files.
import json, os, re
from urllib.parse import urlsplit, parse_qsl

ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/'
W = ROOT + 'apply11/work_tiktok_spark_push_1/'
INP = json.load(open(ROOT + 'apply11/in_tiktok_spark_push_1.json', encoding='utf-8'))
INPD = {u['unit']: u for u in INP}
EXCL = json.load(open(ROOT + 'work/excl_platform_refused_v2.json', encoding='utf-8'))
TR = '/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/wf_12f907cd-edb/agent-a460cb839ce0336f9.jsonl'
PIXEL = "7347671240183693330"   # Visit Diriyah - Base Pixel; pixel/list req 2026101320512927E8BDD2318F842C112D (string in raw API text)
OTHER_PIXEL = "7610705877289091089"
ADV = "7338057963233443842"
TOOL_SUFFIX = 'tiktok_native_action'


def excluded(ad, slot):
    return any(e.get('platform') == 'tiktok' and str(e.get('ad_id')) == str(ad) and e.get('slot') == slot for e in EXCL)


def parts(u):
    s = urlsplit(u)
    return (s.scheme, s.netloc, s.path, s.fragment), sorted(parse_qsl(s.query, keep_blank_values=True))


def equiv(a, b):
    return a is not None and b is not None and parts(a) == parts(b)


def raw_q(url):
    q = urlsplit(url or '').query
    out = []
    for p in q.split('&') if q else []:
        k, _, v = p.partition('=')
        out.append((k, v))
    return out


def eff_url(url, utm_params):
    """full landing URL incl. separately stored utm_params (keys missing from the URL are appended).
    Values compared raw (undecoded) against the URL query, so %2F etc. do not create false conflicts."""
    url = url or ''
    q = dict(raw_q(url))
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
    q = raw_q(new)
    assert all(k.startswith('utm_') and k != 'utm_id' for k, v in q), q
    assert len(set(k for k, v in q)) == len(q), 'duplicate keys'
    assert not any(('%' in v or '+' in v) for k, v in q), 'encoded value in new; check raw vs decoded'
    return [{"key": k, "value": v} for k, v in q]


def _txt(c):
    cc = c.get('content')
    if isinstance(cc, list):
        return ''.join(x.get('text', '') for x in cc if isinstance(x, dict))
    return str(cc) if cc is not None else ''


def tool_events():
    """ordered list of ('use', id, name, input, ts) and ('result', id, text, is_error, ts)"""
    ev = []
    seen = set()
    for line in open(TR, encoding='utf-8'):
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
            if c.get('type') == 'tool_use':
                key = ('u', c['id'])
                if key in seen:
                    continue
                seen.add(key)
                ev.append(('use', c['id'], c.get('name', ''), c.get('input') or {}, e.get('timestamp')))
            elif c.get('type') == 'tool_result':
                key = ('r', c.get('tool_use_id'))
                if key in seen:
                    continue
                seen.add(key)
                ev.append(('result', c.get('tool_use_id'), _txt(c), bool(c.get('is_error')), e.get('timestamp')))
    return ev


def calls(action=None):
    """[(order, tool_use_id, input, result_text, is_error)] for tiktok_native_action calls (optionally one action)"""
    ev = tool_events()
    res = {tid: (t, err) for k, tid, t, err, ts in ev if k == 'result'}
    out = []
    for i, (k, tid, name, inp, ts) in enumerate(ev):
        if k != 'use' or not name.endswith(TOOL_SUFFIX):
            continue
        if action and inp.get('action') != action:
            continue
        t, err = res.get(tid, (None, None))
        out.append((i, tid, inp, t, err))
    return out


def result_json(txt):
    if txt is None:
        return None
    try:
        return json.loads(txt)
    except Exception:
        m = re.search(r'(/[^\s"\']+\.(?:txt|json))', txt)
        if m and os.path.exists(m.group(1)):
            raw = json.load(open(m.group(1), encoding='utf-8'))
            if isinstance(raw, list) and raw and isinstance(raw[0], dict) and 'text' in raw[0]:
                return json.loads(''.join(x.get('text', '') for x in raw if isinstance(x, dict)))
            return raw
        return None


def ad_reads():
    """{ad_id: [(order, request_id, rec)]} from complete (unprojected, untruncated) tiktok_ad_get results"""
    out = {}
    for i, tid, inp, txt, err in calls('tiktok_ad_get'):
        if inp.get('result_fields') or inp.get('fields') or inp.get('compact') or inp.get('max_items') or (inp.get('params') or {}).get('fields'):
            continue
        j = result_json(txt)
        if not j or not j.get('success'):
            continue
        d = (j.get('data') or {}).get('data') or {}
        if d.get('code') != 0:
            continue
        if ((j.get('meta') or {}).get('mcp_output_budget') or {}).get('truncated'):
            continue
        for a in (d.get('data') or {}).get('list') or []:
            if not isinstance(a, dict) or '__mcp_truncated' in json.dumps(a):
                continue
            out.setdefault(str(a['ad_id']), []).append((i, d.get('request_id'), a))
    return out


def text_notes(t):
    if t is None:
        return 'none'
    notes = []
    if t != t.strip():
        notes.append('edge whitespace: lead=%r trail=%r' % (t[:len(t) - len(t.lstrip())], t[len(t.rstrip()):]))
    odd = sorted(set('U+%04X' % ord(ch) for ch in t if ord(ch) > 0xFFFF or ch in ' ​‌‍‎‏﻿'))
    if odd:
        notes.append('special chars ' + ','.join(odd))
    return '; '.join(notes) or 'clean'


def diff(x, y, p=''):
    out = []
    if isinstance(x, dict) and isinstance(y, dict):
        for k in sorted(set(x) | set(y)):
            if k not in x:
                out.append(p + '.' + k + ' missing in first')
            elif k not in y:
                out.append(p + '.' + k + ' extra in first')
            else:
                out += diff(x[k], y[k], p + '.' + k)
    elif isinstance(x, list) and isinstance(y, list) and len(x) == len(y):
        for n, (q, r) in enumerate(zip(x, y)):
            out += diff(q, r, p + '[%d]' % n)
    elif x != y or type(x) != type(y):
        out.append('%s: %r vs %r' % (p, x, y))
    return out
