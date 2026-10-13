import json, sys
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply9/work_google_3')
from lib import *

def rows_of(rid):
    rs, trunc, budget, inp = gaql_rows(rid)
    return parse_rows(rs, rid)

U = units()
# write steps: (ids, pre-read req ids, dry-run req, live req, read-back req ids, idempotency key, mask label)
steps = [
    (['800023610878'], ['dc356697-5888-4c3f-8346-69c689cb5a73'], 'd086a6a6-629e-49e8-9e24-7594f6e8847d', '4efde23d-2a02-416c-a48a-d20c2d8997a2', ['b0043d96-9f9d-443b-be3a-3b5180922d56'], '66bb738a-277b-4c7d-986a-1aabcc91b9fa'),
    (None, ['b0043d96-9f9d-443b-be3a-3b5180922d56'], '48901003-8c6f-4a81-8487-4590823d0f24', 'af0802cc-1700-42c7-8d98-71c5ec0b229b', ['183f367a-f51a-4668-afee-864e265c1b5e'], '38a72291-3136-4377-9e85-f23e1f73bf9b'),
    (['810176320945'], ['183f367a-f51a-4668-afee-864e265c1b5e'], '5f9d2140-57ae-4b9d-8a29-69028104e23f', '8d5b905b-5342-4e36-9260-9727504d7ad2', ['bb991ac7-a61d-4c3a-aa6c-1a70a533198c'], '162940b5-4e13-447e-8fe1-9cea9550a549'),
    (None, ['bb991ac7-a61d-4c3a-aa6c-1a70a533198c', '5a853c51-dda1-4319-bc3b-296dd3deb052'], '794e155d-f276-4b09-bd8d-3fa3611de35d', '484b99d4-2797-4461-b159-889930628c67', ['d3c4da44-06ee-4890-b4a8-cdac0d272d97', '3e4f586c-72e4-4a70-ad14-716981ba3790'], 'effb48e4-11f0-438f-9cc8-ed3970fb1d8d'),
]
info = {}
for ids, pre, dry, live, rb, key in steps:
    inp, lj = result_by_request_id(live)
    sent_ops = inp['params']['operations']
    live_res = lj['data']['data']['data']['results']
    pf = lj['data']['data']['data'].get('partialFailureError')
    _, dj = result_by_request_id(dry)
    dry_ops = dj['data']['body']['operations']
    assert inp['params'] == result_by_request_id(dry)[0]['params'], 'dry/live params differ'
    pre_rows = {}
    for r in pre:
        for k, v in rows_of(r).items():
            pre_rows.setdefault(k, v)
    rb_rows = {}
    for r in rb:
        for k, v in rows_of(r).items():
            rb_rows.setdefault(k, v)
    for i, op in enumerate(sent_ops):
        aid = op['update']['resource_name'].split('/')[-1]
        res = live_res[i]
        err = None
        if not res.get('resourceName'):
            for det in (pf or {}).get('details', []):
                for e in det.get('errors', []):
                    idx = [f.get('index') for f in e.get('location', {}).get('fieldPathElements', []) if f.get('fieldName') == 'operations']
                    if idx and idx[0] == i:
                        topics = [(t.get('type'), t.get('topic')) for t in e.get('details', {}).get('policyFindingDetails', {}).get('policyTopicEntries', [])]
                        err = {'code': e.get('errorCode'), 'message': e.get('message'), 'topics': topics, 'google_request_id': det.get('requestId')}
        info[aid] = {'pre': pre_rows[aid][0], 'rb': rb_rows[aid][0], 'dry': dry, 'live': live, 'key': key, 'op_index': i, 'n_ops': len(sent_ops),
                     'mask': op['update_mask'], 'dry_op_same': dry_ops[i] == op, 'res': res, 'err': err}

