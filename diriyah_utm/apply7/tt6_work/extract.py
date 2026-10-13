# usage: python3 -I extract.py <marker> <out_file>
# Saves the exact text of the LATEST tool_result in my transcript that contains <marker>.
import json, sys
sys.path.insert(0,'/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply7/tt6_work')
from common import *
marker, out = sys.argv[1], sys.argv[2]
r=tool_results(marker)
if not r: sys.exit('marker not found')
t=r[-1][1]
open(out,'w',encoding='utf-8').write(t)
try:
    json.loads(t); print('saved', out, len(t), 'json ok')
except Exception as e:
    print('saved', out, len(t), 'NOT JSON:', t[:500])
