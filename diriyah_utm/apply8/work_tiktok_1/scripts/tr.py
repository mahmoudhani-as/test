# Read-only: pull my own tool calls / results out of my transcript (exact bytes as sent / received).
import json, re, sys
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply8/work_tiktok_1/scripts')
from common import tool_events

PERSIST = re.compile(r'Full output saved to: (\S+\.json)')


def result_json(text):
    m = PERSIST.search(text or '')
    if m:
        raw = json.load(open(m.group(1), encoding='utf-8'))
        if isinstance(raw, list):
            raw = ''.join(x.get('text', '') for x in raw if isinstance(x, dict) and x.get('type') == 'text')
            return json.loads(raw)
        return raw
    try:
        return json.loads(text)
    except Exception:
        return None


def calls(action):
    """[(tool_use_id, input, result_text_or_None)] for tiktok_native_action calls with this action, in order"""
    ev = tool_events()
    res = {tid: t for kind, tid, _, t in ev if kind == 'result'}
    out = []
    for kind, tid, name, inp in ev:
        if kind == 'use' and (name or '').endswith('tiktok_native_action') and inp.get('action') == action:
            out.append((tid, inp, res.get(tid)))
    return out


def ad_reads():
    """{ad_id: [(request_id, ad_record)]} from every ad/get result in my transcript, in order"""
    out = {}
    for tid, inp, txt in calls('tiktok_ad_get'):
        j = result_json(txt)
        if not j or not j.get('success'):
            continue
        d = j['data']['data']
        if d.get('code') != 0:
            continue
        for a in d['data'].get('list') or []:
            out.setdefault(a['ad_id'], []).append((d.get('request_id'), a))
    return out


def sp_reads():
    out = {}
    for tid, inp, txt in calls('tiktok_smart_plus_ad_get'):
        j = result_json(txt)
        if not j or not j.get('success'):
            continue
        d = j['data']['data']
        if d.get('code') != 0:
            continue
        for a in d['data'].get('list') or []:
            out.setdefault(a['smart_plus_ad_id'], []).append((d.get('request_id'), a))
    return out
