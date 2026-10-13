# usage: python3 -I check_dry.py <ad_id> <A|B>
# Read-only: compare the newest dry-run tiktok_ad_update call for <ad> (input + preview body) with payload_<ad>_<shape>.json.
import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply11/work_tiktok_spark_push_4')
from common import *
ad, shape = sys.argv[1], sys.argv[2]
P = json.load(open(W + 'payload_%s_%s.json' % (ad, shape), encoding='utf-8'))
ups = [x for x in update_calls(ad) if x[2].get('dry_run') is not False]
assert ups, 'no dry-run call'
i, tid, inp, j, err, txt = ups[-1]
print('dry-run call order', i, 'dry_run=', inp.get('dry_run'), 'is_error', err)
print('input payload == file payload:', inp.get('payload') == P)
if inp.get('payload') != P:
    a, b = inp.get('payload'), P
    for k in set(a['creatives'][0]) | set(b['creatives'][0]):
        if a['creatives'][0].get(k) != b['creatives'][0].get(k):
            print('   DIFF input vs file', k, repr(a['creatives'][0].get(k))[:200], '|', repr(b['creatives'][0].get(k))[:200])
body = (((j or {}).get('data') or {}).get('data') or {}).get('request', {}).get('body')
assert body, 'no preview body'
pc, bc = P['creatives'][0], body['creatives'][0]
print('top-level same:', {k: body.get(k) == P.get(k) for k in ('advertiser_id', 'adgroup_id')}, '| extra top keys:', sorted(set(body) - set(P)))
diff = []
for k in sorted(set(pc) | set(bc)):
    if pc.get(k) != bc.get(k):
        diff.append(k)
        print('   PREVIEW DIFF', k, '| sent:', repr(pc.get(k))[-80:], '| preview:', repr(bc.get(k))[-80:])
only_trim = diff == ['ad_text'] and pc['ad_text'].rstrip() == bc['ad_text'] or not diff
print('preview == payload except ad_text trailing-space trim:', only_trim, '| diffs:', diff)
print('preview landing_page_url == new:', bc.get('landing_page_url') == INPD[ad]['changes'][0]['new'])
print('preview utm_params:', bc.get('utm_params') == utm_from(INPD[ad]['changes'][0]['new']))
print('preview tiktok_item_id:', bc.get('tiktok_item_id'), '| video_id:', bc.get('video_id'))
