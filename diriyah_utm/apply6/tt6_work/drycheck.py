# usage: python3 drycheck.py <ad_id> [...]  -> checks dry-run call input + preview body == payload, lists diffs vs live pre-read
import json, sys, subprocess
W='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/tt6_work/'
P=json.load(open(W+'payloads.json')); pre=json.load(open(W+'pre_all.json'))
for ad in sys.argv[1:]:
    o=subprocess.run(['python3',W+'cmpcall.py',ad,'dry'],capture_output=True,text=True)
    first=o.stdout.splitlines()[0] if o.stdout else o.stderr
    r=json.load(open(W+f'resp_dry_{ad}.json'))
    body=r['data']['data']['request']['body']
    ok=body==P[ad]
    cr=body['creatives'][0]; p=pre[ad]
    d=[k for k,v in cr.items() if k!='tracking_pixel_id' and v!=p.get(k)]
    pix=cr.get('tracking_pixel_id')
    print(ad, '|', first, '| preview_body==payload:', ok, '| warnings:', r['data']['data'].get('warnings'), '| preflightBlocking:', r['data']['data'].get('preflightBlocking'), '| fields differing from live:', d, '| pixel:', pix, 'live', p.get('tracking_pixel_id'))
