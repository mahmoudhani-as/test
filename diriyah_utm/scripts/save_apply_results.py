"""Save the results the apply8 agents returned (workflow journal) as <apply>/out_<batch>.jsonl + <apply>/lane_reports.json.
Usage: python3 scripts/save_apply_results.py <dir> <apply folder> <run_id>[,<run_id>...]
The agents of diriyah-apply-v8.js write no files: each returns one result object per change in its final answer."""
import sys, os, json, collections
W, A, RUNS = sys.argv[1], sys.argv[2], sys.argv[3].split(',')
D = '/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows'
reps = {}; c = collections.Counter()
for r in RUNS:
    lab = {}
    for l in open(f'{D}/{r}/journal.jsonl'):
        x = json.loads(l)
        if x['type'] == 'started': lab[x['key']] = x.get('label') or ''
        if x['type'] != 'result': continue
        b = lab.get(x['key'], '').split(':', 1)[-1]
        if not b.startswith('in_'): continue
        res = x.get('result') or {}
        plat = b[3:].split('_')[0]
        inp = {(str(u['unit']), ch['slot']): u for u in json.load(open(f'{W}/{A}/{b}')) for ch in u['changes']}
        lines = []
        for y in res.get('results') or []:
            y = dict(y); y.setdefault('platform', plat); y['unit'] = str(y.get('unit'))
            u = inp.get((y['unit'], y.get('slot')))
            if u:
                y.setdefault('account_id', u['account_id']); y.setdefault('unit_type', u['unit_type'])
                if not y.get('ad_ids'): y['ad_ids'] = [str(a) for a in u['ad_ids']]
                if not y.get('ad_names'): y['ad_names'] = u.get('ad_names') or []
            else: c['line not in input'] += 1
            y['ad_ids'] = [str(a) for a in y.get('ad_ids') or []]
            lines.append(y); c[(plat, y.get('result'))] += 1
        with open(f'{W}/{A}/{b.replace("in_", "out_").replace(".json", ".jsonl")}', 'w') as fh:
            for y in lines: fh.write(json.dumps(y, ensure_ascii=False) + '\n')
        missing = len(inp) - len({(y['unit'], y.get('slot')) for y in lines} & set(inp))
        reps[b] = {'run': r, 'systemic_error': res.get('systemic_error') or '', 'counts': {k: res.get(k) for k in ('fixed', 'already_fixed', 'failed', 'skipped', 'not_attempted')},
                   'n_results': len(lines), 'changes_without_result': missing, 'notes': res.get('notes') or ''}
        if missing: c[(plat, 'NO RESULT')] += missing
old = json.load(open(f'{W}/{A}/lane_reports.json')) if os.path.exists(f'{W}/{A}/lane_reports.json') else {}
old.update(reps); json.dump(old, open(f'{W}/{A}/lane_reports.json', 'w'), indent=1, ensure_ascii=False)
for k, v in sorted(c.items(), key=str): print(k, v)
print('batches saved:', sorted(reps))
