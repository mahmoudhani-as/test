# usage: python3 -I save.py <marker (e.g. TikTok request_id)> <out_name>
# Saves the exact text of the LATEST tool_result in this agent's transcript that contains <marker>, and prints a short summary.
import json, sys
sys.path.insert(0,'/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply7/tt4_work')
from common import *
marker, name = sys.argv[1], sys.argv[2]
out = name if name.startswith('/') else T+name
txt = extract(marker, out)
j = json.loads(txt)
print('saved', out, len(txt))
try:
    lst = j['data']['data']['data']['list']
    for a in lst:
        print(' ', a.get('ad_id'), a.get('identity_type'), 'item=%s'%a.get('tiktok_item_id'), a.get('ad_format'), a.get('campaign_automation_type'),
              'keys=%d'%len(a), 'TRUNC' if '__mcp_truncated_keys' in a else '')
except Exception as e:
    print('not an ad list:', repr(e)[:200])
