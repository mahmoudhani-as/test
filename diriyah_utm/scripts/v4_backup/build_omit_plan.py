"""Build URLs under the 12-Oct omit rule for every slot that the generator/legacy rebuild could not fill, then merge with the
legacy/clash items into one plan of edit units (shared creatives that would need two different URLs go to the manual list).
Inputs: work/scored.json, work/legacy_flagged.json, work/legacy_clash_items.json, work/first_serving_all.json, work/serving_out_*.json
Outputs: work/omit_items.json, work/omit_need_serving.json (ads whose first-serving month must be pulled first), work/omit_unbuilt.json,
         work/apply_plan_v5.json  {plan: [...units], skipped: [...units needing a manual split]}"""
import sys, os, json, glob, re, collections
from urllib.parse import urlsplit, parse_qsl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from derive import Deriver, MONTHS, KV_LETTER
from omit import Omit, check_omit
W = sys.argv[1] if len(sys.argv) > 1 else '.'
G = glob.glob(f'{W}/in/e2e*.xlsx')[0]
S = json.load(open(f'{W}/work/scored.json'))
FLAG = json.load(open(f'{W}/work/legacy_flagged.json'))
ITEMS = json.load(open(f'{W}/work/legacy_clash_items.json'))
FS = {tuple(k.split('|', 1)): v for k, v in json.load(open(f'{W}/work/first_serving_all.json')).items()}
NEVER = set()
for f in glob.glob(f'{W}/work/serving_out_*.json'):
    plat = os.path.basename(f).split('serving_out_')[1].split('_')[0]
    for k, v in json.load(open(f)).items():
        if v.get('status') == 'never_served': NEVER.add((plat, str(k)))
clash = json.load(open(f'{W}/work/serving_meta_clash.json'))
D = Deriver(G, clash)
O = Omit(D, S, G)
N = D.N
key = lambda s: (s['platform'], str(s.get('ad_id')), s.get('slot'), s.get('url'))
flag_keys = {key(f) for f in FLAG}
item_keys = {key(i) for i in ITEMS}

items, need, unbuilt = [], [], []
# 1) legacy rows the rebuild flagged
for f in FLAG:
    if 'sitelink' in str(f.get('slot')).lower(): continue
    k2 = (f['platform'], str(f.get('ad_id')))
    if k2 in FS: fd = FS[k2]; month = f'{MONTHS[int(fd[5:7]) - 1]}{fd[2:4]}'; mb = f'MonthYear {month} = first day the ad served ({fd})'
    elif k2 in NEVER: month = None; mb = 'month left out: the ad never served'
    else:
        need.append({k: f.get(k) for k in ('platform', 'account_id', 'account_name', 'campaign_id', 'campaign_name', 'adset_id', 'adset_name', 'ad_id', 'ad_name', 'effective_status')}); continue
    e, om, b = O.legacy(f, month)
    items.append({**f, 'kind': 'omit', 'expected_url': e, 'omitted': om, 'basis': b + [mb]})
# 2) generator-format ads whose ad token is unknown (kva on social/search, Google search without a creative code)
for s in S:
    if not s.get('url') or s['verdict'] != 'WRONG' or key(s) in flag_keys or key(s) in item_keys: continue
    if 'sitelink' in str(s.get('slot')).lower() or s['derive_status'] != 'BLOCKED': continue
    rs = ' | '.join(s['derive_reasons'])
    if 'kva/kvb/kvd' in rs or 'no search creative code' in rs or 'search creative/format on a social platform' in rs:
        e, om, b = O.unknown_ad_token(s)
        if e: items.append({**s, 'kind': 'omit', 'expected_url': e, 'omitted': om, 'basis': b})
        else: unbuilt.append({**s, 'why': om})
# 3) Google sitelink assets: one URL per asset, valid for every campaign / ad group it is linked to
camp_parts = collections.defaultdict(set); set_parts = collections.defaultdict(set)
for i in ITEMS + items:
    if i['platform'] != 'google' or not i.get('expected_url'): continue
    q = dict(parse_qsl(urlsplit(i['expected_url']).query))
    c = q.get('utm_campaign', '').split('_')
    uid = c[0] if c and re.fullmatch(r'[0-9a-f]{8}', c[0]) else None
    rest = c[1:] if uid else c
    obj = rest[-1] if rest and rest[-1] in N.objectives else None
    rest = rest[:-1] if obj else rest
    rest = rest[:-1] if rest and re.fullmatch(r'(' + '|'.join(MONTHS) + r')\d\d', rest[-1]) else rest
    camp_parts[(i['account_id'], i.get('campaign_id'))].add((uid, '_'.join(rest) or None, obj))
    set_parts[(i['account_id'], i.get('adset_id'))].add(q.get('utm_term'))
for s in S:   # first-plan generator URLs count as well
    if s['platform'] == 'google' and s.get('expected_url') and s['derive_status'] == 'FIX':
        q = dict(parse_qsl(urlsplit(s['expected_url']).query)); c = q.get('utm_campaign', '').split('_')
        camp_parts[(s['account_id'], s.get('campaign_id'))].add((c[0], c[1], c[-1])); set_parts[(s['account_id'], s.get('adset_id'))].add(q.get('utm_term'))
assets = collections.defaultdict(list)
for s in S:
    if 'sitelink' in str(s.get('slot')).lower() and s.get('url'): assets[(s['account_id'], str(s.get('ad_id')))].append(s)
