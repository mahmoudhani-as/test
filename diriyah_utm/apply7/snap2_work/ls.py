# ls.py : list this agent's snapchat calls (seq, action, dry_run, ids, requestId, status)
import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply7/snap2_work')
from common import *
for o in calls():
    i = o['input']
    r = o['result'] or {}
    ids = (i.get('path_params') or {}).get('creative_id') or ((i.get('payload') or {}) if isinstance(i.get('payload'), dict) else {}).get('ids')
    if ids is None and isinstance(i.get('payload'), dict) and 'creatives' in i['payload']:
        ids = [x.get('id') for x in i['payload']['creatives']]
    print(o['seq'], i.get('action'), 'dry_run=%r' % i.get('dry_run'), ids, req_id(o), 'success=%r' % r.get('success'), 'err=%r' % o['is_error'], (o['raw'][:200] if not r.get('success') else ''))
