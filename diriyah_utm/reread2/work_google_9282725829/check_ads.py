"""Check transcribed ad pages against candidate URLs (live_interim, targets, 11-Oct) and input.
Usage: python3 -I check_ads.py <root> <page files...>"""
import json, sys, collections
ROOT = sys.argv[1]
files = sys.argv[2:]
inp = json.load(open(f'{ROOT}/reread/in/google_9282725829.json'))
live = [json.loads(l) for l in open(f'{ROOT}/live/google_9282725829.jsonl')]
li = json.load(open(f'{ROOT}/work/live_interim.json'))
tg = {}
for t in json.load(open(f'{ROOT}/work/targets.json')):
    if t.get('platform') == 'google' and str(t.get('account_id')) == '9282725829':
        tg[(str(t['ad_id']), t['slot'])] = t.get('target')
inrow = {r['ad_id']: (r, l) for r, l in zip(inp, live) if r['slot'] == 'ad.final_urls[0]'}
seen = {}
bad = 0
for f in files:
    for n, line in enumerate(open(f), 1):
        line = line.rstrip('\n')
        if not line.strip():
            continue
        parts = line.split('|', 5)
        if len(parts) != 6:
            print('BADLINE', f, n, line[:80]); bad += 1; continue
        ad, ag, st, ps, suf, url = parts
        if ad in seen:
            print('DUP', ad, f, n)
        seen[ad] = parts
        if not (ad.isdigit() and ag.isdigit()):
            print('BADID', f, n, ad, ag); bad += 1
        if st not in ('ENABLED', 'PAUSED', 'REMOVED'):
            print('BADSTATUS', f, n, st); bad += 1
        if ad not in inrow:
            print('NEW (not in input):', ad, ag, st, url)
            continue
        r, l = inrow[ad]
        if l['adset_id'] != ag:
            print('ADGROUP CHANGED?', ad, 'live', l['adset_id'], 'now', ag); bad += 1
        k = f"google|{ad}|ad.final_urls[0]"
        cands = {'live_interim': (li.get(k) or {}).get('url'), 'target': tg.get((ad, 'ad.final_urls[0]')), '11oct': r['url_11oct']}
        m = [n_ for n_, c in cands.items() if c == url]
        if not m:
            print('NO-CANDIDATE-MATCH', ad, '\n   got   ', url)
            for n_, c in cands.items():
                print('   ', n_.ljust(12), c)
            bad += 1
        elif 'live_interim' not in m:
            print('differs from live_interim but matches', m, ad)
print('lines', len(seen), 'problems', bad)
