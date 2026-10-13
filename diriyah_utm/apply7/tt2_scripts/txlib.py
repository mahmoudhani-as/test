"""Read-only helpers: exact tool calls/results of this agent from its own transcript."""
import json
T = '/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/wf_a77bf62d-a6a/agent-a1c19619ffc33f518.jsonl'
ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'

def calls_for(ad):
    uses, res = [], {}
    for line in open(T, encoding='utf-8'):
        try: e = json.loads(line)
        except Exception: continue
        for x in ((e.get('message') or {}).get('content') or []):
            if not isinstance(x, dict): continue
            if x.get('type') == 'tool_use' and 'Whathed' in (x.get('name') or ''): uses.append(x)
            elif x.get('type') == 'tool_result':
                cc = x.get('content')
                res[x.get('tool_use_id')] = ''.join(y.get('text', '') for y in cc if isinstance(y, dict)) if isinstance(cc, list) else (cc or '')
    out = []
    for u in uses:
        if ad in json.dumps(u['input']) and u['id'] in res:
            try: j = json.loads(res[u['id']])
            except Exception: j = None
            out.append((u, j, res[u['id']]))
    return out

def ad_from(j, ad):
    return [x for x in j['data']['data']['data']['list'] if x['ad_id'] == ad][0]

def unit(ad):
    return {u['unit']: u for u in json.load(open(ROOT + '/apply7/in_tiktok_2.json'))}[ad]
