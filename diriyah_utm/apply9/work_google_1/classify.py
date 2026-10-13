import json, sys
from urllib.parse import urlsplit, parse_qsl
def same(a, b):
    if a == b: return True
    if a is None or b is None: return False
    A, B = urlsplit(a), urlsplit(b)
    return (A.scheme, A.netloc, A.path, A.fragment) == (B.scheme, B.netloc, B.path, B.fragment) and sorted(parse_qsl(A.query, keep_blank_values=True)) == sorted(parse_qsl(B.query, keep_blank_values=True))
inp = json.load(open('../in_google_1.json'))
rows = json.load(open(sys.argv[1]))
out = []
from collections import Counter
cnt = Counter()
for u in inp:
    for c in u['changes']:
        rr = rows.get(u['unit'])
        rec = {'unit': u['unit'], 'slot': c['slot']}
        if not rr:
            rec['class'] = 'NOT_FOUND'; rec['cur'] = None
        else:
            if len(rr) > 1: rec['multi'] = True
            r = rr[0]
            fu = r['final_urls'] or []
            cur = fu[0] if fu else None
            rec.update(cur=cur, n_final_urls=len(fu), suffix=r['final_url_suffix'], ad_tracking=r['tracking_url_template'],
                       ag_suffix=r['ag_suffix'], c_suffix=r['c_suffix'], ag_tracking=r['ag_tracking'], c_tracking=r['c_tracking'],
                       aga_status=r['aga_status'], campaign_status=r['campaign_status'], type=r['type'], request_id=r['request_id'])
            if r['final_url_suffix'] or r['ag_suffix'] or r['c_suffix']:
                rec['suffix_note'] = True
            if same(cur, c['new']) and not r['final_url_suffix']:
                rec['class'] = 'AlreadyFixed'
            elif cur == c['now'] or cur in (c.get('alt_now') or []):
                rec['class'] = 'WRITE'
            else:
                rec['class'] = 'CHANGED'
        cnt[rec['class']] += 1
        out.append(rec)
json.dump(out, open(sys.argv[2], 'w'), indent=1, ensure_ascii=False)
print(cnt)
print('suffix notes', [o['unit'] for o in out if o.get('suffix_note')])
print('multi final urls', [o['unit'] for o in out if o.get('n_final_urls', 1) != 1])
print('multi rows', [o['unit'] for o in out if o.get('multi')])
print('statuses', Counter((o.get('aga_status'), o.get('campaign_status')) for o in out))
print('types', Counter(o.get('type') for o in out))
print('tracking', Counter((o.get('ad_tracking'), o.get('ag_tracking'), o.get('c_tracking')) for o in out))
for o in out:
    if o['class'] != 'WRITE': print(o)
