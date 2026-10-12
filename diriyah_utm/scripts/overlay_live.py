"""Overlay the read-backs of an apply run on the keyed re-read: python3 scripts/overlay_live.py <dir> <apply folder> <out json>
Every Fixed / AlreadyFixed / Failed / Skipped line carries what the agent read live (after_live); it replaces the re-read URL of that slot
(sitelink assets: every placement of the asset)."""
import sys, json, glob, re
W, A, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
L = json.load(open(f'{W}/work/live_now.json'))
sl = {}
for k in L:
    p, aid, slot = k.split('|', 2)
    m = re.search(r'sitelink asset (\d+)', slot)
    if p == 'google' and m: sl.setdefault(m.group(1), []).append(k)
n = 0
for f in sorted(glob.glob(f'{W}/{A}/out_*.jsonl')):
    for l in open(f):
        if not l.strip(): continue
        try: x = json.loads(l)
        except Exception: continue
        if not x.get('after_live') or x['result'] == 'NotAttempted': continue
        keys = sl.get(str(x['unit']), []) if x.get('unit_type') == 'sitelink_asset' else [f"{x['platform']}|{a}|{x['slot']}" for a in x.get('ad_ids') or []]
        for k in keys:
            if k in L: L[k] = {**L[k], 'url': x['after_live'], 'note': f"read back after the {A} write ({x['result']})"}; n += 1
json.dump(L, open(OUT, 'w'), indent=0)
print('overlaid', n)
