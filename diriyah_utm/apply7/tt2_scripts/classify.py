# usage: python3 -I classify.py <in_json> <raw_read_txt> <excl_json>
import json, sys
from urllib.parse import urlsplit, parse_qsl

def norm(u):
    s = urlsplit(u)
    return (s.scheme, s.netloc, s.path, s.fragment, tuple(sorted(parse_qsl(s.query, keep_blank_values=True))))

def full_url(ad):
    """landing_page_url with separately stored utm_params merged in (keys not already in the URL)."""
    u = ad.get('landing_page_url') or ''
    up = ad.get('utm_params') or []
    s = urlsplit(u)
    q = parse_qsl(s.query, keep_blank_values=True)
    keys = {k for k, _ in q}
    extra = [(p['key'], p['value']) for p in up if p.get('key') not in keys]
    return u, extra, up

inp = json.load(open(sys.argv[1]))
raw = json.load(open(sys.argv[2]))
ex = json.load(open(sys.argv[3]))
exset = {(e['platform'], e['ad_id'], e['slot']) for e in ex}
ads = {a['ad_id']: a for a in raw['data']['data']['data']['list']}
print('req', raw['data']['data']['request_id'], 'n ads read', len(ads))
for u in inp:
    a = ads.get(u['unit'])
    for c in u['changes']:
        if a is None:
            print(u['unit'], 'NOT FOUND'); continue
        lp, extra, up = full_url(a)
        cur_norm = norm(lp)
        if extra:
            cur_norm = cur_norm[:4] + (tuple(sorted(list(cur_norm[4]) + extra)),)
        upd = {p['key']: p['value'] for p in up}
        newq = dict(parse_qsl(urlsplit(c['new']).query, keep_blank_values=True))
        utm_match_new = all(newq.get(k) == v for k, v in upd.items()) and all(upd.get(k) == v for k, v in newq.items() if k.startswith('utm_')) if up else None
        if cur_norm == norm(c['new']):
            cls = 'AlreadyFixed'
        elif lp == c['now'] or lp in c['alt_now'] or cur_norm == norm(c['now']) or any(cur_norm == norm(x) for x in c['alt_now']):
            cls = 'WRITE'
        else:
            cls = 'Skipped'
        print(u['unit'], cls, 'excluded' if ('tiktok', u['unit'], c['slot']) in exset else '',
              '| idtype', a.get('identity_type'), '| item', a.get('tiktok_item_id'), '| fmt', a.get('ad_format'),
              '| sec', a.get('secondary_status'), '| op', a.get('operation_status'), '| mod', a.get('modify_time'),
              '| lp==new bytes', lp == c['new'], '| extra', extra, '| utm_params match new', utm_match_new,
              '| pixel', a.get('tracking_pixel_id'), '| cta_id', a.get('call_to_action_id'))
