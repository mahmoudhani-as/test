# recman.py <unit_idx> <change_idx|all> <result> <before|-> <after_live|-> --detail-file <path>
# Manual record for Failed / NotAttempted outcomes (blocked writes, auth expiry). '-' = use the plan's 'now'.
import json, sys
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/snap7_work')
from common import *

idx, cis, result, before, after = sys.argv[1:6]
detail = open(sys.argv[sys.argv.index('--detail-file') + 1], encoding='utf-8').read().strip()
assert result in ('Failed', 'NotAttempted', 'Skipped')
u = units()[int(idx)]
sel = range(len(u['changes'])) if cis == 'all' else [int(x) for x in cis.split(',')]
for ci in sel:
    c = u['changes'][ci]
    if (u['unit'], c['slot']) in recorded():
        print('already recorded, skip', ci)
        continue
    b = c['now'] if before == '-' else before
    a = b if after == '-' else after
    append(u, c, b, a, result, detail)
    print('recorded', idx, ci, result)
