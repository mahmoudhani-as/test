# usage: python3 -I prep.py <pre_read_file> <uid> [<uid> ...]
import json, sys
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/tt1r_work')
from lib import *
src = sys.argv[1]
base = ads_from(W + '/readA.json')
ads = ads_from(src)
for uid in sys.argv[2:]:
    a = ads[uid]
    b = base[uid]
    d = [(k, b.get(k), a.get(k)) for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)]
    cur, extra, conf = cur_of(a)
    cl = classify(uid, cur)
    print('==', uid, '| classify:', cl, '| kind:', kind(a), '| diff vs 14:11 read:', d)
    json.dump(a, open(f'{W}/pre_{uid}.json', 'w'), ensure_ascii=False, indent=1)
    if cl != 'write':
        print('   NOT WRITING; cur =', cur)
        continue
    tp = a.get('tracking_pixel_id') or a.get('ad_ref_pixel_id')
    p = build(a, pixel_exact=('7347671240183693330' if tp else None))
    json.dump(p, open(f'{W}/payload_{uid}.json', 'w'), ensure_ascii=False, indent=1)
    print('   ad_text trailing space:', a['ad_text'].endswith(' '))
    print(json.dumps(p, ensure_ascii=False))
