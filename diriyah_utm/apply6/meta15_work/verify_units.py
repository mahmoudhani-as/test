import sys
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/meta15_work')
from lib15 import *
raw = sys.argv[1]
check = sys.argv[2].split(',') if len(sys.argv) > 2 and sys.argv[2] else []
good = json.load(open(W + 'live_read1_good.json'))
r = load_persisted(W + raw)
ads = {a['id']: a for a in r['data']['data']['data'] if isinstance(a, dict)}
print('trunc:', {k: has_trunc(v) for k, v in ads.items()}, 'missing:', [c for c in check if c not in ads])
verified = {}
for k, a in ads.items():
    if k in check:
        u = unit(k)
        rest = verify_ad(good[k], a, u['changes'])
        slots = [(ch['slot'], get_slot(a['creative'], ch['slot']) == ch['new']) for ch in u['changes']]
        print(k, 'status', a['status'], a['configured_status'], a['effective_status'], 'creative', a['creative']['id'],
              '| unexpected diffs:', len(rest), '| slots==new:', all(s[1] for s in slots), '| url_tags:', a['creative'].get('url_tags'))
        for l in rest:
            print('    ', l)
        verified[k] = a
    else:
        d = [l for l in diff(good[k], a) if 'site_link_image_url' not in l and '.image_url' not in l]
        print(k, 'unprocessed, unchanged since pre-read' if not d else ('CHANGED: %s' % d[:5]))
json.dump(verified, open(W + 'verified_' + raw, 'w'), ensure_ascii=False, indent=1)
