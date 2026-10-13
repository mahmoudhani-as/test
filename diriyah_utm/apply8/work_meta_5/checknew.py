import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply8/work_meta_5')
from lib5 import *
AD, NEW = sys.argv[1], sys.argv[2]
new, _ = last_creative_read(NEW, 1)
json.dump(new, open(W + 'new_%s.json' % NEW, 'w'), ensure_ascii=False, indent=1)
orig = json.load(open(W + 'ad_pre_%s.json' % AD))['creative']
u = unit(AD)
for c in u['changes']:
    print('new slot == new:', get_slot(new, c['slot']) == c['new'], c['slot'])
print('url_tags:', new.get('url_tags'))
for l in diff(orig, new): print(l)
