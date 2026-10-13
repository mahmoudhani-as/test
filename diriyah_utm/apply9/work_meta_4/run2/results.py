import json, sys
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply9/work_meta_4/run2')
import lib10 as L

def ad_reads(ad):
    return L.find_calls('meta_ad_id_get', lambda i: (i.get('path_params') or {}).get('ad_id') == ad)

def slot_of(read_res, slot):
    data, d = L.ok_data(read_res)
    return L.full_landing(data['creative'], slot), data, d['meta']['requestId']

out = []
for u in L.units():
    ad = u['unit']
    reads = ad_reads(ad)
    for c in u['changes']:
        first_cur, first_ad, first_rid = slot_of(reads[0][2], c['slot'])
        last_cur, last_ad, last_rid = slot_of(reads[-1][2], c['slot'])
        out.append({
            'platform': 'meta', 'account_id': u['account_id'], 'unit_type': u['unit_type'], 'unit': ad,
            'ad_ids': u['ad_ids'], 'ad_names': u['ad_names'], 'slot': c['slot'],
            'before': first_cur, 'after_expected': c['new'], 'after_live': last_cur,
            '_pre': (first_ad['creative']['id'], first_ad['configured_status'], first_ad['effective_status'], first_rid, first_cur == c['now'], L.same_url(first_cur, c['new'])),
            '_post': (last_ad['creative']['id'], last_ad['configured_status'], last_ad['effective_status'], last_rid, last_cur == c['new'], last_ad['updated_time']),
            '_n_reads': len(reads),
        })
json.dump(out, open(L.W + 'results_raw.json', 'w'), ensure_ascii=False, indent=1)
for r in out:
    print(r['unit'], 'pre', r['_pre'], '| post', r['_post'], '| reads', r['_n_reads'])
    print('  before    ', r['before'])
    print('  after_live', r['after_live'])
    print('  expected  ', r['after_expected'])
