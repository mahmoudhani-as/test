import json, sys
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply9/work_google_3')
from lib import *
# usage: python3 -I check_preview.py <dry_run_req_id> <payload.json>
# Verifies the dry-run preview body == intended payload, each op's URL == input "new", mask/fields only URL (+suffix).
rid, payload_path = sys.argv[1], sys.argv[2]
inp, j = result_by_request_id(rid)
d = j['data']
print('success', j.get('success'), 'dry_run', d.get('dry_run'), 'action', d.get('action'), 'endpoint', d.get('endpoint'), 'warnings', d.get('warnings'))
body = d['body']
want = json.load(open(payload_path))
sent = inp.get('params')
print('call input params == payload file:', sent == want)
U = {u['unit']: u for u in units()}
ok = True
if len(body['operations']) != len(want['operations']):
    print('OP COUNT DIFFERS', len(body['operations']), len(want['operations'])); ok = False
for bop, wop in zip(body['operations'], want['operations']):
    upd = bop['update']; rn = upd['resource_name']; aid = rn.split('/')[-1]
    ch = U[aid]['changes'][0]
    keys = sorted(upd.keys())
    exp_keys = sorted(wop['update'].keys())
    good = (upd.get('final_urls') == [ch['new']] and keys == exp_keys and bop.get('update_mask') == wop['update_mask']
            and rn == 'customers/%s/ads/%s' % (U[aid]['account_id'], aid)
            and ('final_url_suffix' not in upd or upd['final_url_suffix'] == ''))
    extra = sorted(set(bop.keys()) - {'update', 'update_mask'})
    if extra: good = False
    if not good: ok = False
    print(aid, 'OK' if good else 'BAD', keys, bop.get('update_mask'), 'extra=%s' % extra)
print('ALL_OK' if ok else 'NOT_OK')
