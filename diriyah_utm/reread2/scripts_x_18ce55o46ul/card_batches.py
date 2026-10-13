import json, re, sys
W = sys.argv[1]
target = int(sys.argv[2]) if len(sys.argv) > 2 else 56000
inp = json.load(open(W + '/../../reread/in/x_18ce55o46ul.json'))
cards = json.load(open(W + '/card_ids.json'))
pts = {p['id']: p for p in json.load(open(W + '/promoted_tweets.json'))}
tw = json.load(open(W + '/tweets.json'))
info = {}
for r in inp:
    t = tw[pts[r['ad_id']]['tweet_id']]
    cu = t.get('card_uri') or ''
    if not cu.startswith('card://'):
        continue
    cid = cu[7:]
    m = re.search(r'card_type=([A-Z_]+)', r['notes_11oct'] or '')
    ct = m.group(1) if m else None
    i = info.setdefault(cid, {'type': ct, 'slots': set(), 'urllen': 0})
    if r['slot']:
        i['slots'].add(r['slot'])
    if r['url_11oct']:
        i['urllen'] = max(i['urllen'], len(r['url_11oct']))
def est(cid):
    i = info[cid]
    u = i['urllen'] or 250
    base = 370 + 36
    t = i['type']
    if t == 'IMAGE_WEBSITE':
        return base + 430 + 190 + u
    if t == 'VIDEO_WEBSITE':
        return base + 650 + 190 + u
    if t == 'IMAGE_MULTI_DEST_CAROUSEL_WEBSITE':
        n = max(1, len(i['slots']))
        return base + n * (430 + 190 + u + 40)
    if t == 'IMAGE_CAROUSEL_WEBSITE':
        return base + 4 * 360 + 190 + u
    return 36
batches = []
cur = []
size = 1200
for c in cards:
    e = est(c)
    if cur and size + e > target:
        batches.append((cur, size))
        cur = []
        size = 1200
    cur.append(c)
    size += e
if cur:
    batches.append((cur, size))
out = []
for b, s in batches:
    print(len(b), s)
    out.append({'ids': b, 'est': s})
json.dump(out, open(W + '/card_batches.json', 'w'))
