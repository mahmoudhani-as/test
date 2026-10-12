import sys, json, glob, re, collections, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from derive import Deriver, MONTHS
from legacy import Legacy
G = glob.glob('in/e2e*.xlsx')[0]
S = json.load(open('work/scored.json'))
FS = {tuple(k.split('|', 1)): v for k, v in json.load(open('work/first_serving_all.json')).items()}
NEVER = set()
for f in glob.glob('work/serving_out_*.json'):
    plat = f.split('serving_out_')[1].split('_')[0]
    for k, v in json.load(open(f)).items():
        if v.get('status') == 'never_served': NEVER.add((plat, str(k)))
clash = json.load(open('work/serving_meta_clash.json'))
D = Deriver(G, {k: v for k, v in clash.items()})
L = Legacy(D, S, G)
items = []; flagged = collections.Counter(); flag_rows = []
for s in S:
    if not s.get('url'): continue
    reasons = s['derive_reasons']; key = (s['platform'], str(s.get('ad_id')))
    if s['derive_status'] == 'BLOCKED' and any(r.startswith('CONFLICT') for r in reasons):
        if str(s['ad_id']) in clash:
            r = dict(s); r['_use_serving_month'] = True; d = D.derive(r)
            if d['status'] == 'FIX': items.append({**s, 'kind': 'clash', 'expected_url': d['expected_url'], 'basis': d['basis']}); continue
        flagged['month clash: ad never served'] += 1; flag_rows.append({**s, 'flag': 'Month clash: ad never served, so there is no serving month'})
    elif s['derive_status'] == 'BLOCKED' and any('not in generator format' in r or r == 'no ad name' for r in reasons):
        e, m, b = L.rebuild(s, month='x')
        if not e:
            flagged['legacy: missing ' + ', '.join(sorted(set(m) - {'first-serving month'}))] += 1
            flag_rows.append({**s, 'flag': 'Legacy: no source for ' + ', '.join(sorted(set(m) - {'first-serving month'}))}); continue
        if key in NEVER: flagged['legacy: never served'] += 1; flag_rows.append({**s, 'flag': 'Legacy: ad never served, so there is no serving month'}); continue
        if key not in FS: flagged['legacy: no serving date pulled'] += 1; flag_rows.append({**s, 'flag': 'Legacy: serving date not pulled'}); continue
        fd = FS[key]; month = f'{MONTHS[int(fd[5:7]) - 1]}{fd[2:4]}'
        e, m, b = L.rebuild(s, month=month)
        items.append({**s, 'kind': 'legacy', 'expected_url': e, 'basis': b + [f'MonthYear {month} = first day the ad served ({fd}, account timezone)'], 'first_serving': fd})
json.dump(items, open('work/regen_items.json', 'w'), indent=1, default=str)
json.dump(flag_rows, open('work/regen_flagged.json', 'w'), indent=1, default=str)
print('items', len(items), dict(collections.Counter(i['kind'] for i in items)))
for k, v in flagged.most_common(12): print('  flagged', v, k)
UNIT = {'meta': 'ad_id', 'snapchat': 'creative_id', 'tiktok': 'ad_id', 'google': 'ad_id', 'linkedin': 'creative_id', 'x': 'creative_id'}
unit = lambda s: (s['platform'], s.get('account_id'), str(s.get(UNIT[s['platform']]) or s.get('ad_id')))
fix = {(unit(i), i.get('slot'), i['url'], str(i.get('ad_id'))): i for i in items}
touched = {unit(i) for i in items}
rows_by_unit = collections.defaultdict(list)
for s in S:
    if s.get('url') and unit(s) in touched: rows_by_unit[unit(s)].append(s)
plan, manual = [], []
for u, rows in rows_by_unit.items():
    per_slot = collections.defaultdict(set); missing = []
    for r in rows:
        it = fix.get((u, r.get('slot'), r['url'], str(r.get('ad_id'))))
        (per_slot[(r.get('slot'), r['url'])].add(it['expected_url']) if it else missing.append(r))
    its = [v for k, v in fix.items() if k[0] == u]
    rec = {'platform': u[0], 'account_id': u[1], 'unit': u[2], 'account_name': its[0].get('account_name'), 'campaign_name': its[0].get('campaign_name'),
           'adset_name': its[0].get('adset_name'), 'ad_ids': sorted({str(i.get('ad_id')) for i in rows}), 'ad_names': sorted({str(i.get('ad_name')) for i in rows}),
           'campaign_id': its[0].get('campaign_id'), 'adset_id': its[0].get('adset_id'), 'creative_id': its[0].get('creative_id'),
           'status': its[0].get('effective_status') or its[0].get('ad_status'), 'edit_method': its[0].get('edit_method'), 'kind': its[0]['kind'],
           'changes': sorted({(i.get('slot'), i.get('base_url'), i.get('url_tags'), i['url'], i['expected_url']) for i in its if i['expected_url'] != i['url']}),
           'notes': sorted({str(i.get('notes')) for i in rows if i.get('notes')})[:4]}
    conflict = [k for k, v in per_slot.items() if len(v) > 1]
    if conflict: rec['skip_reason'] = 'shared creative/card used by ads that need different URLs'; manual.append(rec); continue
    if missing: rec['skip_reason'] = f'shared creative/card: {len(missing)} other ad(s) on it cannot be rebuilt'; manual.append(rec); continue
    if rec['changes']: plan.append(rec)
json.dump({'plan': plan, 'skipped': manual}, open('work/regen_plan.json', 'w'), indent=1, default=str)
print('units', len(plan), 'slots', sum(len(p['changes']) for p in plan), 'manual', len(manual))
print(collections.Counter((p['platform'], p['account_name']) for p in plan))
