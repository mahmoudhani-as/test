# Read-only helpers for apply8 in_tiktok_1: parse saved TikTok reads, compare URLs. No API calls, no result files.
import json, unicodedata
from urllib.parse import urlsplit, parse_qsl
ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/'
W = ROOT + 'apply8/work_tiktok_1/'
INP = json.load(open(ROOT + 'apply8/in_tiktok_1.json', encoding='utf-8'))
INPD = {u['unit']: u for u in INP}
EXCL = json.load(open(ROOT + 'work/excl_platform_refused_v2.json', encoding='utf-8'))
TR = '/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/wf_6a795359-362/agent-aea963c27adcd0000.jsonl'


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
    extra = []
    conflict = []
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


def load_tool_json(path):
    """a saved MCP tool result: either the raw JSON or a [{type:text,text:...}] wrapper"""
    raw = json.load(open(path, encoding='utf-8'))
    if isinstance(raw, list) and raw and isinstance(raw[0], dict) and 'text' in raw[0]:
        raw = json.loads(''.join(x.get('text', '') for x in raw if x.get('type') == 'text'))
    return raw


def tool_events():
    """(kind, tool_use_id, name_or_None, input_or_text) for my own transcript, in order"""
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


def text_notes(txt):
    txt = txt or ''
    return {"trailing_ws": txt != txt.rstrip(), "leading_ws": txt != txt.lstrip(),
            "nonprint": sorted({'U+%04X' % ord(c) for c in txt if unicodedata.category(c) in ('Cf', 'Cc', 'Zs', 'Mn') and c != ' '})}
