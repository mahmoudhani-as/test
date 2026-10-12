# usage: python3 -I checkdry.py <marker(requestId of dry run)> <uid>
import json, sys, subprocess
W = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/tt1r_work'
sys.path.insert(0, W)
from lib import *
marker, uid = sys.argv[1], sys.argv[2]
subprocess.run(['python3', '-I', W + '/extract.py', marker, f'{W}/dry_{uid}.json'], check=True)
d = json.load(open(f'{W}/dry_{uid}.json'))
body = d['data']['data']['request']['body']
p = json.load(open(f'{W}/payload_{uid}.json'))
a = json.load(open(f'{W}/pre_{uid}.json'))
cr = body['creatives'][0]
print('dryRun:', d['data']['dryRun'], '| warnings:', d['data']['data']['warnings'], '| preflightBlocking:', d['data']['data']['preflightBlocking'])
print('body == payload:', body == p, '| ad_id:', cr['ad_id'] == uid, '| adgroup:', body['adgroup_id'] == a['adgroup_id'])
print('fields differing from live read:', [k for k in cr if k in a and cr[k] != a[k]], '| fields not in read:', [k for k in cr if k not in a])
print('ad_text identical:', cr['ad_text'] == a['ad_text'], '| landing == new:', cr['landing_page_url'] == UNITS[uid]['changes'][0]['new'])
