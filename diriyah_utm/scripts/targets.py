"""Final target URL for every live URL slot (computed from the 11-Oct inventory = the URLs before any fix), and a diff
against a fresh live pull.  Usage:
  python3 scripts/targets.py <dir>                      -> work/targets.json (one row per 11-Oct slot with its target)
  python3 scripts/targets.py <dir> <fresh_live_dir>     -> also work/diff.json: slots whose live URL != target, and the after %
Target priority: generator-derived URL (derive FIX/OK) > legacy rebuild (legacy_clash_items) > omit rule (omit_items).
A slot with no target is listed with the reason (shared creative needing a split, serving month not pulled yet, ...)."""
import sys, os, json, glob, collections
from urllib.parse import urlsplit, parse_qsl
W = sys.argv[1]
S = json.load(open(f'{W}/work/scored.json'))
LEG = json.load(open(f'{W}/work/legacy_clash_items.json'))
OM = json.load(open(f'{W}/work/omit_items.json')) if os.path.exists(f'{W}/work/omit_items.json') else []
NEED = {(n['platform'], str(n['ad_id'])) for n in json.load(open(f'{W}/work/omit_need_serving.json'))} if os.path.exists(f'{W}/work/omit_need_serving.json') else set()
V5 = json.load(open(f'{W}/work/apply_plan_v5.json')) if os.path.exists(f'{W}/work/apply_plan_v5.json') else {'plan': [], 'skipped': []}
P1 = json.load(open(f'{W}/work/apply_plan.json'))
key = lambda s: (s['platform'], str(s.get('ad_id')), s.get('slot'))
tgt, why = {}, {}
for o in OM:
    if not o.get('check'): tgt[key(o)] = (o['expected_url'], o['kind'])
for i in LEG: tgt[key(i)] = (i['expected_url'], i['kind'])
for s in S:
    if s.get('url') and s['derive_status'] in ('FIX', 'OK') and s.get('expected_url'): tgt[key(s)] = (s['expected_url'], 'generator')
skip_ads = {}
for u in P1['skipped'] + V5['skipped']:
    for a in u['ad_ids']: skip_ads[(u['platform'], str(a))] = u['skip_reason']
rows = []
for s in S:
    if not s.get('url'): continue
    k = key(s); t = tgt.get(k)
    r = {'platform': s['platform'], 'account_id': s.get('account_id'), 'account_name': s.get('account_name'), 'campaign_name': s.get('campaign_name'),
         'adset_name': s.get('adset_name'), 'ad_id': str(s.get('ad_id')), 'ad_name': s.get('ad_name'), 'creative_id': s.get('creative_id'), 'slot': s.get('slot'),
         'status_11oct': s.get('effective_status') or s.get('ad_status'), 'url_11oct': s['url'], 'target': t[0] if t else None, 'source': t[1] if t else None}
    if (s['platform'], str(s.get('ad_id'))) in skip_ads: r['manual'] = 'shared creative/card: ' + skip_ads[(s['platform'], str(s.get('ad_id')))]
    if not t: r['no_target'] = 'serving month not pulled yet' if (s['platform'], str(s.get('ad_id'))) in NEED else 'no target (see legacy/omit outputs)'
    rows.append(r)
json.dump(rows, open(f'{W}/work/targets.json', 'w'), indent=1, default=str)
print('slots', len(rows), 'with target', sum(1 for r in rows if r['target']), collections.Counter(r['source'] for r in rows))
print('no target', collections.Counter(r.get('no_target') for r in rows if not r['target']))
if len(sys.argv) > 2:
    live = {}
    for f in glob.glob(os.path.join(sys.argv[2], '*.jsonl')):
        for line in open(f):
            if line.strip():
                x = json.loads(line)
                live[(x['platform'], str(x.get('ad_id')), x.get('slot'))] = x
    norm = lambda u: (lambda p: (p.scheme, p.netloc.lower(), p.path, p.fragment, tuple(sorted(parse_qsl(p.query, keep_blank_values=True)))))(urlsplit((u or '').strip()))
    diff, c = [], collections.Counter()
    for r in rows:
        x = live.get((r['platform'], r['ad_id'], r['slot']))
        r['url_now'] = x.get('url') if x else None
        if not x: c['gone from live'] += 1; continue
        if not r['target']: c['no target'] += 1; continue
        if norm(r['url_now']) == norm(r['target']): c['correct'] += 1
        else: c['needs edit' + (' (manual: shared)' if r.get('manual') else '')] += 1; diff.append(r)
    new = [k for k in live if k not in {(r['platform'], r['ad_id'], r['slot']) for r in rows} and live[k].get('url')]
    json.dump(diff, open(f'{W}/work/diff.json', 'w'), indent=1, default=str)
    tot = sum(c.values()) - c['gone from live']
    print(dict(c), 'new slots since 11-Oct (score them with the pipeline):', len(new))
    print(f"after: correct {c['correct']}/{tot} = {c['correct'] / tot:.1%}" if tot else '')
