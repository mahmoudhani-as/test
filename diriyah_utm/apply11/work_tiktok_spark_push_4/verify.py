# usage: python3 -I verify.py <ad_id>
# Read-only: compare the newest complete read made AFTER the last live update call for <ad> with "new" (byte for byte)
# and list every field that differs from the newest read made BEFORE that live call.
import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply11/work_tiktok_spark_push_4')
from common import *
ad = sys.argv[1]
ch = INPD[ad]['changes'][0]
lives = [x for x in update_calls(ad) if x[2].get('dry_run') is False]
assert lives, 'no live call'
for (i, tid, inp, j, err, txt) in lives:
    d = ((j or {}).get('data') or {}).get('data') or {}
    errj = (j or {}).get('error') or {}
    ut = (((errj.get('details') or {}).get('upstream_details') or {}).get('tiktok') or {})
    cr = ((inp.get('payload') or {}).get('creatives') or [{}])[0]
    shape = 'A(tiktok_item_id)' if 'tiktok_item_id' in cr else ('B(video_id)' if 'video_id' in cr else '?')
    print('LIVE call order', i, 'shape', shape, '| is_error', err, '| code', d.get('code', ut.get('code')), '| msg', d.get('message', ut.get('message')),
          '| request_id', d.get('request_id', ut.get('request_id')))
last = lives[-1][0]
_li = lives[-1][2]
_cr = ((_li.get('payload') or {}).get('creatives') or [{}])[0]
_shape = 'A' if 'tiktok_item_id' in _cr else 'B'
_P = json.load(open(W + 'payload_%s_%s.json' % (ad, _shape), encoding='utf-8'))
_dr = [x for x in update_calls(ad) if x[2].get('dry_run') is not False and x[0] < last]
print('last live input == payload file %s:' % _shape, _li.get('payload') == _P, '| == preceding dry-run input:', bool(_dr) and _dr[-1][2].get('payload') == _li.get('payload'))
reads = ad_reads().get(ad) or []
before = [r for r in reads if r[0] < last]
after = [r for r in reads if r[0] > last]
assert before and after, ('reads', len(before), len(after))
ob, rb, A0 = before[-1]
oa, ra, A1 = after[-1]
cur1, extra1, conflict1 = eff_url(A1.get('landing_page_url'), A1.get('utm_params'))
print('BEFORE read', rb, '| AFTER read', ra)
print('AFTER landing_page_url == new (bytes):', A1.get('landing_page_url') == ch['new'])
print('AFTER eff url equiv new:', equiv(cur1, ch['new']), '| utm extra', extra1, '| conflict', conflict1)
print('AFTER utm_params == UTMs(new) (order-insensitive):',
      sorted((x['key'], x['value']) for x in (A1.get('utm_params') or [])) == sorted((x['key'], x['value']) for x in utm_from(ch['new'])),
      '| has utm_id:', any(x['key'] == 'utm_id' for x in (A1.get('utm_params') or [])))
skip = {'modify_time', 'landing_page_url', 'utm_params', 'secondary_status'}
changed = []
for k in sorted(set(A0) | set(A1)):
    if k in skip:
        continue
    if A0.get(k) != A1.get(k):
        changed.append(k)
        print('   CHANGED', k, '|', repr(A0.get(k))[-90:], '->', repr(A1.get(k))[-90:])
print('other fields changed:', changed)
print('ad_text only trailing-space trimmed:', A0.get('ad_text') != A1.get('ad_text') and A0.get('ad_text').rstrip() == A1.get('ad_text'))
print('status before/after:', A0.get('operation_status'), A0.get('secondary_status'), '->', A1.get('operation_status'), A1.get('secondary_status'))
print('tiktok_item_id before/after:', A0.get('tiktok_item_id'), '->', A1.get('tiktok_item_id'), '| video_id', A0.get('video_id'), '->', A1.get('video_id'))
print('modify_time after:', A1.get('modify_time'))
print('AFTER_URL_JSON:', json.dumps(A1.get('landing_page_url')))
print('BEFORE_CUR_JSON:', json.dumps(eff_url(A0.get('landing_page_url'), A0.get('utm_params'))[0]))
