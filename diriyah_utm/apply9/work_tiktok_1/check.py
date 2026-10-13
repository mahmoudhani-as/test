# usage: python3 -I check.py <ad_id> dry|live|verify
# Read-only check of one ad/update write, from my own transcript:
#   dry   : my newest dry-run call for the ad == expected payload (built from the PRE-read: creative fields as read,
#           only landing_page_url = new and utm_params = UTMs of new) and the preview body == it.
#   live  : my live call(s) for the ad == the dry-run payload; API code/message/request_id.
#   verify: newest ad/get read of the ad: URL (+ utm_params) == new byte for byte, other fields unchanged vs the pre-read.
import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply9/work_tiktok_1')
from h import *

ad, mode = sys.argv[1], sys.argv[2]
u = INPD[ad]
ch = u['changes'][0]
assert len(u['changes']) == 1 and ch['slot'] == 'ad.landing_page_url'
assert not excluded(ad, ch['slot']), 'EXCLUDED'
R = ad_reads()
rr = R[ad]
# pre-read = the newest read made BEFORE my first live call for this ad (or the newest read if no live call yet)


def my_calls(dry):
    return [(t, i, r) for t, i, r in calls('tiktok_ad_update')
            if bool(i.get('dry_run', True)) == dry and ((i.get('payload') or {}).get('creatives') or [{}])[0].get('ad_id') == ad]


ev_order = [i for k, i, n, x in events() if k == 'use']
live = my_calls(False)
first_live_pos = ev_order.index(live[0][0]) if live else 10 ** 9
reads_with_pos = []
for t, inp, txt in calls('tiktok_ad_get'):
    j = rj(txt)
    if not j or not j.get('success') or j['data']['data'].get('code') != 0:
        continue
    for a in j['data']['data']['data']['list']:
        if a['ad_id'] == ad:
            reads_with_pos.append((ev_order.index(t), j['data']['data']['request_id'], a))
pre_l = [x for x in reads_with_pos if x[0] < first_live_pos]
pre_pos, pre_rid, pre = pre_l[-1]
cur = eff_url(pre.get('landing_page_url'), pre.get('utm_params'))[0]
assert cur == ch['now'] or cur in ch['alt_now'], 'pre-read not now/alt'
expected = expected_payload(u, pre)
print('pre-read rid', pre_rid, '| class', classify(pre), '| pre cur == now:', cur == ch['now'])

if mode == 'dry':
    cs = my_calls(True)
    assert cs, 'no dry-run call'
    tid, inp, txt = cs[-1]
    print('dry calls for this ad:', len(cs))
    d = diff(inp.get('payload'), expected)
    print('sent payload == expected:', not d, d)
    print('other top-level args:', sorted(k for k in inp if k not in ('action', 'dry_run', 'payload')))
    j = rj(txt)
    body = j['data']['data']['request']['body']
    d2 = diff(body, expected)
    print('preview body vs expected:', 'EQUAL' if not d2 else d2)
    print('preview method/path:', j['data']['data']['request']['method'], j['data']['data']['request']['path'],
          '| warnings:', j['data']['data'].get('warnings'), '| preflightBlocking:', j['data']['data'].get('preflightBlocking'))
elif mode == 'live':
    print('live calls for this ad:', len(live))
    dry = my_calls(True)
    for tid, inp, txt in live:
        d = diff(inp.get('payload'), dry[-1][1].get('payload'))
        print('live payload == dry-run payload:', not d, d)
        j = rj(txt)
        if not j:
            print('RAW RESULT:', (txt or '')[:1500])
            continue
        dd = (j.get('data') or {}).get('data') or {}
        print('success:', j.get('success'), '| code:', dd.get('code'), '| message:', dd.get('message'), '| request_id:',
              dd.get('request_id'), '| error:', json.dumps(j.get('error'))[:800] if j.get('error') else None)
        for c in (dd.get('data') or {}).get('creatives') or []:
            print('resp landing_page_url == new:', c.get('landing_page_url') == ch['new'], '| resp utm:',
                  [(x['key'], x['value']) for x in c.get('utm_params') or []], '| resp item:', c.get('tiktok_item_id'))
        print('need_audit:', (dd.get('data') or {}).get('need_audit'), '| gateway meta:', json.dumps((j.get('data') or {}).get('meta'))[:300])
elif mode == 'verify':
    post_l = [x for x in reads_with_pos if x[0] > first_live_pos]
    assert post_l, 'no read after the live call'
    pos, rid, post = post_l[-1]
    print('post-read rid', rid)
    eff, extra, conflict = eff_url(post.get('landing_page_url'), post.get('utm_params'))
    print('AFTER_LIVE_URL_FIELD:', post.get('landing_page_url'))
    print('url field == new (bytes):', post.get('landing_page_url') == ch['new'])
    print('effective == new (bytes):', eff == ch['new'], '| extra:', extra, '| conflict:', conflict)
    if pre.get('utm_params'):
        print('utm_params == UTMs of new (in order):', [(x['key'], x['value']) for x in post.get('utm_params') or []] ==
              [(x['key'], x['value']) for x in utm_from(ch['new'])])
    print('utm_id present:', any(x['key'] == 'utm_id' for x in post.get('utm_params') or []) or 'utm_id=' in (post.get('landing_page_url') or ''))
    other = {k: (pre.get(k), post.get(k)) for k in sorted(set(pre) | set(post))
             if k not in ('landing_page_url', 'utm_params', 'modify_time') and pre.get(k) != post.get(k)}
    print('other fields changed:', other)
    print('tiktok_item_id:', pre.get('tiktok_item_id'), '->', post.get('tiktok_item_id'), '| identity:', post.get('identity_type'),
          post.get('identity_id'))
    print('modify_time:', pre.get('modify_time'), '->', post.get('modify_time'), '| status:', post.get('operation_status'),
          post.get('secondary_status'))
