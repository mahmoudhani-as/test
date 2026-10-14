# usage: python3 -I urlpass.py <collected.json> <urls_out.json>
# Merges the URL-pass reads: ad/get filtering {primary_status: STATUS_NOT_DELETE, campaign_automation_type: MANUAL}
# (page_size 45 pages 1-7 and page_size 50 pages 7-12), rejecting truncated pages; rows keyed by ad_id; a row seen twice
# (page overlap) must be identical, otherwise the later read wins and the difference is reported.
import json, sys
C = json.load(open(sys.argv[1], encoding='utf-8'))
F = {"primary_status": "STATUS_NOT_DELETE", "campaign_automation_type": "MANUAL"}
rows, src, problems, totals, diffs, pages = {}, {}, [], set(), [], []
for r in C:
    inp = r['input'] or {}
    if inp.get('action') != 'tiktok_ad_get':
        continue
    p = inp.get('params') or {}
    if (p.get('filtering') or {}) != F:
        continue
    res = r['result']
    inner = res['data']['data']
    if inner.get('code') != 0:
        problems.append(('api code', r['seq'], inner.get('code'))); continue
    dd = inner['data']; lst = dd['list']
    if any(not isinstance(x, dict) for x in lst):
        problems.append(('truncated', r['seq'], p['page'], p['page_size'])); continue
    totals.add(dd['page_info']['total_number'])
    pages.append((p['page_size'], p['page'], len(lst), inner.get('request_id')))
    for x in lst:
        if x['ad_id'] in rows and rows[x['ad_id']] != x:
            diffs.append((x['ad_id'], rows[x['ad_id']], x))
        rows[x['ad_id']] = x
        src[x['ad_id']] = {'page_size': p['page_size'], 'page': p['page'], 'request_id': inner.get('request_id'), 'seq': r['seq']}
print('pages', pages)
print('total_number', totals, 'unique rows', len(rows), 'diffs on overlap', len(diffs), 'problems', problems)
for d in diffs: print('  diff', d)
json.dump({'rows': rows, 'src': src, 'total_number': sorted(totals), 'pages': pages, 'problems': problems, 'diffs': diffs},
          open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False)
