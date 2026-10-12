"""Check transcribed link pages against the input sitelink rows (live inventory link identity + 11-Oct link status)."""
import json, sys, glob, os, re, collections
ROOT = sys.argv[1]
W = os.path.dirname(os.path.abspath(__file__))
live = [json.loads(l) for l in open(f'{ROOT}/live/google_9282725829.jsonl')]
exp_ca, exp_aga = {}, {}
for r in live:
    if r['slot'].endswith('(campaign_asset)'):
        exp_ca[(r['campaign_id'], r['ad_id'])] = r['ad_status']
    elif r['slot'].endswith('(ad_group_asset)'):
        exp_aga[(r['adset_id'], r['ad_id'])] = r['ad_status']
for kind, pat, exp in (('campaign_asset', 'links_ca_p*.txt', exp_ca), ('ad_group_asset', 'links_aga_p*.txt', exp_aga)):
    got = {}
    for f in sorted(glob.glob(os.path.join(W, pat))):
        for n, line in enumerate(open(f), 1):
            line = line.rstrip('\n')
            if not line.strip():
                continue
            a, b, st = line.split('|')
            if (a, b) in got:
                print('DUP', kind, a, b)
            got[(a, b)] = st
            if st not in ('ENABLED', 'PAUSED', 'REMOVED'):
                print('BAD STATUS', f, n, line)
    extra = [k for k in got if k not in exp]
    missing = [k for k in exp if k not in got]
    changed = [(k, exp[k], got[k]) for k in exp if k in got and exp[k] != got[k]]
    print(kind, 'got', len(got), 'expected(input)', len(exp), 'extra(not in input)', len(extra), 'missing', len(missing), 'status changed', changed[:20])
    if extra:
        print('  extra sample', extra[:10])
    if missing:
        print('  missing sample', missing[:10])
