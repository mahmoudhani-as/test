import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply8/work_meta_5')
from lib5 import *
AD = sys.argv[1]
ad, inp = last_ad_read(AD)
json.dump(ad, open(W + 'ad_after_%s.json' % AD, 'w'), ensure_ascii=False, indent=1)
u = unit(AD)
print('creative', ad['creative']['id'], 'url_tags', ad['creative'].get('url_tags'))
for c in u['changes']:
    after = full_url(ad['creative'], c['slot'])
    print('after == new:', after == c['new'], c['slot'])
print(ad['status'], ad['configured_status'], ad['effective_status'], ad['updated_time'])
