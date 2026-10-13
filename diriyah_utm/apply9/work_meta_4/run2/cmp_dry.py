import json, sys
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply9/work_meta_4/run2')
import lib10 as L
AD = sys.argv[1]
p = json.load(open(L.W + 'payload_%s.json' % AD))
hits = L.find_calls('meta_ad_account_id_adcreatives_create', lambda i: i.get('dry_run') is True)
cid, inp, res, err = hits[-1]
d = L.parse_result(res)
body = d['data']['data']['request']['body']
print('tool input == payload:', inp.get('payload') == p)
print('dry body == payload:', body == p)
print('diff input/payload', L.diff(p, inp.get('payload')))
print('diff body/payload', L.diff(p, body))
print('url', d['data']['data']['request']['url'], 'requestId', d['meta']['requestId'], 'path_params', inp.get('path_params'))
