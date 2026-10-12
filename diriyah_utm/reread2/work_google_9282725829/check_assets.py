"""Check transcribed sitelink asset pages against candidates (live_interim, targets, 11-Oct)."""
import json, sys, glob, os, collections
ROOT = sys.argv[1]
W = os.path.dirname(os.path.abspath(__file__))
inp = json.load(open(f'{ROOT}/reread/in/google_9282725829.json'))
li = json.load(open(f'{ROOT}/work/live_interim.json'))
tg = collections.defaultdict(set)
for t in json.load(open(f'{ROOT}/work/targets.json')):
    if t.get('platform') == 'google' and str(t.get('account_id')) == '9282725829' and t['slot'].startswith('sitelink'):
        if t.get('target'):
            tg[str(t['ad_id'])].add(t['target'])
cand = collections.defaultdict(dict)
for r in inp:
    if not r['slot'].startswith('sitelink'):
        continue
    k = f"google|{r['ad_id']}|{r['slot']}"
    c = cand[r['ad_id']]
    c.setdefault('live_interim', set()).add((li.get(k) or {}).get('url'))
    c.setdefault('11oct', set()).add(r['url_11oct'])
    c['target'] = tg.get(r['ad_id'], set())
got = {}
bad = 0
for f in sorted(glob.glob(os.path.join(W, 'assets_p*.txt'))):
    for n, line in enumerate(open(f), 1):
        line = line.rstrip('\n')
        if not line.strip():
            continue
        aid, suf, nn, url = line.split('|', 3)
        if aid in got:
            print('DUP', aid)
        got[aid] = url
        if suf:
            print('SUFFIX', aid, suf)
        if nn != '1':
            print('N_URLS', aid, nn)
        if aid not in cand:
            print('UNEXPECTED asset', aid); bad += 1; continue
        m = [k for k, v in cand[aid].items() if url in v]
        if not m:
            print('NO-CANDIDATE-MATCH', aid, '\n   got ', url)
            for k, v in cand[aid].items():
                for u in v:
                    print('   ', k.ljust(12), u)
            bad += 1
        elif 'live_interim' not in m:
            print('differs from live_interim but matches', m, aid)
        if len(cand[aid]['live_interim']) > 1:
            print('NOTE: multiple live_interim urls for', aid, cand[aid]['live_interim'])
print('assets', len(got), 'of', len(cand), 'problems', bad, 'missing', len([a for a in cand if a not in got]))
