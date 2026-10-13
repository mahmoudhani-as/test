# usage: python3 -I check.py <ad_id> dry|live|verify [item|video]
# Read-only checks of THIS agent's own ad/update calls for <ad_id> (from the transcript, byte-exact):
#   dry   : newest dry-run call input == built payload; preview body == it (or the accepted ad_text trailing-space trim)
#   live  : newest live call input == built payload; API code / message / request id / response URL
#   verify: newest complete ad/get read after the newest live call: URL + utm_params == new byte for byte; other fields unchanged
import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply11/work_tiktok_spark_push_1')
from common import *
from build import build, is_update_for

ad, mode = sys.argv[1], sys.argv[2]
shape = sys.argv[3] if len(sys.argv) > 3 else 'item'
b = build(ad, shape)
expected, ch, pre = b['payload'], b['ch'], b['a']


def mine(dry):
    return [(i, tid, inp, txt, err) for i, tid, inp, txt, err in calls('tiktok_ad_update')
            if is_update_for(inp, ad) and (inp.get('dry_run', True) is not False) == dry]


if mode == 'dry':
    cs = mine(True)
    assert cs, 'no dry-run call'
    i, tid, inp, txt, err = cs[-1]
    d = diff(inp.get('payload'), expected)
    print('dry calls for this ad:', len(cs), '| sent payload == expected:', not d, d)
    print('other top-level args:', {k: v for k, v in inp.items() if k not in ('payload',)})
    j = result_json(txt)
    if not j:
        print('RAW:', (txt or '')[:1500]); sys.exit()
    dd = j['data']['data']
    if 'request' not in dd:
        print('NO PREVIEW:', json.dumps(j, ensure_ascii=False)[:2000]); sys.exit()
    body = dd['request']['body']
    d2 = diff(body, expected)
    print('preview', dd['request']['method'], dd['request']['path'], '| warnings:', dd.get('warnings'), '| preflightBlocking:', dd.get('preflightBlocking'))
    print('preview body == expected:', not d2, d2)
    if d2:
        sa, sb = expected['creatives'][0].get('ad_text'), body['creatives'][0].get('ad_text')
        print('ad_text: sent %r | preview %r | preview == sent.rstrip(): %s' % ((sa or '')[-8:], (sb or '')[-8:], sb == (sa or '').rstrip()))
    print('preview other keys:', sorted(k for k in dd if k not in ('request',)))
elif mode == 'live':
    cs = mine(False)
    assert cs, 'no live call'
    print('live calls for this ad (all shapes):', len(cs))
    i, tid, inp, txt, err = cs[-1]
    d = diff(inp.get('payload'), expected)
    print('newest live call: sent payload == expected(%s): %s %s | is_error: %s' % (shape, not d, d, err))
    print('other top-level args:', {k: v for k, v in inp.items() if k not in ('payload',)})
    j = result_json(txt)
    if not j:
        print('RAW:', (txt or '')[:3000]); sys.exit()
    dd = (j.get('data') or {}).get('data') or {}
    print('success:', j.get('success'), '| code:', dd.get('code'), '| message:', dd.get('message'), '| request_id:', dd.get('request_id'),
          '| gateway req:', (j.get('meta') or {}).get('requestId'))
    if not j.get('success') or dd.get('code') not in (0, None):
        print('ERROR:', json.dumps(j, ensure_ascii=False)[:3000])
    for c in ((dd.get('data') or {}).get('creatives') or []):
        print('resp ad_id:', c.get('ad_id'), '| resp landing_page_url == new:', c.get('landing_page_url') == ch['new'],
              '| resp item:', c.get('tiktok_item_id'), '| resp video:', c.get('video_id'))
        print('resp utm:', [(x['key'], x['value']) for x in c.get('utm_params') or []])
    print('resp keys:', sorted((dd.get('data') or {}).keys()) if isinstance(dd.get('data'), dict) else dd.get('data'),
          '| need_audit:', (dd.get('data') or {}).get('need_audit') if isinstance(dd.get('data'), dict) else None)
elif mode == 'verify':
    lc = mine(False)
    assert lc, 'no live call'
    last_live = lc[-1][0]
    rr = [r for r in (ad_reads().get(ad) or []) if r[0] > last_live]
    assert rr, 'no complete read after the live call'
    order, rid, post = rr[-1]
    lj = result_json(lc[-1][3]) or {}
    lrid = ((lj.get('data') or {}).get('data') or {}).get('request_id') or ''
    print('post-read rid', rid, '| after live write rid', lrid, ':', rid[:14] >= lrid[:14] if lrid else 'n/a')
    eff, extra, conflict = eff_url(post.get('landing_page_url'), post.get('utm_params'))
    print('AFTER_LIVE:', eff)
    print('url field == new (bytes):', post.get('landing_page_url') == ch['new'], '| effective == new (bytes):', eff == ch['new'],
          '| extra:', extra, '| conflict:', conflict)
    print('utm_params == UTMs of new (as set):', sorted((x['key'], x['value']) for x in post.get('utm_params') or []) ==
          sorted((x['key'], x['value']) for x in utm_from(ch['new'])), '| utm_params:', [(x['key'], x['value']) for x in post.get('utm_params') or []])
    print('utm_id present:', any(x['key'] == 'utm_id' for x in post.get('utm_params') or []) or 'utm_id=' in (post.get('landing_page_url') or ''))
    other = {k: (pre.get(k), post.get(k)) for k in sorted(set(pre) | set(post))
             if k not in ('landing_page_url', 'utm_params', 'modify_time') and pre.get(k) != post.get(k)}
    print('other fields changed:', json.dumps(other, ensure_ascii=True))
    print('modify_time:', pre.get('modify_time'), '->', post.get('modify_time'), '| status:', post.get('operation_status'), post.get('secondary_status'),
          '| identity:', post.get('identity_type'), '| item before:', pre.get('tiktok_item_id'), '| item after:', post.get('tiktok_item_id'),
          '| same item:', pre.get('tiktok_item_id') == post.get('tiktok_item_id'), '| video after:', post.get('video_id'))
