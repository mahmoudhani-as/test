# usage: python3 -I snapshot.py <collected.json> <snapshot_out.json>
# Builds the current-state snapshot from the paged reads: manual ads (ad/get MANUAL, STATUS_ALL, page_size 34, pages 1-19)
# and Upgraded Smart+ ads (smart_plus/ad/get STATUS_ALL, page_size 40, pages 1-3). Takes the LAST complete read of each page.
import json, sys
C = json.load(open(sys.argv[1]))
man_pages, sp_pages, reqs = {}, {}, []
for r in C:
    inp = r['input'] or {}
    p = inp.get('params') or {}
    res = r["result"]
    if inp.get("action") not in ("tiktok_ad_get", "tiktok_smart_plus_ad_get"):
        continue
    if not isinstance(res, dict) or not res.get('success'):
        continue
    inner = res['data']['data']
    if inner.get('code') != 0:
        continue
    dd = inner.get('data') or {}
    lst = dd.get('list') or []
    if any(not isinstance(x, dict) for x in lst):
        continue  # truncated page, ignore
    f = p.get('filtering') or {}
    if inp.get('action') == 'tiktok_ad_get' and f == {"primary_status": "STATUS_ALL", "campaign_automation_type": "MANUAL"} and p.get('page_size') == 34:
        man_pages[p['page']] = (lst, dd['page_info'], inner.get('request_id'))
    if inp.get('action') == 'tiktok_smart_plus_ad_get' and f == {"primary_status": "STATUS_ALL"} and p.get('page_size') == 40:
        sp_pages[p['page']] = (lst, dd['page_info'], inner.get('request_id'))
man, sp = {}, {}
for k in sorted(man_pages):
    for x in man_pages[k][0]:
        man[x['ad_id']] = x
for k in sorted(sp_pages):
    for x in sp_pages[k][0]:
        sp[x['smart_plus_ad_id']] = x
print('manual pages', sorted(man_pages), 'ads', len(man), 'totals', {v[1]['total_number'] for v in man_pages.values()})
print('smart+ pages', sorted(sp_pages), 'ads', len(sp), 'totals', {v[1]['total_number'] for v in sp_pages.values()}, 'rows', sum(len(v[0]) for v in sp_pages.values()))
snap = {'manual': man, 'smart_plus': sp,
        'manual_request_ids': {k: v[2] for k, v in man_pages.items()},
        'smart_plus_request_ids': {k: v[2] for k, v in sp_pages.items()},
        'manual_total_number': sorted({v[1]['total_number'] for v in man_pages.values()}),
        'smart_plus_total_number': sorted({v[1]['total_number'] for v in sp_pages.values()})}
json.dump(snap, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
