import json, sys
W = sys.argv[1]
def load(p):
    s = open(p).read()
    d = json.loads(s)
    if isinstance(d, list):
        d = json.loads(d[0]['text'])
    inner = d['data']['data']
    assert inner['request_status'] == 'SUCCESS'
    return [x['creative'] for x in inner['creatives']]
pages = [load(W + '/cr_p1.txt'), load(W + '/cr_p2.txt'), load(W + '/cr_p3.json')]
m = {}
conflicts = 0
for pg in pages:
    for c in pg:
        if c['id'] in m and m[c['id']] != c:
            conflicts += 1
            print('CONFLICT', c['id'])
        m[c['id']] = c
ids = sorted(m)
print('total creatives', len(m), 'conflicts', conflicts)
# check ordering contiguity: list API is sorted by id
allseq = [c['id'] for pg in pages for c in pg]
print('sorted pages?', [pg == sorted(pg, key=lambda c: c['id']) for pg in pages])
print('p1 last < p2 first', pages[0][-1]['id'] < pages[1][0]['id'])
need = json.load(open(W + '/needed_creatives.json'))
print('needed missing', [n for n in need if n not in m])
json.dump(m, open(W + '/creatives.json', 'w'), indent=0)
from collections import Counter
print(Counter(c['type'] for c in m.values()))
print(Counter(c.get('review_status') for c in m.values()))
print('keys', Counter(k for c in m.values() for k in c))
