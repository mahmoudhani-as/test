# usage: python3 -I refresh.py <collected.json> <snapshot.json>
# Merges the later targeted re-reads (ad/get with filtering.ad_ids; smart_plus/ad/get with filtering.smart_plus_ad_ids)
# into the snapshot (later read wins) and reports any URL / utm / status differences against the sweep values.
import json, sys
C = json.load(open(sys.argv[1]))
snap = json.load(open(sys.argv[2]))
man, sp = snap['manual'], snap['smart_plus']
changes, n_m, n_s, rids = [], 0, 0, []
ref_m, ref_s = [], []
for r in C:
    inp = r['input'] or {}
    p = inp.get('params') or {}
    f = p.get('filtering') or {}
    act = inp.get('action')
    res = r['result']
    if act not in ('tiktok_ad_get', 'tiktok_smart_plus_ad_get') or not isinstance(res, dict) or not res.get('success'):
        continue
    inner = res['data']['data']
    if inner.get('code') != 0:
        continue
    lst = (inner.get('data') or {}).get('list') or []
    if any(not isinstance(x, dict) for x in lst):
        continue
    if act == 'tiktok_ad_get' and f.get('ad_ids'):
        rids.append(inner.get('request_id'))
        for x in lst:
            old = man.get(x['ad_id'])
            if old is None:
                changes.append(('manual NEW in refresh', x['ad_id']))
            else:
                for k in ('landing_page_url', 'utm_params', 'secondary_status', 'operation_status'):
                    if old.get(k) != x.get(k):
                        changes.append(('manual', x['ad_id'], k, old.get(k), x.get(k)))
            man[x['ad_id']] = x
            ref_m.append(x['ad_id'])
            n_m += 1
    if act == 'tiktok_smart_plus_ad_get' and f.get('smart_plus_ad_ids'):
        rids.append(inner.get('request_id'))
        for x in lst:
            old = sp.get(x['smart_plus_ad_id'])
            if old is None:
                changes.append(('smart NEW in refresh', x['smart_plus_ad_id']))
            else:
                for k in ('landing_page_url_list', 'ad_configuration', 'secondary_status', 'operation_status'):
                    if old.get(k) != x.get(k):
                        changes.append(('smart', x['smart_plus_ad_id'], k, old.get(k), x.get(k)))
            sp[x['smart_plus_ad_id']] = x
            ref_s.append(x['smart_plus_ad_id'])
            n_s += 1
snap['refresh_request_ids'] = rids
snap['refreshed_manual_ids'] = sorted(set(ref_m))
snap['refreshed_smart_ids'] = sorted(set(ref_s))
snap['refresh_differences'] = [list(c) for c in changes]
json.dump(snap, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print('refreshed manual', n_m, 'smart', n_s, 'requests', rids)
print('differences vs sweep:', len(changes))
for c in changes:
    print(c)
