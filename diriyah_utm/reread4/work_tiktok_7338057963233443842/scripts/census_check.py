# usage: python3 -I census_check.py <collected.json> <snapshot.json>
# Compares the final census reads (ad/get STATUS_ALL page_size 100 fields ad_id/modify_time/secondary_status, all pages;
# smart_plus/ad/get STATUS_ALL page_size 100) with the full-field snapshot: any ad whose modify_time or secondary_status
# differs (or that is new) must be re-read.
import json, sys
C = json.load(open(sys.argv[1], encoding='utf-8'))
S = json.load(open(sys.argv[2], encoding='utf-8'))
man, sp = S['manual'], S['smart_plus']
cen_pages, sp_cen, tot = {}, {}, set()
for r in C:
    inp = r['input'] or {}
    p = inp.get('params') or {}
    if p.get('page_size') != 100 or (p.get('filtering') or {}) != {"primary_status": "STATUS_ALL"}:
        continue
    if sorted(p.get('fields') or []) not in (sorted(['ad_id', 'modify_time', 'secondary_status']), sorted(['smart_plus_ad_id', 'modify_time', 'secondary_status'])):
        continue
    res = r['result']
    dd = res['data']['data']['data']
    lst = dd['list']
    assert all(isinstance(x, dict) for x in lst), 'truncated census page'
    if inp['action'] == 'tiktok_ad_get':
        cen_pages[p['page']] = (lst, res['data']['data']['request_id'])
        tot.add(dd['page_info']['total_number'])
    else:
        for x in lst:
            sp_cen[x['smart_plus_ad_id']] = x
        print('smart+ census', len(lst), 'total', dd['page_info']['total_number'], res['data']['data']['request_id'])
print('ad/get census pages', sorted(cen_pages), 'total_number', tot)
rows = {}
dups = 0
for k in sorted(cen_pages):
    for x in cen_pages[k][0]:
        if x['ad_id'] in rows:
            dups += 1
        rows[x['ad_id']] = x
print('census rows', len(rows), 'dups', dups)
chg = []
seen_man = 0
for aid, a in man.items():
    x = rows.get(aid)
    if x is None:
        chg.append(('manual missing from census', aid))
        continue
    seen_man += 1
    if x.get('modify_time') != a.get('modify_time') or x.get('secondary_status') != a.get('secondary_status'):
        chg.append(('manual changed', aid, a.get('modify_time'), x.get('modify_time'), a.get('secondary_status'), x.get('secondary_status')))
others = [aid for aid in rows if aid not in man]
print('manual matched in census', seen_man, '| census rows not manual (Smart+ creative rows expected 149):', len(others))
for sid, a in sp.items():
    x = sp_cen.get(sid)
    if x is None:
        chg.append(('smart missing from census', sid))
        continue
    if x.get('modify_time') != a.get('modify_time') or x.get('secondary_status') != a.get('secondary_status'):
        chg.append(('smart changed', sid, a.get('modify_time'), x.get('modify_time'), a.get('secondary_status'), x.get('secondary_status')))
for sid in sp_cen:
    if sid not in sp:
        chg.append(('smart new in census', sid))
print('changes since full read:', len(chg))
for c in chg:
    print('  ', c)
