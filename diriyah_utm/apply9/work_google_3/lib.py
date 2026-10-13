import json
from urllib.parse import urlsplit, parse_qsl

D = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
W = D + '/apply9/work_google_3'
IN = D + '/apply9/in_google_3.json'
EXCL = D + '/work/excl_platform_refused_v2.json'
T = '/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/wf_bc821e36-21b/agent-af722bcb7bf041c8d.jsonl'


def load_transcript(path=T):
    """Return (calls, order, results) from my own transcript: exact tool-result text."""
    calls, order, results = {}, [], {}
    for line in open(path):
        try:
            e = json.loads(line)
        except Exception:
            continue
        msg = e.get('message') or {}
        content = msg.get('content')
        if not isinstance(content, list):
            continue
        for c in content:
            if not isinstance(c, dict):
                continue
            if c.get('type') == 'tool_use':
                if c['id'] not in calls:
                    order.append(c['id'])
                calls[c['id']] = (c.get('name'), c.get('input'))
            elif c.get('type') == 'tool_result':
                rc = c.get('content')
                if isinstance(rc, list):
                    txt = ''.join(x.get('text', '') for x in rc if isinstance(x, dict) and x.get('type') == 'text')
                else:
                    txt = rc if isinstance(rc, str) else json.dumps(rc)
                results[c['tool_use_id']] = txt
    return calls, order, results


def result_by_request_id(req_id):
    calls, order, results = load_transcript()
    for tid in order:
        txt = results.get(tid)
        if not txt or req_id not in txt:
            continue
        try:
            j = json.loads(txt)
        except Exception:
            continue
        if (j.get('meta') or {}).get('requestId') == req_id:
            return calls[tid][1], j
    raise KeyError('request id not found in transcript: ' + req_id)


def gaql_rows(req_id):
    inp, j = result_by_request_id(req_id)
    data = j['data']['data']['data']
    res = data.get('results', [])
    rows = [r for r in res if isinstance(r, dict)]
    trunc = [r for r in res if not isinstance(r, dict)]
    budget = (j.get('meta') or {}).get('mcp_output_budget')
    return rows, trunc, budget, inp


def landing(ad):
    fu = ad.get('finalUrls', [])
    u = fu[0] if fu else None
    suf = ad.get('finalUrlSuffix')
    if suf and u is not None:
        u = u + ('&' if '?' in u else '?') + suf
    return u


def norm(u):
    if u is None:
        return None
    s = urlsplit(u)
    return (s.scheme, s.netloc, s.path, s.fragment, tuple(sorted(parse_qsl(s.query, keep_blank_values=True))))


def same(a, b):
    return a is not None and b is not None and norm(a) == norm(b)


def units():
    return json.load(open(IN))


def excluded():
    ex = json.load(open(EXCL))
    return {(e['ad_id'], e['slot']) for e in ex if e['platform'] == 'google'}


def classify(cur, ch):
    if same(cur, ch['new']):
        return 'AlreadyFixed'
    if cur == ch['now'] or cur in (ch.get('alt_now') or []):
        return 'Write'
    return 'Skipped'


def parse_rows(rs, rid):
    rows = {}
    for r in rs:
        aga = r['adGroupAd']; ad = aga['ad']
        aid = ad['id']
        rec = {
            'req': rid, 'type': ad.get('type'), 'final_urls': ad.get('finalUrls', []),
            'final_url_suffix': ad.get('finalUrlSuffix'), 'tracking_url_template': ad.get('trackingUrlTemplate'),
            'aga_resource': aga.get('resourceName'),
            'status': aga.get('status'), 'approval': (aga.get('policySummary') or {}).get('approvalStatus'),
            'ad_group': r['adGroup']['id'], 'campaign': r['campaign']['id'], 'campaign_status': r['campaign'].get('status'),
            'parent_suffix': [r['adGroup'].get('finalUrlSuffix'), r['campaign'].get('finalUrlSuffix'), (r.get('customer') or {}).get('finalUrlSuffix')],
            'parent_tut': [r['adGroup'].get('trackingUrlTemplate'), r['campaign'].get('trackingUrlTemplate'), (r.get('customer') or {}).get('trackingUrlTemplate')],
            'landing': landing(ad)}
        rows.setdefault(aid, []).append(rec)
    return rows
