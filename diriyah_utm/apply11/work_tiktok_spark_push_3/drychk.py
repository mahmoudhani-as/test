# usage: python3 -I drychk.py <ad_id> item|video   (read-only)
import sys
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply11/work_tiktok_spark_push_3')
from common import *
from build import build, pixel_exact
ad, shape = sys.argv[1], sys.argv[2]
b = build(ad, shape)
dr = [x for x in updates(ad) if x[1].get('dry_run') is True]
i, inp, j, txt = dr[-1]
shape_sent = 'item' if 'tiktok_item_id' in inp['payload']['creatives'][0] else 'video'
print('last dry-run shape:', shape_sent, '| input == built:', inp['payload'] == b['payload'])
body = j['data']['data']['request']['body']
p = dict(b['payload']); pc = dict(p['creatives'][0])
trim = pc.get('ad_text') is not None and pc['ad_text'] != pc['ad_text'].rstrip()
pc['ad_text'] = pc['ad_text'].rstrip() if pc.get('ad_text') is not None else None
print('preview body == built (ad_text rstripped):', body == {**p, 'creatives': [pc]}, '| ad_text trailing ws trimmed:', trim,
      '| warnings:', j['data']['data'].get('warnings'), '| preflightBlocking:', j['data']['data'].get('preflightBlocking'))
cr = body['creatives'][0]; a = b['a']
diff = []
for k in cr:
    rv = a.get(k)
    if k == 'tracking_pixel_id' and rv is not None:
        rv = pixel_exact(rv)
    if cr[k] != rv:
        diff.append(k)
print('fields differing from read:', diff, '| read fields not sent (non-RO, non-default):', b['unsent'])
