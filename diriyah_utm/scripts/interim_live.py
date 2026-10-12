"""Interim live state when a re-read is partial: python3 scripts/interim_live.py <dir> <base live json> <reread out dir> <apply folder> <out json>
base (e.g. work/live_interim.json) <- keyed re-read rows of the accounts already re-read <- read-backs of the apply run (after_live; sitelink assets: every placement)."""
import sys, json, glob, os, re
W, BASE, RR, A, OUT = sys.argv[1:6]
L = json.load(open(f'{W}/{BASE}'))
n_rr = 0
for f in glob.glob(f'{W}/{RR}/*.jsonl'):
    if os.path.basename(f).startswith('new_'): continue
    for l in open(f):
        if not l.strip(): continue
        try: x = json.loads(l)
        except Exception: continue
        L[f"{x['platform']}|{x['ad_id']}|{x['slot']}"] = {k: x.get(k) for k in ('url', 'status_now', 'found', 'note', 'creative_id_now')}; n_rr += 1
sl = {}
for k in L:
    p, aid, slot = k.split('|', 2)
    m = re.search(r'sitelink asset (\d+)', slot)
    if p == 'google' and m: sl.setdefault(m.group(1), []).append(k)
n_ap = 0
for f in sorted(glob.glob(f'{W}/{A}/out_*.jsonl')):
    for l in open(f):
        if not l.strip(): continue
        try: x = json.loads(l)
        except Exception: continue
        if not x.get('after_live') or x['result'] == 'NotAttempted': continue
        keys = sl.get(str(x['unit']), []) if x.get('unit_type') == 'sitelink_asset' else [f"{x['platform']}|{a}|{x['slot']}" for a in x.get('ad_ids') or []]
        for k in keys:
            if k in L: L[k] = {**L[k], 'url': x['after_live'], 'note': f"read back during the {A} run ({x['result']})"}; n_ap += 1
json.dump(L, open(f'{W}/{OUT}', 'w'), indent=0)
print('rows', len(L), 're-read rows applied', n_rr, 'apply read-backs applied', n_ap)
