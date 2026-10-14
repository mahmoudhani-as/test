"""Plan id chunks for the 14-Oct detail reads so each MCP result is > 50,000 chars (saved to a file instead of inlined)
and < 65,536 bytes (the gateway's output cap). Per-ad sizes are simulated from the 13-Oct detail records (reread5), with the
creative name dropped (not requested any more). The simulation is first calibrated against the 13-Oct calls' real sizes.
Usage: make_chunks.py IN_FILE PREV_CALLS PREV_DETAILS OUT_JSON LO_CHARS HI_BYTES"""
import json, sys, copy
IN_FILE, PREV_CALLS, PREV, OUT, LO, HI = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]), int(sys.argv[6])
ACC = '2194833637927644'


def envelope(records, aggregate):
    inner = {'data': records}
    if aggregate:
        inner['meta'] = {'aggregate_pages': True, 'pages_fetched': 1}
    return {'success': True,
            'data': {'success': True, 'action': 'meta_ad_account_id_ads_get', 'method': 'GET', 'host': 'graph.facebook.com',
                     'path': '/v25.0/act_%s/ads' % ACC, 'dryRun': False, 'data': inner,
                     'meta': {'requestId': None, 'waitedMs': 1234, 'throttled': False, 'warnings': [], 'compatibility': None,
                              'compatibilitySkipped': True, 'mcp_result_projection': {'compact': True}}},
            'meta': {'requestId': '00000000-0000-0000-0000-000000000000', 'latencyMs': 12345}}


def size(records, aggregate=True):
    s = json.dumps(envelope(records, aggregate), indent=2, ensure_ascii=False)
    return len(s), len(s.encode('utf-8'))


# ---- calibration against the 13-Oct calls ----
calls = json.load(open(PREV_CALLS, encoding='utf-8'))
for i, c in enumerate(calls):
    inp = c['input'] or {}
    if inp.get('action') != 'meta_ad_account_id_ads_get' or 'filtering' not in (inp.get('params') or {}):
        continue
    if '"id"' not in inp['params']['filtering']:
        continue
    recs = c['payload']['data']['data']['data']
    ch, by = size(recs, aggregate=bool(inp.get('aggregate_pages')))
    print('calib call', i, 'n', len(recs), 'raw_len', c['raw_len'], 'sim chars', ch, 'sim bytes', by, 'diff', c['raw_len'] - ch)

# ---- plan ----
rows = json.load(open(IN_FILE, encoding='utf-8'))
inv = json.load(open('data/inventory.json', encoding='utf-8'))
prev = json.load(open(PREV, encoding='utf-8'))
in_ids = []
for r in rows:
    if r['ad_id'] not in in_ids:
        in_ids.append(r['ad_id'])
new_ids = [a for a in inv if a not in set(in_ids) and inv[a]['effective_status'] != 'DELETED']


def rec(aid, with_names):
    p = copy.deepcopy(prev.get(aid))
    if p is None:
        return None
    (p.get('creative') or {}).pop('name', None)
    if not with_names:
        p.pop('campaign', None); p.pop('adset', None)
    elif 'campaign' not in p:
        p['campaign'] = {'name': 'x' * 60, 'id': '1' * 18}; p['adset'] = {'name': 'x' * 60, 'id': '1' * 18}
    return p


def pack(ids, with_names):
    # balanced: the fewest chunks that keep every chunk under HI bytes, then cut at even shares of the total
    for aid in ids:
        if rec(aid, with_names) is None:
            print('no 13-Oct record for', aid)
    per = [size([rec(aid, with_names) or {}])[1] - size([])[1] for aid in ids]
    total = sum(per)
    n = 1
    while True:
        target = total / n
        chunks, cur, acc, k = [], [], 0.0, 1
        for aid, s in zip(ids, per):
            if cur and acc + s / 2 > target * k:
                chunks.append(cur); cur = []; k += 1
            cur.append(aid); acc += s
        if cur:
            chunks.append(cur)
        if all(size([rec(a, with_names) or {} for a in c])[1] <= HI for c in chunks):
            break
        n += 1
    out = []
    for c in chunks:
        ch, by = size([rec(a, with_names) or {} for a in c])
        out.append({'ids': c, 'sim_chars': ch, 'sim_bytes': by})
    return out


plan = {'input_chunks': pack(in_ids, False), 'new_chunks': pack(new_ids, True), 'new_ids': new_ids}
json.dump(plan, open(OUT, 'w'), indent=1)
for k in ('input_chunks', 'new_chunks'):
    for i, c in enumerate(plan[k]):
        flag = '' if c['sim_chars'] > LO else '  <-- below the persist threshold'
        print(k, i, 'n', len(c['ids']), 'chars', c['sim_chars'], 'bytes', c['sim_bytes'], flag)
print('input ads', len(in_ids), 'new', len(new_ids))
