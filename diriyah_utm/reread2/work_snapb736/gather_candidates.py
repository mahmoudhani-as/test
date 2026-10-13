import json, glob, sys, os
from collections import defaultdict
ROOT = sys.argv[1]
OUT = sys.argv[2]
ACC = "b736921f-da3e-4889-8620-d3b0969c69b0"
units = defaultdict(list)   # key "unit||slot" -> history
for f in sorted(glob.glob(ROOT + '/apply*/out_snapchat_*.jsonl')):
    for line in open(f):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get('account_id') != ACC:
            continue
        units[r.get('unit') + '||' + (r.get('slot') or '')].append(
            {'file': os.path.relpath(f, ROOT), 'result': r.get('result'), 'before': r.get('before'),
             'after_live': r.get('after_live'), 'after_expected': r.get('after_expected')})
json.dump({'units': units}, open(OUT, 'w'), indent=1)
from collections import Counter
print('keys', len(units), Counter(k.split('||')[1][:40] for k in units))
