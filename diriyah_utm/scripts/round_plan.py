"""Build an apply round from work/targets.json + every earlier apply read-back (apply*/out_*.jsonl).
Usage: python3 scripts/round_plan.py <dir> <round_dir_name> [--exclude problems.json]
  current URL of a slot = last read-back that matched (result Fixed) else the 11-Oct URL (or, after a keyed re-read, url_now)
  a slot needs an edit when current != target (query-order-insensitive compare, as targets.py)
Outputs in <dir>/<round>/: diff.json (one row per slot), in_<platform>_<n>.json (edit units), batches.json, manual.json, summary.txt
Every target must pass omit.check_omit; failures are held back (held.json) and never written."""
import sys, os, json, glob, collections, re
from urllib.parse import urlsplit, parse_qsl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from derive import Deriver
from omit import check_omit
W, RD = sys.argv[1], sys.argv[2]
EXCL = set()
if '--exclude' in sys.argv:
    for p in json.load(open(sys.argv[sys.argv.index('--exclude') + 1])): EXCL.add((p['platform'], str(p['ad_id']), p['slot']))
OUT = f'{W}/{RD}'; os.makedirs(OUT, exist_ok=True)
G = glob.glob(f'{W}/in/e2e*.xlsx')[0]
N = Deriver(G, json.load(open(f'{W}/work/serving_meta_clash.json'))).N
norm = lambda u: (lambda p: (p.scheme, p.netloc.lower(), p.path, p.fragment, tuple(sorted(parse_qsl(p.query, keep_blank_values=True)))))(urlsplit((u or '').strip()))
T = json.load(open(f'{W}/work/targets.json'))
NOW = {}   # optional keyed re-read: work/live_now.json {platform|ad_id|slot: url}
if os.path.exists(f'{W}/work/live_now.json'): NOW = json.load(open(f'{W}/work/live_now.json'))
fixed, tried = {}, collections.defaultdict(list)
for f in sorted(glob.glob(f'{W}/apply*/out_*.jsonl')):
    for l in open(f):
        if not l.strip(): continue
        x = json.loads(l)
        for a in x.get('ad_ids') or []:
            k = (x['platform'], str(a), x['slot'])
            if x['result'] == 'Fixed': fixed[k] = x
            elif x.get('after_expected'): tried[k].append(x['after_expected'])
UNIT = {'meta': 'ad_id', 'tiktok': 'ad_id', 'google': 'ad_id', 'snapchat': 'creative_id', 'x': 'creative_id', 'linkedin': 'creative_id'}
c = collections.Counter(); diff, held, manual = [], [], []
for r in T:
    k = (r['platform'], r['ad_id'], r['slot'])
    if not r['target']: c['no target'] += 1; continue
    nk = '|'.join(k)
    if nk in NOW:
        v = NOW[nk]
        cur = (v.get('url') if v.get('found', True) else None) if isinstance(v, dict) else v
    elif k in fixed: cur = fixed[k]['after_live']
    else: cur = r['url_11oct']
    if cur is None: c['slot gone/unreadable now'] += 1; continue
    if norm(cur) == norm(r['target']): c['correct'] += 1; continue
    if r.get('manual'): c['manual (shared creative)'] += 1; manual.append({**r, 'url_now': cur}); continue
    if 'tweet.entities' in str(r['slot']) or 'tweet text link' in str(r['slot']):
        c['manual (tweet text link)'] += 1; manual.append({**r, 'url_now': cur, 'manual': 'link in the text of a published tweet: X does not allow editing it; post a new tweet if needed'}); continue
    if k in EXCL: c['held (review problem)'] += 1; held.append({**r, 'url_now': cur, 'why': ['review problem']}); continue
    errs = check_omit(N, r['target'])
    if errs: c['held (check_omit)'] += 1; held.append({**r, 'url_now': cur, 'why': errs}); continue
    alt = sorted({u for u in [r['url_11oct'], (fixed.get(k) or {}).get('after_live')] + tried.get(k, []) if u and u != cur})
    c['needs edit'] += 1
    diff.append({**r, 'url_now': cur, 'alt_now': alt})
json.dump(diff, open(f'{OUT}/diff.json', 'w'), indent=1, default=str)
json.dump(held, open(f'{OUT}/held.json', 'w'), indent=1, default=str)
json.dump(manual, open(f'{OUT}/manual.json', 'w'), indent=1, default=str)

