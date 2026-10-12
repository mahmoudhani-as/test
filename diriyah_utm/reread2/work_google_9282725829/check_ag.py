"""Check transcribed ad group pages against the 11-Oct inventory (adset_status, campaign_id)."""
import json, sys, glob, os
ROOT = sys.argv[1]
W = os.path.dirname(os.path.abspath(__file__))
live = [json.loads(l) for l in open(f'{ROOT}/live/google_9282725829.jsonl')]
lag = {}
for r in live:
    if r.get('adset_id'):
        lag.setdefault(r['adset_id'], set()).add((r['adset_status'], r['campaign_id']))
need = open(os.path.join(W, 'needed_adgroups.txt')).read().split(',')
got = {}
for f in sorted(glob.glob(os.path.join(W, 'adgroups_p*.txt'))):
    for n, line in enumerate(open(f), 1):
        line = line.rstrip('\n')
        if not line.strip():
            continue
        ag, st, suf, cid = line.split('|')
        if ag in got:
            print('DUP', ag)
        got[ag] = (st, suf, cid)
        if st not in ('ENABLED', 'PAUSED', 'REMOVED'):
            print('BAD STATUS', f, n, line)
        if suf:
            print('SUFFIX', ag, suf)
        if ag in lag:
            old = lag[ag]
            if len(old) != 1:
                print('MULTI 11-Oct', ag, old)
            (ost, ocid), = list(old)[:1]
            if ocid != cid:
                print('CAMPAIGN DIFF', ag, ocid, '->', cid)
            if ost != st:
                print('STATUS CHANGED', ag, ost, '->', st)
        elif ag not in need:
            print('UNEXPECTED', ag)
print('got', len(got), 'needed', len(need), 'missing', len([a for a in need if a not in got]))
