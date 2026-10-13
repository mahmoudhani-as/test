import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply8/work_meta_5')
from lib5 import *
AD = sys.argv[1]
p = json.load(open(W + 'payload_%s.json' % AD))
inp, r, txt = last_call('meta_ad_account_id_adcreatives_create')
print('dry_run sent:', inp.get('dry_run'), 'acct', inp.get('path_params'))
sent = inp['payload']
d1 = diff(p, sent)
print('sent == payload file:', d1 == [], d1[:5])
if inp.get('dry_run') is True:
    body = r['data']['data']['request']['body']
    d2 = diff(p, body)
    print('dry body == payload file:', d2 == [], d2[:5])
else:
    print('live result:', json.dumps(r.get('data', {}).get('data') if isinstance(r, dict) else r)[:300])
