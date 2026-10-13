import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply8/work_meta_5')
from lib5 import *
AD = sys.argv[1]
ref = sys.argv[2] if len(sys.argv) > 2 else None
ad, inp = last_ad_read(AD)
json.dump(ad, open(W + 'ad_pre_%s.json' % AD, 'w'), ensure_ascii=False, indent=1)
u = unit(AD)
cr = ad['creative']
print('ad', AD, 'status', ad.get('status'), ad.get('configured_status'), ad.get('effective_status'), 'creative', cr['id'], 'plan creative', u['creative_id'], 'updated', ad.get('updated_time'))
cl = classify(u, cr)
for x in cl: print(x)
if all(v == 'Write' for _, v, _ in cl):
    p, notes = build_payload(cr, u['changes'])
    print(notes, 'invisible', has_invisible(p), 'bigints', big_ints(p))
    json.dump(p, open(W + 'payload_%s.json' % AD, 'w'), ensure_ascii=False, indent=1)
    if ref:
        pr = json.load(open(W + 'payload_%s.json' % ref))
        print('payload identical to', ref, 'payload:', diff(pr, p) == [], diff(pr, p)[:5])
    orig = {k: cr[k] for k in p}
    for l in diff(orig, p): print(l)
