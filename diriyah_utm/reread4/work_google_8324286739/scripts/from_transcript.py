"""Copy an INLINE (not persisted) Whathead tool result out of this agent's own transcript, byte for byte,
into inline/<name>.json in the same shape as a persisted tool-result file ([{"type":"text","text":...}]),
so grab.py can validate and parse it (nothing is transcribed by hand).
Usage: python3 -I from_transcript.py <transcript.jsonl> <meta.requestId of the result> <name>"""
import json, sys, os

tr, req, name = sys.argv[1], sys.argv[2], sys.argv[3]
W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
hits = []
for line in open(tr, encoding='utf-8'):
    if req not in line:
        continue
    x = json.loads(line)
    c = (x.get('message') or {}).get('content')
    if not isinstance(c, list):
        continue
    for b in c:
        if b.get('type') != 'tool_result':
            continue
        cont = b.get('content')
        if isinstance(cont, list):
            texts = [t.get('text') for t in cont if t.get('type') == 'text']
        else:
            texts = [cont]
        for t in texts:
            if t and req in t:
                hits.append(t)
assert len(hits) == 1, f'{len(hits)} tool results carry requestId {req}'
t = hits[0]
j = json.loads(t)
assert j['meta']['requestId'] == req, j['meta']
os.makedirs(os.path.join(W, 'inline'), exist_ok=True)
dst = os.path.join(W, 'inline', name + '.json')
json.dump([{'type': 'text', 'text': t}], open(dst, 'w'), ensure_ascii=False)
print('wrote', dst, 'text len', len(t))
