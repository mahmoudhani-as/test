# usage: python3 -I collect.py <transcript.jsonl> <out collected.json>
# Extracts every Whathead tiktok_native_action call made by this agent (input + parsed JSON result) from the agent's own
# transcript, so the API responses are used byte-for-byte (no hand transcription). Large results that the harness saved
# to a file are read from that file.
import json, re, sys, os

TOOL = 'mcp__Whathed_MCP__tiktok_native_action'
tp, outp = sys.argv[1], sys.argv[2]
uses, results, order = {}, {}, []
for line in open(tp, encoding='utf-8'):
    try:
        o = json.loads(line)
    except Exception:
        continue
    m = o.get('message') or {}
    c = m.get('content')
    if not isinstance(c, list):
        continue
    for b in c:
        if not isinstance(b, dict):
            continue
        if b.get('type') == 'tool_use' and b.get('name') == TOOL:
            uses[b['id']] = b.get('input')
            order.append(b['id'])
        elif b.get('type') == 'tool_result':
            results[b.get('tool_use_id')] = b.get('content')


def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return ''.join(x.get('text', '') for x in content if isinstance(x, dict))
    return ''


def parse(t):
    t = t.strip()
    try:
        return json.loads(t), 'inline'
    except Exception:
        pass
    # harness saved a large output to a file: find an absolute path in the text
    for p in re.findall(r'(/[^\s"\'<>]+)', t):
        p = p.rstrip('.,;:)')
        if os.path.isfile(p):
            raw = open(p, encoding='utf-8').read()
            try:
                j = json.loads(raw)
            except Exception:
                continue
            if isinstance(j, list) and j and isinstance(j[0], dict) and 'text' in j[0]:
                j = json.loads(''.join(x.get('text', '') for x in j))
            return j, 'file:' + p
    return None, 'unparsed'


out = []
for i, uid in enumerate(order):
    if uid not in results:
        continue
    t = text_of(results[uid])
    j, src = parse(t)
    out.append({'seq': i, 'tool_use_id': uid, 'input': uses[uid], 'result': j, 'source': src, 'text_len': len(t),
                'raw_text_head': None if j is not None else t[:2000]})
json.dump(out, open(outp, 'w', encoding='utf-8'), ensure_ascii=False)
print('calls', len(order), 'with results', len(out), 'unparsed', sum(1 for x in out if x['result'] is None))
for x in out:
    inp = x['input'] or {}
    p = inp.get('params') or {}
    r = x['result'] or {}
    d = ((r.get('data') or {}).get('data') or {}) if isinstance(r, dict) else {}
    dd = d.get('data') or {} if isinstance(d, dict) else {}
    lst = dd.get('list') if isinstance(dd, dict) else None
    print(x['seq'], inp.get('action'), json.dumps(p.get('filtering')), 'page', p.get('page'), 'ps', p.get('page_size'),
          '| code', d.get('code') if isinstance(d, dict) else None, 'n', len(lst) if isinstance(lst, list) else None,
          'pi', json.dumps(dd.get('page_info')) if isinstance(dd, dict) else None, '| src', x['source'], 'len', x['text_len'],
          '| budget', (r.get('meta') or {}).get('mcp_output_budget') if isinstance(r, dict) else None)