# edit units
units = collections.OrderedDict(); obj_targets, obj_units = {}, {}
for d in diff:
    p = d['platform']
    sl = 'sitelink' in str(d['slot']).lower()
    m = re.search(r'sitelink asset (\d+)', str(d['slot']))
    uid = ('asset', m.group(1)) if sl and m else ('id', str(d.get(UNIT[p]) or d['ad_id']))
    key = (p, d['account_id'], uid)
    u = units.setdefault(key, {'platform': p, 'account_id': d['account_id'], 'account_name': d['account_name'],
                               'unit_type': 'sitelink_asset' if sl else {'meta': 'ad', 'tiktok': 'ad', 'google': 'ad', 'snapchat': 'creative', 'x': 'tweet', 'linkedin': 'creative'}[p],
                               'unit': uid[1], 'creative_id': d.get('creative_id'), 'ad_ids': [], 'ad_names': [], 'campaign_name': d.get('campaign_name'),
                               'adset_name': d.get('adset_name'), 'status_11oct': d.get('status_11oct'), 'changes': []})
    if d['ad_id'] not in u['ad_ids']: u['ad_ids'].append(d['ad_id']); u['ad_names'].append(d.get('ad_name'))
    slot = re.sub(r'\s*\((campaign|ad_group|customer)_asset\)', '', d['slot']) if sl else d['slot']
    sub = re.search(r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', slot) if p == 'snapchat' else None
    obj_targets.setdefault((p, d['account_id'], sub.group(1) if sub else uid[1], re.sub(r'\(.*?\)|-> creative \S+', '', slot)), set()).add(norm(d['target']))
    obj_units.setdefault((p, d['account_id'], sub.group(1) if sub else uid[1], re.sub(r'\(.*?\)|-> creative \S+', '', slot)), set()).add(key)
    ch = {'slot': slot, 'now': d['url_now'], 'alt_now': d['alt_now'], 'new': d['target']}
    same = [x for x in u['changes'] if x['slot'] == slot]
    if same:
        if norm(same[0]['new']) != norm(ch['new']): u.setdefault('conflict', []).append(slot)
        continue
    u['changes'].append(ch)
ul = list(units.values())
for ok_, tg in obj_targets.items():      # one edited object (Snapchat sub-creative, card) that ads in different units need with different URLs
    if len(tg) > 1:
        for k in obj_units[ok_]: units[k].setdefault('conflict', []).append('shared sub-creative ' + str(ok_[2]))
bad = [u for u in ul if u.get('conflict')]
ul = [u for u in ul if not u.get('conflict')]
for u in bad: manual.append({'platform': u['platform'], 'unit': u['unit'], 'ad_ids': u['ad_ids'], 'ad_names': u['ad_names'], 'changes': u['changes'], 'manual': 'shared creative / sub-creative used by ads that need different URLs - split it by hand'})
json.dump(manual, open(f'{OUT}/manual.json', 'w'), indent=1, default=str)
SIZE = {('meta', 'ad'): 12, ('tiktok', 'ad'): 20, ('google', 'ad'): 60, ('google', 'sitelink_asset'): 60, ('snapchat', 'creative'): 20, ('x', 'tweet'): 15, ('linkedin', 'creative'): 20}
batches = collections.defaultdict(list)
by = collections.defaultdict(list)
for u in ul: by[(u['platform'], u['unit_type'])].append(u)
for (p, t), us in sorted(by.items()):
    n = SIZE[(p, t)]
    for i in range(0, len(us), n):
        f = f'in_{p}{"_sl" if t == "sitelink_asset" else ""}_{i // n + 1}.json'
        json.dump(us[i:i + n], open(f'{OUT}/{f}', 'w'), indent=1, default=str)
        batches[p].append(f)
json.dump(batches, open(f'{OUT}/batches.json', 'w'), indent=1)
s = [f'slots: {dict(c)}', f'units: {collections.Counter((u["platform"], u["unit_type"]) for u in ul)}',
     f'changes: {sum(len(u["changes"]) for u in ul)}', f'batches: { {p: len(v) for p, v in batches.items()} }', f'conflict units -> manual: {len(bad)}']
open(f'{OUT}/summary.txt', 'w').write('\n'.join(s) + '\n'); print('\n'.join(s))