results = []
for u in U:
    ch = u['changes'][0]
    aid = u['unit']
    x = info[aid]
    pre, rb = x['pre'], x['rb']
    before = pre['landing']
    after = rb['landing']
    assert before == ch['now'], aid
    byte_eq = rb['final_urls'] == [ch['new']] and not rb['final_url_suffix'] and after == ch['new']
    suffix_note = ''
    if pre['final_url_suffix']:
        suffix_note = ' Before = final_urls[0] + %s + ad-level final_url_suffix (old UTMs/ValueTrack lived in the ad suffix); the same op set final_url_suffix "" (update_mask final_urls,final_url_suffix) and the read-back shows no suffix.' % ("'&'" if '?' in pre['final_urls'][0] else "'?'")
    status_note = ' Ad status %s and campaign %s unchanged (pre %s/%s); approval %s -> %s.' % (rb['status'], rb['campaign_status'], pre['status'], pre['campaign_status'], pre['approval'], rb['approval'])
    if x['err'] is None and byte_eq:
        result = 'Fixed'
        detail = ('AdService MutateAds (google_ads_v23_ad_mutate_ads) update customers/%s/ads/%s, update_mask %s, op %d of %d%s. '
                  'Pre-read GAQL req %s: live == now (exact). Dry-run req %s: preview body held only resource_name/final_urls%s. '
                  'Live req %s (idempotency_key %s) returned %s. Read-back GAQL req %s: final_urls == [new] byte for byte, no ad/ad group/campaign/account suffix or tracking template.%s%s'
                  % (u['account_id'], aid, x['mask'], x['op_index'] + 1, x['n_ops'], ' (partial_failure true)' if x['n_ops'] > 1 else '',
                     pre['req'], x['dry'], '/final_url_suffix ""' if pre['final_url_suffix'] else '', x['live'], x['key'], x['res'].get('resourceName'), rb['req'], suffix_note, status_note))
        if rb['approval'] == 'UNKNOWN':
            detail += ' Side effect: Google re-reviews the ad after a URL change (approval_status UNKNOWN at read-back).'
    else:
        result = 'Failed'
        e = x['err']
        detail = ('Google Ads refused the update (not written). MutateAds live req %s (idempotency_key %s, partial_failure true, op %d of %d, update_mask %s) returned partialFailureError for this op: %s "%s" policy topics %s, Google requestId %s. '
                  'Pre-read GAQL req %s: live == now (exact); dry-run req %s preview held only resource_name/final_urls/final_url_suffix "". '
                  'Read-back GAQL req %s: unchanged (final_urls [%s], ad-level final_url_suffix still set). Ad is PAUSED and was already DISAPPROVED before the write; campaign PAUSED. '
                  'Not retried: deterministic platform policy refusal (same class as the platform-refused list); the target page needs fixing or a different destination before any retry.'
                  % (x['live'], x['key'], x['op_index'] + 1, x['n_ops'], x['mask'], json.dumps(e['code']), e['message'], e['topics'], e['google_request_id'],
                     pre['req'], x['dry'], rb['req'], rb['final_urls'][0]))
    results.append({'platform': 'google', 'account_id': u['account_id'], 'unit_type': u['unit_type'], 'unit': aid,
                    'ad_ids': u['ad_ids'], 'ad_names': [n for n in u['ad_names'] if n is not None],
                    'slot': ch['slot'], 'before': before, 'after_expected': ch['new'], 'after_live': after,
                    'result': result, 'new_entity_ids': '', 'detail': detail})
from collections import Counter
print(Counter(r['result'] for r in results), len(results))
json.dump(results, open(W + '/results_final.json', 'w'), ensure_ascii=False, indent=1)
# sanity
for r, u in zip(results, U):
    assert r['after_expected'] == u['changes'][0]['new']
    assert r['before'] == u['changes'][0]['now']
    if r['result'] == 'Fixed':
        assert r['after_live'] == r['after_expected']
print('dry ops identical to live ops:', all(v['dry_op_same'] for v in info.values()))
print([ (r['unit'], r['detail'][:400]) for r in results if r['result'] != 'Fixed'])
print(results[0]['detail'])
print(results[20]['detail'])
