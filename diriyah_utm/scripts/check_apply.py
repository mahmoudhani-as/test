"""Check apply results against the plan: python3 scripts/check_apply.py <dir> <apply folder> [platform]
Per input change: result line present, Fixed => after_live == after_expected == plan 'new' (query-order-insensitive), AlreadyFixed => after_live == new."""
import sys, json, glob, os, collections
from urllib.parse import urlsplit, parse_qsl
W, A = sys.argv[1], sys.argv[2]; P = sys.argv[3] if len(sys.argv) > 3 else None
norm = lambda u: (lambda p: (p.scheme, p.netloc.lower(), p.path, p.fragment, tuple(sorted(parse_qsl(p.query, keep_blank_values=True)))))(urlsplit((u or '').strip()))
c = collections.Counter(); probs = []
for f in sorted(glob.glob(f'{W}/{A}/in_*.json')):
    plat = os.path.basename(f)[3:].split('_')[0]
    if P and plat != P: continue
    o = f.replace('/in_', '/out_').replace('.json', '.jsonl')
    if not os.path.exists(o): c[(plat, 'batch not run')] += 1; continue
    res = collections.defaultdict(list)
    for l in open(o):
        if l.strip():
            try: x = json.loads(l)
            except Exception: c[(plat, 'bad line')] += 1; continue
            res[(str(x.get('unit')), x.get('slot'))].append(x)
    for u in json.load(open(f)):
        for ch in u['changes']:
            r = res.get((str(u['unit']), ch['slot']))
            if not r: c[(plat, 'NO RESULT LINE')] += 1; probs.append((os.path.basename(f), u['unit'], ch['slot'], 'no result')); continue
            x = r[-1]; c[(plat, x['result'])] += 1
            if x['result'] in ('Fixed', 'AlreadyFixed') and norm(x.get('after_live')) != norm(ch['new']):
                c[(plat, 'MISMATCH')] += 1; probs.append((os.path.basename(f), u['unit'], ch['slot'], 'after_live != new', x.get('after_live')))
            elif x['result'] in ('Fixed', 'AlreadyFixed') and (x.get('after_live') or '').strip() != ch['new']:
                c[(plat, 'same params, different order/encoding')] += 1
for k, v in sorted(c.items()): print(k, v)
for p in probs[:30]: print('PROBLEM', p)
