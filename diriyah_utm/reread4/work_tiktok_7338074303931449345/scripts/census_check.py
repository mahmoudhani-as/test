# usage: python3 -I census_check.py
# Compares the final census reads (ad/get STATUS_ALL page_size 100, fields ad_id/secondary_status/operation_status/modify_time,
# all pages; smart_plus/ad/get STATUS_ALL page_size 100, fields secondary_status/operation_status/modify_time, all pages),
# made AFTER the full-field reads, with the snapshot built from the full-field reads. Any ad that is new, missing, or whose
# modify_time / secondary_status / operation_status differs must be re-read before the outputs are final.
import collections
import datetime
import json

BASE = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
ACC = '7338074303931449345'
W = f'{BASE}/reread4/work_tiktok_{ACC}'
C = json.load(open(f'{W}/data/collected.json', encoding='utf-8'))
S = json.load(open(f'{W}/data/snapshot.json', encoding='utf-8'))


def req_utc(rid):
    return (datetime.datetime.strptime(rid[:14], '%Y%m%d%H%M%S') - datetime.timedelta(hours=8)).strftime('%H:%M:%S')


ad_pages, sp_pages = {}, {}
for x in C:
    i = x['input'] or {}
    p = i.get('params') or {}
    flds = p.get('fields') or []
    if (p.get('filtering') or {}) != {'primary_status': 'STATUS_ALL'} or p.get('page_size') != 100:
        continue
    if i.get('action') == 'tiktok_ad_get' and 'campaign_automation_type' not in flds:
        tgt = ad_pages
    elif i.get('action') == 'tiktok_smart_plus_ad_get' and 'landing_page_url_list' not in flds:
        tgt = sp_pages
    else:
        continue
    r = x['result']
    d = r['data']['data']
    assert d['code'] == 0 and not (r.get('meta') or {}).get('mcp_output_budget')
    lst = d['data']['list']
    assert all(isinstance(it, dict) for it in lst)
    tgt[p['page']] = (lst, d['data']['page_info'], d['request_id'])


def merge(pages, key, name):
    pi = {v[1]['total_page'] for v in pages.values()}
    tn = {v[1]['total_number'] for v in pages.values()}
    assert len(pi) == 1 and sorted(pages) == list(range(1, pi.pop() + 1)), (name, sorted(pages))
    out = {}
    for pg in sorted(pages):
        for it in pages[pg][0]:
            assert it[key] not in out, (name, 'dup', it[key])
            out[it[key]] = it
    assert len(out) == tn.pop(), name
    print(name, len(out), 'rows; requests', [(pages[pg][2], req_utc(pages[pg][2])) for pg in sorted(pages)])
    return out


ad_c = merge(ad_pages, 'ad_id', 'final ad/get census')
sp_c = merge(sp_pages, 'smart_plus_ad_id', 'final smart_plus/ad/get census')
chg = []
man, sp, census = S['manual'], S['smart_plus'], S['census']
F = ('modify_time', 'secondary_status', 'operation_status')
for a, v in ad_c.items():
    ref = man.get(a) or census.get(a)
    if ref is None:
        chg.append(('new ad row (not in first census / manual read)', a, v))
        continue
    d = [(f, ref.get(f), v.get(f)) for f in F if ref.get(f) != v.get(f)]
    if d:
        chg.append(('ad changed', a, d))
for a in set(census) - set(ad_c):
    chg.append(('ad row missing from final census', a))
for a, v in sp_c.items():
    ref = sp.get(a)
    if ref is None:
        chg.append(('new Smart+ ad', a, v))
        continue
    d = [(f, ref.get(f), v.get(f)) for f in F if ref.get(f) != v.get(f)]
    if d:
        chg.append(('smart+ changed', a, d))
for a in set(sp) - set(sp_c):
    chg.append(('smart+ missing from final census', a))
print('changes since the full-field reads:', len(chg))
for c in chg:
    print('  ', c)
