import json, sys
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply8/work_meta_7')
from lib7 import *
raw = sys.argv[1]
ids = sys.argv[2].split(',')
d = load_persisted(raw)
txt = json.dumps(d)
print('trunc markers:', [m for m in ['TRUNC', 'truncated'] if m in txt])
ads = {a['id']: a for a in d['data']['data']['data']}
for aid in ids:
    pre = json.load(open(W + 'ad_%s_pre.json' % aid))
    post = ads[aid]
    json.dump(post, open(W + 'ad_%s_post.json' % aid, 'w'), ensure_ascii=False, indent=1)
    u = unit(aid)
    print('=== AD', aid, post['status'], post['configured_status'], post['effective_status'], post['updated_time'], 'creative', pre['creative']['id'], '->', post['creative']['id'])
    for c in u['changes']:
        after = full_url(post['creative'], c['slot'])
        print('  after_live:', after)
        print('  after==new byte for byte:', after == c['new'], '| url_tags:', post['creative'].get('url_tags'))
    print('  creative diff:')
    for l in diff(pre['creative'], post['creative']):
        print('   ', l)
    print('  ad-level diff:', diff({k: v for k, v in pre.items() if k != 'creative'}, {k: v for k, v in post.items() if k != 'creative'}))
