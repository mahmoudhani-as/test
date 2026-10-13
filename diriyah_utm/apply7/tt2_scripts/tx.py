"""Transcript helper: exact text of this agent's own tool calls and results.

usage: python3 -I tx.py <marker> <out_prefix>
Finds the LATEST tool_use (of a Whathead tool) whose input JSON contains <marker>,
writes <out_prefix>.input.json (the exact input sent) and <out_prefix>.result.txt
(the exact text of its tool_result), and prints a short summary.
"""
import json, sys
T = '/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/wf_a77bf62d-a6a/agent-a1c19619ffc33f518.jsonl'
marker, out = sys.argv[1], sys.argv[2]
uses, results = [], {}
for line in open(T, encoding='utf-8'):
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
        if c.get('type') == 'tool_use' and 'Whathed' in (c.get('name') or ''):
            uses.append(c)
        elif c.get('type') == 'tool_result':
            cc = c.get('content')
            if isinstance(cc, list):
                t = ''.join(x.get('text', '') for x in cc if isinstance(x, dict) and x.get('type') == 'text')
            else:
                t = cc if isinstance(cc, str) else ''
            results[c.get('tool_use_id')] = t
cand = [u for u in uses if marker in json.dumps(u.get('input'), ensure_ascii=False)]
if not cand:
    sys.exit('marker not found in any tool_use input')
u = cand[-1]
json.dump(u['input'], open(out + '.input.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
r = results.get(u['id'])
if r is None:
    sys.exit('no result yet for ' + u['id'])
open(out + '.result.txt', 'w', encoding='utf-8').write(r)
print('tool', u['name'], 'id', u['id'], 'input bytes', len(json.dumps(u['input'])), 'result bytes', len(r))
