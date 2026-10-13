# usage: python3 -I census.py <collected.json> <census_out.json>
# Builds the account census from the ad/get reads with filtering {primary_status: STATUS_ALL}, page_size 100 and the
# compact census field set (no URL fields) - all pages, rejecting truncated pages. Later reads of the same page win.
import json, sys, collections
C = json.load(open(sys.argv[1], encoding='utf-8'))
CEN_FIELDS = sorted(["ad_id", "campaign_automation_type", "operation_status", "secondary_status", "modify_time", "create_time",
                     "tiktok_item_id", "identity_type", "identity_id", "identity_authorized_bc_id", "ad_format"])
pages, totals, problems = {}, set(), []
for r in C:
    inp = r['input'] or {}
    if inp.get('action') != 'tiktok_ad_get':
        continue
    p = inp.get('params') or {}
    if (p.get('filtering') or {}) != {"primary_status": "STATUS_ALL"} or p.get('page_size') != 100:
        continue
    if sorted(p.get('fields') or []) != CEN_FIELDS:
        continue
    res = r['result']
    inner = res['data']['data']
    if inner.get('code') != 0:
        problems.append(('api code', r['seq'], inner.get('code'), inner.get('message'))); continue
    dd = inner['data']; lst = dd['list']
    if any(not isinstance(x, dict) for x in lst):
        problems.append(('truncated census page', r['seq'], p['page'])); continue
    pages[p['page']] = (lst, inner.get('request_id'), r['seq'])
    totals.add(dd['page_info']['total_number'])
rows, dup = {}, []
for k in sorted(pages):
    for x in pages[k][0]:
        if x['ad_id'] in rows: dup.append(x['ad_id'])
        rows[x['ad_id']] = dict(x, _page=k, _request_id=pages[k][1])
tot = sorted(totals)
need = (tot[0] + 99) // 100 if tot else None
print('pages', sorted(pages), 'need', need, 'total_number', tot, 'rows', len(rows), 'dups', dup)
if need and sorted(pages) != list(range(1, need + 1)): problems.append(('missing pages', sorted(set(range(1, need + 1)) - set(pages))))
if tot and len(rows) != tot[0]: problems.append(('row count != total_number', len(rows), tot))
print('by type', collections.Counter(x.get('campaign_automation_type') for x in rows.values()))
print('by status', collections.Counter(x.get('secondary_status') for x in rows.values()).most_common())
print('request_ids', {k: v[1] for k, v in sorted(pages.items())})
json.dump({'rows': rows, 'request_ids': {k: v[1] for k, v in pages.items()}, 'total_number': tot, 'problems': problems},
          open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False)
print('problems', problems)
