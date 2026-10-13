# usage: python3 -I smartplus.py <collected.json> <sp_out.json> [<input.json>]
# Union of all smart_plus/ad/get reads (filtering may be STATUS_ALL or smart_plus_ad_ids): keyed by smart_plus_ad_id, later
# read wins; reports differences between repeated reads of the same ad, coverage vs total_number and vs the input ids.
import json, sys, collections
C = json.load(open(sys.argv[1], encoding='utf-8'))
rows, src, diffs, totals, calls, problems = {}, {}, [], set(), [], []
for r in C:
    inp = r['input'] or {}
    if inp.get('action') != 'tiktok_smart_plus_ad_get':
        continue
    p = inp.get('params') or {}
    res = r['result']
    inner = res['data']['data']
    if inner.get('code') != 0:
        problems.append(('api code', r['seq'], inner.get('code'), inner.get('message'))); continue
    dd = inner['data']; lst = dd['list']
    good = [x for x in lst if isinstance(x, dict)]
    trunc = len(good) != len(lst)
    f = p.get('filtering') or {}
    calls.append((r['seq'], json.dumps({k: (f'<{len(v)} ids>' if isinstance(v, list) else v) for k, v in f.items()}), p.get('page'), p.get('page_size'), len(good), trunc, dd.get('page_info'), inner.get('request_id')))
    if f == {"primary_status": "STATUS_ALL"}:
        totals.add(dd['page_info']['total_number'])
    for x in good:  # items shown before a truncation marker are complete records
        sid = x['smart_plus_ad_id']
        if sid in rows and rows[sid] != x:
            diffs.append((sid, r['seq']))
        rows[sid] = x
        src[sid] = {'seq': r['seq'], 'request_id': inner.get('request_id'), 'page': p.get('page'), 'page_size': p.get('page_size')}
for c in calls: print('call', c)
print('total_number', totals, 'unique smart+ ads', len(rows), 'diffs between repeated reads', diffs, 'problems', problems)
if len(sys.argv) > 3:
    inp = json.load(open(sys.argv[3], encoding='utf-8'))
    spin = [r['ad_id'] for r in inp if r['slot'] != 'ad.landing_page_url']
    miss = [a for a in spin if a not in rows]
    print('input smart+ ids', len(spin), 'missing', len(miss), miss)
    notin = {a: (x['secondary_status'], x['create_time']) for a, x in rows.items() if a not in set(spin)}
    print('smart+ ads not in input', len(notin), collections.Counter(v[0] for v in notin.values()))
    for a, v in notin.items():
        if 'DELETE' not in v[0]: print('  NOT DELETED', a, v)
json.dump({'rows': rows, 'src': src, 'total_number': sorted(totals), 'calls': calls, 'diffs': diffs, 'problems': problems},
          open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False)
