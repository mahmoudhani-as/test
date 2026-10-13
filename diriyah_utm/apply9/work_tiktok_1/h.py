# Read-only helpers for apply9 in_tiktok_1: parse this agent's own transcript (raw tool inputs/results),
# compare URLs, build the expected update payload. No API calls, no result files.
import json, sys, unicodedata
from urllib.parse import urlsplit, parse_qsl

ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/'
W = ROOT + 'apply9/work_tiktok_1/'
INP = json.load(open(ROOT + 'apply9/in_tiktok_1.json', encoding='utf-8'))
INPD = {u['unit']: u for u in INP}
EXCL = json.load(open(ROOT + 'work/excl_platform_refused_v2.json', encoding='utf-8'))
TR = '/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/wf_0b1bfc20-cbb/agent-a14343dd39c0d2588.jsonl'
TOOL = 'mcp__Whathed_MCP__tiktok_native_action'
PIXEL = '7347671240183693330'  # exact pixel id (pixel/list), the gateway shows it as 7347671240183693000


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


def events():
    """(kind, id, name, input_or_text) in transcript order"""
    ev = []
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
                ev.append(('use', c.get('id'), c.get('name'), c.get('input') or {}))
            elif c.get('type') == 'tool_result':
                cc = c.get('content')
                if isinstance(cc, list):
                    t = ''.join(x.get('text', '') for x in cc if isinstance(x, dict) and x.get('type') == 'text')
                else:
                    t = cc if isinstance(cc, str) else ''
                ev.append(('result', c.get('tool_use_id'), None, t))
    return ev


def calls(action=None):
    """[(tool_use_id, input, result_text)] for my tiktok_native_action calls, in order"""
    ev = events()
    res = {i: t for k, i, n, t in ev if k == 'result'}
    out = []
    for k, i, n, inp in ev:
        if k == 'use' and n == TOOL and (action is None or inp.get('action') == action):
            out.append((i, inp, res.get(i)))
    return out


def rj(txt):
    if not txt:
        return None
    try:
        return json.loads(txt)
    except Exception:
        # large results are saved to a file; the text names the path
        import re
        m = re.search(r'(/[^\s"\']+\.(?:json|txt))', txt)
        if m:
            raw = json.load(open(m.group(1), encoding='utf-8'))
            if isinstance(raw, list) and raw and isinstance(raw[0], dict) and 'text' in raw[0]:
                raw = json.loads(''.join(x.get('text', '') for x in raw if x.get('type') == 'text'))
            return raw
        return None


def ad_reads():
    """{ad_id: [(request_id, record), ...]} from every tiktok_ad_get result, in order"""
    out = {}
    for i, inp, txt in calls('tiktok_ad_get'):
        j = rj(txt)
        if not j or not j.get('success'):
            continue
        d = j['data']['data']
        if d.get('code') != 0:
            continue
        for a in d['data']['list']:
            out.setdefault(a['ad_id'], []).append((d['request_id'], a))
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


# creative fields sent per class (as read), plus landing_page_url = new and utm_params = UTMs of new
F_SPARK_PULL = ['ad_id', 'ad_name', 'identity_id', 'identity_type', 'ad_format', 'tiktok_item_id', 'promotional_music_disabled',
                'ad_text', 'call_to_action', 'call_to_action_id', 'landing_page_url', 'utm_params', 'tracking_pixel_id',
                'creative_authorized', 'vast_moat_enabled']
F_CUSTOM = ['ad_id', 'ad_name', 'identity_id', 'identity_type', 'ad_format', 'video_id', 'image_ids', 'ad_text', 'call_to_action',
            'call_to_action_id', 'card_id', 'landing_page_url', 'utm_params', 'tracking_pixel_id', 'display_name',
            'avatar_icon_web_uri', 'aigc_disclosure_type', 'creative_authorized', 'vast_moat_enabled']
F_BC = ['ad_id', 'ad_name', 'identity_type', 'identity_id', 'identity_authorized_bc_id', 'ad_format', 'video_id', 'image_ids',
        'music_id', 'ad_text', 'call_to_action', 'call_to_action_id', 'card_id', 'landing_page_url', 'utm_params', 'dark_post_status',
        'creative_auto_enhancement_strategy_list', 'tracking_pixel_id', 'creative_authorized', 'vast_moat_enabled']
EMPTY = (None, '', [], {})


def expected_payload(u, a):
    ch = u['changes'][0]
    cls = classify(a)
    fields = {'SPARK_PULL': F_SPARK_PULL, 'CUSTOMIZED_USER': F_CUSTOM, 'BC_AUTH_TT_NO_ITEM': F_BC}[cls]
    cr = {}
    for k in fields:
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


def text_notes(txt):
    txt = txt or ''
    return {"trailing_ws": txt != txt.rstrip(), "leading_ws": txt != txt.lstrip(),
            "nonprint": sorted({'U+%04X' % ord(c) for c in txt if unicodedata.category(c) in ('Cf', 'Cc', 'Zs', 'Mn') and c != ' '})}
