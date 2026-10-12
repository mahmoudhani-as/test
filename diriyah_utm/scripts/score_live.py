"""Score every live URL slot: validate + derive. Writes scored.json and prints summary."""
import sys, os, json, glob, collections, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from derive import Deriver, PLATFORM_SOURCES

live_dir, gen_path, out_path = sys.argv[1:4]
D = Deriver(gen_path); N = D.N
rows = []
for f in sorted(glob.glob(os.path.join(live_dir, '*.jsonl'))):
    for ln, line in enumerate(open(f), 1):
        line = line.strip()
        if not line: continue
        try: r = json.loads(line)
        except Exception as e:
            print('BAD JSON', f, ln, e); continue
        r['_file'] = os.path.basename(f)
        rows.append(r)

def extra_checks(r, url):
    errs = []
    p = (r.get('platform') or '').lower()
    q = dict((k.lower(), v) for k, v in re.findall(r'[?&]([^=&#]+)=([^&#]*)', url))
    src = q.get('utm_source', '').lower()
    if src and p in PLATFORM_SOURCES and src not in PLATFORM_SOURCES[p]:
        errs.append(('SOURCE_PLATFORM_MISMATCH', f'utm_source "{src}" on a {p} ad'))
    co = q.get('utm_content', '').lower()
    if p == 'google' and 'ritz-carlton-signature' in q.get('utm_campaign', '').lower() and not co.startswith('78f964bb_rcsr-search_search_'):
        errs.append(('RITZ_SEARCH_CODE', 'Ritz Google search must use 78f964bb_rcsr-search_search_{lang} (user decision)'))
    return errs

scored = []
for r in rows:
    url = r.get('url')
    s = dict(r)
    if url:
        errs = N.check(url) + extra_checks(r, url)
    else:
        errs = []
    d = D.derive(r)
    s['violations'] = errs
    s['derive_status'] = d['status']; s['expected_url'] = d['expected_url']
    s['derive_reasons'] = d['reasons']; s['basis'] = d['basis']
    if not url:
        verdict = 'NO URL'
    elif d['status'] == 'OK' and not [e for e in errs if e[0] != 'LP_LANG_MISMATCH']:
        verdict = 'CORRECT'
    elif errs or d['status'] in ('FIX',) or (d['status'] == 'BLOCKED' and any('kva' in x or 'search creative' in x for x in d['reasons'])):
        verdict = 'WRONG'
    else:
        verdict = 'UNTRACEABLE'   # URL passes every format rule but its ad is not in generator naming
    s['verdict'] = verdict
    scored.append(s)

json.dump(scored, open(out_path, 'w'), indent=1, default=str)
W = [s for s in scored if s.get('url')]
print(f'rows {len(scored)}  url slots {len(W)}  ads {len({(s["platform"], s.get("account_id"), s.get("ad_id")) for s in scored})}')
c = collections.Counter(s['verdict'] for s in scored)
print('verdicts', dict(c))
wrong = sum(1 for s in W if s['verdict'] == 'WRONG')
print(f'WRONG {wrong}/{len(W)} = {wrong/len(W):.1%}' if W else 'no urls')
print('\nby platform / account')
g = collections.defaultdict(collections.Counter)
for s in scored: g[(s['platform'], s.get('account_name'))][s['verdict']] += 1
for k, v in sorted(g.items(), key=str):
    tot = v['WRONG'] + v['CORRECT'] + v['UNTRACEABLE']
    print(f'  {k[0]:9} {str(k[1])[:45]:45} url={tot:4} wrong={v["WRONG"]:4} ({(v["WRONG"]/tot if tot else 0):6.1%}) correct={v["CORRECT"]:4} untraceable={v["UNTRACEABLE"]:4} no_url={v["NO URL"]:4}')
print('\nviolation codes on live urls')
vc = collections.Counter(k for s in W for k in {e[0] for e in s['violations']})
for k, v in vc.most_common(): print(f'  {v:5} {v/len(W):6.1%} {k}')
print('\nderive status', dict(collections.Counter(s['derive_status'] for s in W)))
br = collections.Counter(re.sub(r'"[^"]*"', '"…"', x) for s in W if s['derive_status'] == 'BLOCKED' for x in s['derive_reasons'])
for k, v in br.most_common(20): print(f'  {v:5} {k}')
