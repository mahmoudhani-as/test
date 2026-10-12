"""Month rule (user, binding): the utm_campaign month = month the ad FIRST SERVED (first day with impressions, account time zone).
Generator-derived targets (and omit targets for generator-format ads) took the month from the campaign name. This step makes every
non-sitelink target follow the first-serving date on file (work/first_serving_all.json), and leaves the month out for ads verified
as never served (12-Oct omit rule). Run after targets.py; rewrites work/targets.json in place and lists every change in work/month_fixes.json."""
import sys, os, json, glob, re, collections
from urllib.parse import urlsplit, urlunsplit, parse_qsl, quote
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from derive import MONTHS
W = sys.argv[1]
FS = json.load(open(f'{W}/work/first_serving_all.json'))
NEVER = set()
for f in glob.glob(f'{W}/work/serving_out_*.json'):
    plat = os.path.basename(f).split('serving_out_')[1].split('_')[0]
    for k, v in json.load(open(f)).items():
        if v.get('status') == 'never_served': NEVER.add(f'{plat}|{k}')
NEVER -= set(FS)          # a served date always wins over an older never_served note
T = json.load(open(f'{W}/work/targets.json'))
MRE = re.compile(r'(' + '|'.join(MONTHS) + r')\d\d')
fixes, c = [], collections.Counter()

def rebuild(url, newcamp):
    p = urlsplit(url); q = parse_qsl(p.query, keep_blank_values=True)
    q = [(k, newcamp if k == 'utm_campaign' else v) for k, v in q if not (k == 'utm_campaign' and not newcamp)]
    query = '&'.join(f'{k}={quote(v, safe="-_.~{}/:")}' for k, v in q)
    return urlunsplit((p.scheme, p.netloc, p.path, query, p.fragment))

for r in T:
    if not r.get('target') or 'sitelink' in str(r['slot']).lower(): continue
    k = f"{r['platform']}|{r['ad_id']}"
    q = dict(parse_qsl(urlsplit(r['target']).query))
    camp = q.get('utm_campaign')
    if camp is None: continue
    toks = camp.split('_')
    idx = [i for i, t in enumerate(toks) if MRE.fullmatch(t)]
    want = None
    if k in FS: want = f'{MONTHS[int(FS[k][5:7]) - 1]}{FS[k][2:4]}'
    if k in FS and idx and toks[idx[-1]] != want:
        old = toks[idx[-1]]; toks[idx[-1]] = want; why = f'month {old} -> {want}: first day the ad served {FS[k]}'
    elif k in NEVER and idx:
        old = toks.pop(idx[-1]); why = f'month {old} left out: the ad never served (verified zero impressions over its whole life)'
    else:
        c['unchanged'] += 1; continue
    new = rebuild(r['target'], '_'.join(toks))
    fixes.append({'platform': r['platform'], 'ad_id': r['ad_id'], 'slot': r['slot'], 'source': r['source'], 'old_target': r['target'], 'target': new, 'why': why})
    r['target_before_month_fix'] = r['target']; r['target'] = new; r['month_fix'] = why
    c[(r['source'], 'month changed' if 'never' not in why else 'month removed (never served)')] += 1
json.dump(T, open(f'{W}/work/targets.json', 'w'), indent=1, default=str)
json.dump(fixes, open(f'{W}/work/month_fixes.json', 'w'), indent=1, default=str)
print(dict(c))
