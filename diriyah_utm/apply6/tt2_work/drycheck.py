# usage: python3 -I drycheck.py <ad_id> <dry_response_file>
import json, sys
ad, f = sys.argv[1], sys.argv[2]
p = json.load(open('payloads.json'))[ad]
r = json.load(open(f))
body = r['data']['data']['request']['body']
assert r['data']['dryRun'] is True
print('body == payload:', body == p)
raw = json.load(open('pre3_raw.json'))['data']['data']['data']['list']
a = [x for x in raw if x['ad_id'] == ad][0]
cr = body['creatives'][0]
diff = []
for k, v in cr.items():
    if k in ('landing_page_url', 'utm_params'):
        continue
    rv = a.get(k)
    if k == 'tracking_pixel_id':
        ok = int(float(rv)) == int(float(7347671240183693000)) and v == '7347671240183693330'
    else:
        ok = (rv == v)
    if not ok:
        diff.append((k, rv, v))
print('fields differing from read (excluding URL/utm_params):', diff)
print('sent landing_page_url == new:', cr['landing_page_url'] == json.load(open('../in_tiktok_2.json')) and False or cr['landing_page_url'] == [u for u in json.load(open('../in_tiktok_2.json')) if u['unit'] == ad][0]['changes'][0]['new'])
print('utm_params:', [(x['key'], x['value']) for x in cr['utm_params']])
print('read fields NOT sent:', sorted(k for k in a if k not in cr and a[k] not in (None, '', [], {}) ))
