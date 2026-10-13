import json, sys
from urllib.parse import urlsplit, parse_qsl

BASE = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
units = json.load(open(BASE + '/apply9/in_google_sl_1.json'))
excl = json.load(open(BASE + '/work/excl_platform_refused_v2.json'))
read_path = sys.argv[1] if len(sys.argv) > 1 else BASE + '/apply9/work_google_sl_1/preread.json'
pre = json.load(open(read_path))['assets']


def norm(u):
    s = urlsplit(u)
    return (s.scheme, s.netloc, s.path, s.fragment, sorted(parse_qsl(s.query, keep_blank_values=True)))


excl_ids = {str(e.get('ad_id')) for e in excl}
out = []
for u in units:
    for c in u['changes']:
        aid = u['unit']
        urls = pre.get(aid)
        if aid in excl_ids:
            cls = 'EXCLUDED'
            cur = None
        elif urls is None:
            cls = 'NOT_FOUND'
            cur = None
        else:
            cur = urls[0]
            if len(urls) != 1:
                cls = 'MULTI_URL'
            elif cur == c['new'] or norm(cur) == norm(c['new']):
                cls = 'ALREADY'
            elif cur == c['now'] or cur in c['alt_now']:
                cls = 'WRITE'
            else:
                cls = 'CHANGED'
        out.append({'unit': aid, 'slot': c['slot'], 'cls': cls, 'cur': cur, 'now_eq': cur == c['now'],
                    'new': c['new']})
for o in out:
    print(o['unit'], o['cls'], 'cur==now' if o['now_eq'] else '')
print(json.dumps({k: sum(1 for o in out if o['cls'] == k) for k in sorted({o['cls'] for o in out})}))
json.dump(out, open(read_path.replace('.json', '_class.json'), 'w'), ensure_ascii=False, indent=1)
