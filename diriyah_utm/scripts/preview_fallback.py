import sys, json, glob, re, collections, os, random
sys.path.insert(0, 'scripts')
from derive import Deriver, MONTHS
from fallback import Fallback
from nomen import Nomen
G = glob.glob('in/e2e*.xlsx')[0]
S = json.load(open('work/scored.json'))
FS = {tuple(k.split('|', 1)): v for k, v in json.load(open('work/first_serving_all.json')).items()}
CREATED = {}
for f in glob.glob('work/serving_out_*.json'):
    plat = f.split('serving_out_')[1].split('_')[0]
    for k, v in json.load(open(f)).items():
        m = re.search(r'\b(?:ad|creative|promoted tweet|tweet|post)\s+(?:was\s+)?created\s*(?:at|on)?\s*:?\s*(20\d\d)-(\d\d)', str(v.get('note') or ''), re.I)
        if m: CREATED[(plat, str(k))] = f'{MONTHS[int(m.group(2)) - 1]}{m.group(1)[2:]}'
clash = json.load(open('work/serving_meta_clash.json'))
D = Deriver(G, clash)
L = Fallback(D, S, G, CREATED)
N = Nomen(G)
F = json.load(open('work/legacy_flagged.json'))
res = collections.Counter(); miss = collections.Counter(); out = []
for f in F:
    if 'sitelink' in str(f.get('slot')).lower(): res['sitelink (not attempted)'] += 1; continue
    key = (f['platform'], str(f.get('ad_id')))
    month = None
    if key in FS: fd = FS[key]; month = f'{MONTHS[int(fd[5:7]) - 1]}{fd[2:4]}'
    e, m, b, used = L.rebuild_fb(f, month)
    if e:
        errs = [x for x in N.check(e) if x[0] != 'LP_LANG_MISMATCH']
        res['rebuilt' + (' (FORMAT ERRORS)' if errs else '')] += 1
        out.append({**{k: f.get(k) for k in ('platform', 'account_name', 'campaign_name', 'adset_name', 'ad_name', 'ad_id', 'slot', 'url', 'effective_status', 'flag')}, 'new': e, 'basis': b, 'errs': errs})
    else:
        res['still missing'] += 1; miss[', '.join(m)] += 1
print(res); print(miss.most_common(10))
print('created months known', len(CREATED))
json.dump(out, open('work/fallback_preview.json', 'w'), indent=1, default=str)
random.seed(11)
for o in random.sample(out, 14):
    print('-', o['platform'], '| ad:', str(o['ad_name'])[:60], '| set:', str(o['adset_name'])[:50]); print('   old:', o['url'][:230]); print('   new:', o['new'][:230])
