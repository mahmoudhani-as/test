import json, sys
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply9/work_google_3')
from lib import *
from collections import Counter
# usage: python3 -I preread.py <out.json> <req_id> [<req_id> ...]
out_path = sys.argv[1]
rows = {}
for rid in sys.argv[2:]:
    rs, trunc, budget, inp = gaql_rows(rid)
    print(rid, 'rows', len(rs), 'trunc', trunc, 'budget_truncated', (budget or {}).get('truncated'))
    for aid, lst in parse_rows(rs, rid).items():
        rows.setdefault(aid, [])
        for rec in lst:
            if not any(x['aga_resource'] == rec['aga_resource'] for x in rows[aid]):
                rows[aid].append(rec)
U = units(); ex = excluded()
plan = []; cnt = Counter()
for u in U:
    for ch in u['changes']:
        aid = u['unit']
        lst = rows.get(aid)
        if not lst:
            plan.append({'unit': aid, 'slot': ch['slot'], 'cls': 'MISSING'}); cnt['MISSING'] += 1; continue
        r = lst[0]
        cur = r['landing']
        cls = classify(cur, ch)
        flags = []
        if len(lst) > 1: flags.append('multi_rows=%d' % len(lst))
        if any(x['landing'] != cur or x['final_urls'] != r['final_urls'] for x in lst): flags.append('ROWS_DIFFER')
        if len(r['final_urls']) != 1: flags.append('final_urls_len=%d' % len(r['final_urls']))
        if r['final_url_suffix']: flags.append('AD_SUFFIX')
        if any(r['parent_suffix']): flags.append('PARENT_SUFFIX=%s' % r['parent_suffix'])
        if any(r['parent_tut']) or r['tracking_url_template']: flags.append('TRACKING=%s/%s' % (r['tracking_url_template'], r['parent_tut']))
        if (aid, ch['slot']) in ex: flags.append('EXCLUDED')
        plan.append({'unit': aid, 'slot': ch['slot'], 'cls': cls, 'exact_now': cur == ch['now'], 'cur_eq_new_bytes': cur == ch['new'],
                     'flags': flags, 'type': r['type'], 'status': r['status'], 'approval': r['approval'], 'ad_group': r['ad_group'],
                     'campaign': r['campaign'], 'campaign_status': r['campaign_status'], 'req': r['req'], 'cur': cur,
                     'final_urls': r['final_urls'], 'final_url_suffix': r['final_url_suffix']})
        cnt[cls] += 1
json.dump({'rows': rows, 'plan': plan}, open(out_path, 'w'), indent=1, ensure_ascii=False)
print('ads read:', len(rows), 'units:', len(U))
print('classes:', dict(cnt))
print('missing:', [p['unit'] for p in plan if p['cls'] == 'MISSING'])
for p in plan:
    if p['cls'] not in ('Write', 'MISSING') or (p['cls'] == 'Write' and not p.get('exact_now')) or [f for f in p.get('flags', []) if f != 'AD_SUFFIX']:
        print('NOTE', json.dumps(p, ensure_ascii=False)[:700])
print('types:', Counter(p.get('type') for p in plan))
print('ad suffix units:', [p['unit'] for p in plan if 'AD_SUFFIX' in p.get('flags', [])])
print('approval:', Counter(p.get('approval') for p in plan))
print('status:', Counter((p.get('status'), p.get('campaign_status')) for p in plan))
