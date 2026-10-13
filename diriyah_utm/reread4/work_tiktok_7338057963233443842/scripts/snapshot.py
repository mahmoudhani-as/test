# usage: python3 -I snapshot.py <collected.json> <snapshot_out.json>
# Builds the current-state snapshot from this agent's read-only calls (reread4, 13-Oct-2026):
#  - manual ads: ad/get filtering {primary_status STATUS_ALL, campaign_automation_type MANUAL}, page_size 40, all pages
#  - Upgraded Smart+ ads: smart_plus/ad/get filtering {primary_status STATUS_ALL}, page_size 40, all pages
#  - refresh reads (filtering with modified_after / ad_ids / smart_plus_ad_ids) that requested the URL fields are applied
#    afterwards in call order (later read wins); minimal-field census reads are only used for change detection.
# Pages with truncation markers are rejected. Reports completeness against page_info.total_number.
import json, sys
C = json.load(open(sys.argv[1], encoding='utf-8'))
MAN_F = {"primary_status": "STATUS_ALL", "campaign_automation_type": "MANUAL"}
SP_F = {"primary_status": "STATUS_ALL"}
man_pages, sp_pages, refresh, problems, totals = {}, {}, [], [], {}
for r in C:
    inp = r['input'] or {}
    act = inp.get('action')
    if act not in ('tiktok_ad_get', 'tiktok_smart_plus_ad_get'):
        continue
    p = inp.get('params') or {}
    res = r['result']
    if not isinstance(res, dict) or not res.get('success'):
        problems.append(('not success', r['seq'], act, r.get('error')))
        continue
    inner = res['data']['data']
    if inner.get('code') != 0:
        problems.append(('api code', r['seq'], inner.get('code'), inner.get('message')))
        continue
    dd = inner.get('data') or {}
    lst = dd.get('list') or []
    if any(not isinstance(x, dict) for x in lst):
        problems.append(('truncated page ignored', r['seq'], act, p.get('page'), p.get('page_size')))
        continue
    f = p.get('filtering') or {}
    flds = set(p.get('fields') or [])
    rid = inner.get('request_id')
    if act == 'tiktok_ad_get' and f == MAN_F and p.get('page_size') == 40:
        man_pages[p['page']] = (lst, dd['page_info'], rid, r['seq'])
        totals.setdefault('manual', set()).add(dd['page_info']['total_number'])
    elif act == 'tiktok_smart_plus_ad_get' and f == SP_F and p.get('page_size') == 40:
        sp_pages[p['page']] = (lst, dd['page_info'], rid, r['seq'])
        totals.setdefault('smart_plus', set()).add(dd['page_info']['total_number'])
    elif f.get('modified_after') or f.get('ad_ids') or f.get('smart_plus_ad_ids'):
        if act == 'tiktok_ad_get' and f.get('campaign_automation_type') not in (None, 'MANUAL'):
            continue
        full = ('landing_page_url' in flds) if act == 'tiktok_ad_get' else ('landing_page_url_list' in flds)
        if not full:
            continue  # census-only read (ad_id / modify_time), not an URL refresh
        refresh.append((r['seq'], act, f, lst, rid))
man, sp, man_seen = {}, {}, {}
for k in sorted(man_pages):
    for x in man_pages[k][0]:
        if x['ad_id'] in man:
            problems.append(('duplicate manual ad across pages', x['ad_id'], k))
        man[x['ad_id']] = x
        man_seen[x['ad_id']] = {'page': k, 'request_id': man_pages[k][2]}
sp_seen = {}
for k in sorted(sp_pages):
    for x in sp_pages[k][0]:
        if x['smart_plus_ad_id'] in sp:
            problems.append(('duplicate smart+ ad across pages', x['smart_plus_ad_id'], k))
        sp[x['smart_plus_ad_id']] = x
        sp_seen[x['smart_plus_ad_id']] = {'page': k, 'request_id': sp_pages[k][2]}
mt = sorted(totals.get('manual', []))
st = sorted(totals.get('smart_plus', []))
need_m = (mt[0] + 39) // 40 if mt else None
need_s = (st[0] + 39) // 40 if st else None
print('manual pages', sorted(man_pages), 'need', need_m, 'ads', len(man), 'total_number', mt)
print('smart+ pages', sorted(sp_pages), 'need', need_s, 'ads', len(sp), 'total_number', st)
if len(mt) > 1: problems.append(('manual total_number changed between pages', mt))
if len(st) > 1: problems.append(('smart+ total_number changed between pages', st))
if need_m and sorted(man_pages) != list(range(1, need_m + 1)):
    problems.append(('missing manual pages', sorted(set(range(1, need_m + 1)) - set(man_pages))))
if need_s and sorted(sp_pages) != list(range(1, need_s + 1)):
    problems.append(('missing smart+ pages', sorted(set(range(1, need_s + 1)) - set(sp_pages))))
if mt and len(man) != mt[0]:
    problems.append(('manual count mismatch', len(man), mt))
if st and len(sp) != st[0]:
    problems.append(('smart+ count mismatch', len(sp), st))
diffs, refreshed_m, refreshed_s = [], {}, {}
for seq, act, f, lst, rid in sorted(refresh, key=lambda t: t[0]):
    for x in lst:
        if act == 'tiktok_ad_get':
            old = man.get(x['ad_id'])
            if old is None:
                diffs.append(['manual ad first seen in refresh', x['ad_id']])
                old = {}
            for k in ('landing_page_url', 'utm_params', 'secondary_status', 'operation_status', 'modify_time'):
                if old.get(k) != x.get(k):
                    diffs.append(['manual', x['ad_id'], k, old.get(k), x.get(k)])
            merged = dict(old)
            for k in ('landing_page_url', 'landing_page_urls', 'utm_params', 'deeplink', 'page_id'):
                merged.pop(k, None)  # compact drops empty values, so clear URL fields before overlaying
            merged.update(x)
            man[x['ad_id']] = merged
            refreshed_m[x['ad_id']] = {'seq': seq, 'request_id': rid}
        else:
            sid = x['smart_plus_ad_id']
            old = sp.get(sid)
            if old is None:
                diffs.append(['smart+ ad first seen in refresh', sid])
                old = {}
            for k in ('landing_page_url_list', 'ad_configuration', 'secondary_status', 'operation_status', 'modify_time'):
                if old.get(k) != x.get(k):
                    diffs.append(['smart', sid, k, old.get(k), x.get(k)])
            merged = dict(old)
            for k in ('landing_page_url_list', 'ad_configuration'):
                merged.pop(k, None)
            merged.update(x)
            sp[sid] = merged
            refreshed_s[sid] = {'seq': seq, 'request_id': rid}
snap = {'manual': man, 'smart_plus': sp, 'manual_seen': man_seen, 'smart_plus_seen': sp_seen,
        'manual_request_ids': {k: v[2] for k, v in man_pages.items()},
        'smart_plus_request_ids': {k: v[2] for k, v in sp_pages.items()},
        'manual_total_number': mt, 'smart_plus_total_number': st,
        'refreshed_manual': refreshed_m, 'refreshed_smart': refreshed_s,
        'refresh_differences': diffs, 'problems': problems}
json.dump(snap, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False)
print('refresh reads', len(refresh), 'refreshed manual', len(refreshed_m), 'smart', len(refreshed_s), 'differences', len(diffs))
for d in diffs[:60]:
    print('  diff', d)
print('problems', problems)
