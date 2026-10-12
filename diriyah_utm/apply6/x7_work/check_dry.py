# Read-only: confirm the latest dry-run request I sent for unit N equals the locally built payload, and the gateway echo equals it too.
import json, sys
sys.path.insert(0,'/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/x7_work')
from tr import load_tr
calls, results, order = load_tr()
idx=int(sys.argv[1])
u=json.load(open('../in_x_7.json'))[idx]; cid=json.load(open('share_summary.json'))[u['unit']]['card_id']
upd=[t for t in order if (calls[t][0] or '').endswith('x_ads_native_action') and calls[t][1].get('action')=='UPDATE_CARD' and (calls[t][1].get('path_params') or {}).get('card_id')==cid and t in results]
t=upd[-1]; inp=calls[t][1]; d=json.loads(results[t])
exp=json.load(open(f'payload_{idx}.json'))
print(t, 'card', cid, 'dry_run flag', inp.get('dry_run'), '| echo dry_run', d['data'].get('dry_run'))
print('sent == expected:', inp['payload']==exp, '| echo == expected:', d['data']['request']['payload']==exp, '| card id', d['data']['request']['card_id']==cid, '| account', d['data']['request']['account_id']=='18ce55o46ul')
