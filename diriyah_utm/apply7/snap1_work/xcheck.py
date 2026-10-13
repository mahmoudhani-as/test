"""Cross-check text fields of a before file against strings saved by earlier runs (independent transcriptions)."""
import json, glob, collections, sys
BASE = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/'
seen = collections.defaultdict(set)
for f in glob.glob(BASE + 'apply*/snap*_work/*.json') + glob.glob(BASE + 'apply*/*/snap*_work/*.json') + glob.glob(BASE + 'apply*/snap*/*.json'):
    if '/apply7/' in f: continue
    try: o = json.load(open(f))
    except Exception: continue
    def walk(x):
        if isinstance(x, dict):
            for k in ('headline', 'brand_name', 'name'):
                if isinstance(x.get(k), str): seen[k].add(x[k])
            for v in x.values(): walk(v)
        elif isinstance(x, list):
            for v in x: walk(v)
    walk(o)
o = json.load(open(sys.argv[1]))
objs = o if isinstance(o, list) else [o]
done = set()
for x in objs:
    for k in ('headline', 'brand_name', 'name'):
        v = x.get(k)
        if v is None or (k, v) in done: continue
        done.add((k, v))
        cps = [hex(ord(c)) for c in v] if any(ord(c) > 127 for c in v) else ''
        near = [s for s in seen[k] if s != v and s.replace('​', '').replace('ّ', '').strip() == v.replace('​', '').replace('ّ', '').strip()]
        print(k, repr(v), cps, '| identical seen earlier:', v in seen[k], '| near-miss variants:', [repr(s) for s in near][:4])
