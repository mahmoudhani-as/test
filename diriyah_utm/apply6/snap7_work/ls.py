# ls.py : list this agent's snapchat_native_action calls with their seq numbers
import sys
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/snap7_work')
from common import *

for o in calls():
    i = o['input']
    r = o['result'] or {}
    info = ''
    try:
        d = r['data']['data']
        if isinstance(d, dict):
            info = 'req=%s status=%s' % (d.get('request_id'), d.get('request_status'))
            crs = d.get('creatives') or []
            info += ' creatives=' + ','.join(
                '%s:%s:%s' % (x['creative']['id'][:8], x['creative'].get('updated_at', ''), x.get('sub_request_status'))
                for x in crs if isinstance(x, dict) and 'creative' in x)
    except Exception:
        pass
    p = i.get('payload')
    ids = ''
    if isinstance(p, dict):
        ids = ' payload_ids=' + ','.join((x.get('id') or '?')[:8] if isinstance(x, dict) else str(x)[:8]
                                         for x in (p.get('creatives') or p.get('ids') or []))
    print(o['seq'], i.get('action'), 'dry_run=%s' % i.get('dry_run'), (i.get('path_params') or {}).get('creative_id', ''),
          ids, info[:400], 'ERROR' if o['is_error'] else '', '' if o['result'] is not None else 'UNPARSED:' + o['raw'][:200])