for (acct, aid), links in assets.items():
    cps = set()
    for l in links: cps |= camp_parts.get((acct, l.get('campaign_id')), {(None, None, None)})
    uid = {c[0] for c in cps}; nm = {c[1] for c in cps}; ob = {c[2] for c in cps}
    one = lambda xs: next(iter(xs)) if len(xs) == 1 else None
    cuid, cname, obj = one(uid), one(nm), one(ob)
    if not cname: cuid = None
    terms = set()
    for l in links:
        terms |= (set_parts.get((acct, l.get('adset_id')), {None}) if l.get('adset_id') else {None})
    term = one(terms)
    url = links[0]['url']
    lp = re.search(r'/(en|ar)(/|$)', urlsplit(url.strip()).path.lower())
    lang = lp.group(1) if lp else None
    omitted = ['ad token (no generator code for sitelinks)', 'month (sitelinks have no serving date of their own)']
    if not cname: omitted.append('campaign name (asset shared by campaigns with different names)' if len(nm) > 1 else 'campaign name')
    if not obj: omitted.append('objective')
    if not term: omitted.append('ad set part (campaign-level link or ad groups differ)')
    if not lang: omitted.append('language')
    e = O.compose(url, 'google', 'paid-search', [cuid, cname, None, obj], [term] if term else [], [None, None, 'search', lang])
    for l in links:
        items.append({**l, 'kind': 'omit-sitelink', 'expected_url': e, 'omitted': omitted,
                      'basis': [f'sitelink asset {aid} linked in {len(links)} placement(s); every part that differs between them is left out']})

# validate
bad = collections.Counter()
for i in items:
    errs = check_omit(N, i['expected_url'])
    i['check'] = errs
    for x in errs: bad[x.split(':')[0]] += 1
print('omit items', len(items), collections.Counter(i['kind'] for i in items), 'need serving pull (ads)', len({(n['platform'], n['ad_id']) for n in need}),
      'unbuilt', len(unbuilt))
print('check errors', dict(bad))
json.dump(items, open(f'{W}/work/omit_items.json', 'w'), indent=1, default=str)
json.dump(need, open(f'{W}/work/omit_need_serving.json', 'w'), indent=1, default=str)
json.dump(unbuilt, open(f'{W}/work/omit_unbuilt.json', 'w'), indent=1, default=str)

# ---------- merge with legacy/clash items into edit units ----------
UNIT = {'meta': 'ad_id', 'snapchat': 'creative_id', 'tiktok': 'ad_id', 'google': 'ad_id', 'linkedin': 'creative_id', 'x': 'creative_id'}
unit = lambda s: (s['platform'], s.get('account_id'), str(s.get(UNIT[s['platform']]) or s.get('ad_id')))
allitems = [i for i in ITEMS] + [i for i in items if not i['check']]
fix = {(unit(i), i.get('slot'), i['url'], str(i.get('ad_id'))): i for i in allitems}
touched = {unit(i) for i in allitems}
rows_by_unit = collections.defaultdict(list)
for s in S:
    if s.get('url') and unit(s) in touched: rows_by_unit[unit(s)].append(s)
plan, manual = [], []
for u, rows in rows_by_unit.items():
    per_slot = collections.defaultdict(set); missing = []
    for r in rows:
        it = fix.get((u, r.get('slot'), r['url'], str(r.get('ad_id'))))
        if it: per_slot[(r.get('slot'), r['url'])].add(it['expected_url'])
        elif r['verdict'] == 'CORRECT': per_slot[(r.get('slot'), r['url'])].add(r['url'])
        else: missing.append(r)
    its = [v for k, v in fix.items() if k[0] == u]
    rec = {'platform': u[0], 'account_id': u[1], 'unit': u[2], 'account_name': its[0].get('account_name'), 'campaign_name': its[0].get('campaign_name'),
           'adset_name': its[0].get('adset_name'), 'ad_ids': sorted({str(i.get('ad_id')) for i in rows}), 'ad_names': sorted({str(i.get('ad_name')) for i in rows}),
           'campaign_id': its[0].get('campaign_id'), 'adset_id': its[0].get('adset_id'), 'creative_id': its[0].get('creative_id'),
           'status': its[0].get('effective_status') or its[0].get('ad_status'), 'edit_method': its[0].get('edit_method'),
           'kind': sorted({i['kind'] for i in its}),
           'changes': sorted({(i.get('slot'), i.get('base_url'), i.get('url_tags'), i['url'], i['expected_url']) for i in its if i['expected_url'] != i['url']}),
           'notes': sorted({str(i.get('notes')) for i in rows if i.get('notes')})[:4]}
    conflict = [k for k, v in per_slot.items() if len(v) > 1]
    if conflict: rec['skip_reason'] = 'shared creative/card used by ads that need different URLs'; manual.append(rec); continue
    if missing: rec['skip_reason'] = f'shared creative/card: {len(missing)} other ad(s) on it still need their serving month or cannot be built'; manual.append(rec); continue
    if rec['changes']: plan.append(rec)
json.dump({'plan': plan, 'skipped': manual}, open(f'{W}/work/apply_plan_v5.json', 'w'), indent=1, default=str)
print('v5 units', len(plan), 'slots', sum(len(p['changes']) for p in plan), 'manual units', len(manual))
print(collections.Counter((p['platform'], tuple(p['kind'])) for p in plan))
