# usage: python3 -I check.py <ad_id> dry|post [item|video]
# Read-only. dry: the newest dry-run body for <ad> == built payload (byte-exact) and its diff vs the pre-read.
# post: the newest complete read after the last live update: URL == new byte for byte, utm_params == UTMs of new, all other field diffs.
import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply11/work_tiktok_spark_push_3')
from common import *
from build import build, pixel_exact

ad, mode = sys.argv[1], sys.argv[2]
shape = sys.argv[3] if len(sys.argv) > 3 else 'item'
b = build(ad, shape)
a, ch, payload = b['a'], b['ch'], b['payload']
ups = updates(ad)
if mode == 'dry':
    dr = [x for x in ups if x[1].get('dry_run') is True]
    assert dr, 'no dry run'
    i, inp, j, txt = dr[-1]
    sent = inp.get('payload')
    print('dry-run input payload == built payload:', sent == payload)
    body = (((j or {}).get('data') or {}).get('data') or {}).get('request', {}).get('body')
    print('preview body == built payload:', body == payload, '| warnings:', (((j or {}).get('data') or {}).get('data') or {}).get('warnings'),
          '| preflightBlocking:', (((j or {}).get('data') or {}).get('data') or {}).get('preflightBlocking'))
    cr = (body or {}).get('creatives', [{}])[0]
    for k in sorted(set(cr) | set(a)):
        if k in cr:
            rv = a.get(k)
            if k == 'tracking_pixel_id' and rv is not None:
                rv = pixel_exact(rv)
            if cr[k] != rv:
                print('  DIFF sent vs read:', k, '| read:', json.dumps(a.get(k), ensure_ascii=False)[:300], '| sent:', json.dumps(cr[k], ensure_ascii=False)[:300])
elif mode == 'post':
    live = [x for x in ups if x[1].get('dry_run') is False]
    assert live, 'no live update'
    last = max(x[0] for x in live)
    for i, inp, j, txt in live:
        d = ((j or {}).get('data') or {}).get('data') or {}
        print('live update order', i, '| code', d.get('code'), '| msg', str(d.get('message'))[:300], '| request_id', d.get('request_id'),
              '| shape', 'item' if 'tiktok_item_id' in inp['payload']['creatives'][0] else 'video' if 'video_id' in inp['payload']['creatives'][0] else '?')
        if not j:
            print('   raw result:', (txt or '')[:800])
    rr = [r for r in (ad_reads().get(ad) or []) if r[0] > last]
    if not rr:
        print('NO READ AFTER LAST LIVE UPDATE')
        sys.exit(0)
    order, rid, p = rr[-1]
    url = p.get('landing_page_url')
    print('read-back rid', rid, '| modify_time', p.get('modify_time'))
    print('AFTER_URL:', url)
    print('url == new (byte):', url == ch['new'], '| ~ new:', equiv(url, ch['new']))
    print('utm_params == UTMs of new:', p.get('utm_params') == utm_from(ch['new']),
          '| same set:', sorted((x['key'], x['value']) for x in (p.get('utm_params') or [])) == sorted((x['key'], x['value']) for x in utm_from(ch['new'])))
    eff, extra, conflict = eff_url(url, p.get('utm_params'))
    print('eff url == new:', eff == ch['new'], '| utm extra:', extra, '| conflict:', conflict)
    print('item before/after:', a.get('tiktok_item_id'), '->', p.get('tiktok_item_id'), '| video before/after:', a.get('video_id'), '->', p.get('video_id'))
    print('identity after:', p.get('identity_type'), p.get('identity_id'), p.get('identity_authorized_bc_id'), '| op/sec after:', p.get('operation_status'), p.get('secondary_status'))
    skip = {'landing_page_url', 'utm_params', 'modify_time'}
    for k in sorted(set(a) | set(p)):
        if k in skip:
            continue
        if a.get(k) != p.get(k):
            print('  OTHER DIFF:', k, '| before:', json.dumps(a.get(k), ensure_ascii=False)[:200], '| after:', json.dumps(p.get(k), ensure_ascii=False)[:200])
    print('ad_text same:', a.get('ad_text') == p.get('ad_text'), '| status same:', a.get('operation_status') == p.get('operation_status'))
