"""Collect the per-ad detail records (id-filtered GET act_/ads reads) from data/calls.json into data/details.json and check coverage.
Usage: details.py IN_FILE first_detail_call_index"""
import json, sys
IN_FILE, FIRST = sys.argv[1], int(sys.argv[2])
calls = json.load(open('data/calls.json', encoding='utf-8'))
plan = json.load(open('data/chunks.json', encoding='utf-8'))
det = {}
bad = []
for i, c in enumerate(calls):
    if i < FIRST:
        continue
    inp = c['input'] or {}
    if inp.get('action') != 'meta_ad_account_id_ads_get':
        continue
    params = inp.get('params') or {}
    filt = json.loads(params['filtering']) if isinstance(params.get('filtering'), str) else params.get('filtering')
    idf = [f for f in (filt or []) if f['field'] == 'id']
    if not idf:
        continue
    want = idf[0]['value']
    if c['truncated'] or c['payload'] is None:
        print('call', i, 'TRUNCATED or unparsable; asked', len(want), 'len', c['raw_len'], c['source'][-60:])
        bad.append(i)
        continue
    items = c['payload']['data']['data']['data']
    if not all(isinstance(x, dict) for x in items):
        print('call', i, 'has a truncation marker item'); bad.append(i); continue
    got = [x['id'] for x in items]
    missing = sorted(set(want) - set(got))
    extra = sorted(set(got) - set(want))
    print('call', i, 'asked', len(want), 'got', len(got), 'missing', missing, 'extra', extra, 'len', c['raw_len'], 'src', 'file' if c['source'] != 'inline' else 'inline')
    for x in items:
        if x['id'] in det and det[x['id']] != x:
            print('  NOTE: ad', x['id'], 'differs between two reads; keeping the later read')
        det[x['id']] = x
json.dump(det, open('data/details.json', 'w', encoding='utf-8'), ensure_ascii=False)
rows = json.load(open(IN_FILE, encoding='utf-8'))
in_ids = {r['ad_id'] for r in rows}
print('details', len(det), 'input ads missing from details', len(in_ids - set(det)), sorted(in_ids - set(det))[:50])
print('new ads in plan', len(plan['new_ids']), 'missing from details', sorted(set(plan['new_ids']) - set(det)))
print('bad calls', bad)
