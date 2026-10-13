# usage: python3 -I check_manual.py <ad_id> dry|live|verify
# Read-only check of a CUSTOMIZED_USER manual ad write:
#   dry   : the exact dry-run call I sent (from my transcript) == expected payload (pre-read creative fields as read,
#           only landing_page_url = new and utm_params = UTMs of new; pixel as exact string) and the preview body == it.
#   live  : the exact live call == the dry-run call; print API code/message/request_id and the response URL.
#   verify: the newest ad/get read of the ad after the live call: URL + utm_params == new byte for byte, other fields unchanged.
import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply8/work_tiktok_1/scripts')
from common import *
from tr import calls, result_json, ad_reads

PIXEL = "7347671240183693330"
FIELDS = ['ad_id', 'ad_name', 'identity_id', 'identity_type', 'ad_format', 'video_id', 'image_ids', 'ad_text', 'call_to_action',
          'landing_page_url', 'utm_params', 'tracking_pixel_id', 'display_name', 'avatar_icon_web_uri', 'aigc_disclosure_type',
          'creative_authorized', 'vast_moat_enabled']

ad, mode = sys.argv[1], sys.argv[2]
u = INPD[ad]
ch = u['changes'][0]
assert ch['slot'] == 'ad.landing_page_url' and len(u['changes']) == 1
assert not excluded(ad, ch['slot']), 'EXCLUDED'
pre_j = load_tool_json(W + 'reads/pre_manual_19.json')
pre = {a['ad_id']: a for a in pre_j['data']['data']['data']['list']}[ad]
pre_rid = pre_j['data']['data']['request_id']
assert pre['identity_type'] == 'CUSTOMIZED_USER' and not pre.get('tiktok_item_id')
assert float(int(PIXEL)) == float(pre['tracking_pixel_id']), (PIXEL, pre['tracking_pixel_id'])
cur = eff_url(pre['landing_page_url'], pre.get('utm_params'))[0]
assert cur == ch['now'] or cur in ch['alt_now'], 'pre-read not now/alt'

cr = {}
for k in FIELDS:
    if k == 'landing_page_url':
        cr[k] = ch['new']
    elif k == 'utm_params':
        cr[k] = utm_from(ch['new'])
    elif k == 'tracking_pixel_id':
        cr[k] = PIXEL
    else:
        cr[k] = pre[k]
expected = {"advertiser_id": u['account_id'], "adgroup_id": pre['adgroup_id'], "creatives": [cr]}
# every non-empty creative field of the read must be either sent or a read-only/report field
ro = {'adgroup_name', 'campaign_name', 'campaign_id', 'adgroup_id', 'advertiser_id', 'secondary_status', 'operation_status',
      'modify_time', 'create_time', 'profile_image_url', 'is_new_structure', 'campaign_automation_type', 'is_aco',
      'deeplink_type', 'viewability_postbid_partner', 'brand_safety_postbid_partner'}
unsent = sorted(k for k, v in pre.items() if v not in (None, '', [], {}) and k not in FIELDS and k not in ro)
print('pre-read rid', pre_rid, '| unsent non-empty fields:', unsent)


def my_call(dry):
    cs = [(t, i, r) for t, i, r in calls('tiktok_ad_update')
          if bool(i.get('dry_run', True)) == dry and ((i.get('payload') or {}).get('creatives') or [{}])[0].get('ad_id') == ad]
    return cs


def diff(a, b, p=''):
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append(p + '.' + k + ' missing in sent')
            elif k not in b:
                out.append(p + '.' + k + ' extra in sent')
            else:
                out += diff(a[k], b[k], p + '.' + k)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            out += diff(x, y, p + '[%d]' % i)
    elif a != b or type(a) != type(b):
        out.append('%s: sent %r expected %r' % (p, a, b))
    return out


if mode == 'dry':
    cs = my_call(True)
    assert cs, 'no dry-run call found'
    tid, inp, txt = cs[-1]
    print('dry calls for this ad:', len(cs))
    d = diff(inp.get('payload'), expected)
    print('sent payload == expected:', not d, d)
    extra_top = sorted(k for k in inp if k not in ('action', 'dry_run', 'payload', 'advertiser_id'))
    print('other top-level args:', extra_top, '| top advertiser_id:', inp.get('advertiser_id'))
    j = result_json(txt)
    body = j['data']['data']['request']['body']
    d2 = diff(body, expected)
    print('preview body == expected:', not d2, d2)
    print('preview method/path:', j['data']['data']['request']['method'], j['data']['data']['request']['path'],
          '| warnings:', j['data']['data'].get('warnings'), '| preflightBlocking:', j['data']['data'].get('preflightBlocking'))
    print('text notes:', text_notes(pre.get('ad_text')))
elif mode == 'live':
    cs = my_call(False)
    assert cs, 'no live call found'
    print('live calls for this ad:', len(cs))
    tid, inp, txt = cs[-1]
    d = diff(inp.get('payload'), expected)
    print('live payload == expected:', not d, d)
    j = result_json(txt)
    if not j:
        print('RAW RESULT:', (txt or '')[:1500])
        sys.exit()
    dd = j.get('data', {}).get('data', {})
    print('success:', j.get('success'), '| code:', dd.get('code'), '| message:', dd.get('message'), '| request_id:', dd.get('request_id'))
    for c in (dd.get('data') or {}).get('creatives') or []:
        print('resp landing_page_url == new:', c.get('landing_page_url') == ch['new'])
        print('resp utm:', [(x['key'], x['value']) for x in c.get('utm_params') or []])
        print('resp need_audit:', (dd.get('data') or {}).get('need_audit'))
elif mode == 'verify':
    rr = ad_reads().get(ad) or []
    live_ids = [t for t, i, r in my_call(False)]
    # newest read that came after the newest live call
    ev_ids = [t for t, i, r in calls('tiktok_ad_get')]
    assert rr, 'no reads'
    rid, post = rr[-1]
    print('post-read rid', rid, '(reads of this ad in transcript: %d)' % len(rr))
    lc = my_call(False)
    if lc:
        lj = result_json(lc[-1][2]) or {}
        lrid = ((lj.get('data') or {}).get('data') or {}).get('request_id') or ''
        print('post-read is after the live write (request-id time):', rid[:14] > lrid[:14], '| live rid', lrid)
    eff, extra, conflict = eff_url(post.get('landing_page_url'), post.get('utm_params'))
    print('AFTER_LIVE_URL_FIELD:', post.get('landing_page_url'))
    print('url field == new (bytes):', post.get('landing_page_url') == ch['new'])
    print('effective == new (bytes):', eff == ch['new'], '| extra:', extra, '| conflict:', conflict)
    print('utm_params == UTMs of new (as set):', sorted((x['key'], x['value']) for x in post.get('utm_params') or []) == sorted((x['key'], x['value']) for x in utm_from(ch['new'])))
    print('utm_id present:', any(x['key'] == 'utm_id' for x in post.get('utm_params') or []) or 'utm_id=' in (post.get('landing_page_url') or ''))
    other = {k: (pre.get(k), post.get(k)) for k in sorted(set(pre) | set(post))
             if k not in ('landing_page_url', 'utm_params', 'modify_time') and pre.get(k) != post.get(k)}
    print('other fields changed:', other)
    print('modify_time:', pre.get('modify_time'), '->', post.get('modify_time'), '| status:', post.get('operation_status'), post.get('secondary_status'))
