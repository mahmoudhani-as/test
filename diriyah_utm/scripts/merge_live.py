"""Merge the keyed re-read (reread/out/<platform>_<account>.jsonl) into work/live_now.json {platform|ad_id|slot: {url, status_now, found, note}}.
Prints coverage against the 11-Oct inventory (every URL slot should be re-read)."""
import sys, json, glob, os, collections
W = sys.argv[1]
S = json.load(open(f'{W}/work/scored.json'))
live, bad = {}, 0
for f in glob.glob(f'{W}/reread/out/*.jsonl'):
    if os.path.basename(f).startswith('new_'): continue
    for l in open(f):
        if not l.strip(): continue
        try: x = json.loads(l)
        except Exception: bad += 1; continue
        live[f"{x['platform']}|{x['ad_id']}|{x['slot']}"] = {k: x.get(k) for k in ('url', 'status_now', 'found', 'note', 'creative_id_now')}
json.dump(live, open(f'{W}/work/live_now.json', 'w'), indent=0)
c = collections.Counter()
for s in S:
    if not s.get('url'): continue
    k = f"{s['platform']}|{s['ad_id']}|{s['slot']}"
    c[(s['platform'], 'reread' if k in live else 'MISSING')] += 1
print('rows', len(live), 'bad lines', bad, dict(c))
