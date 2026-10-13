# usage: python3 -I check_sp.py <smart_plus_ad_id> pre|dry|live|verify
# Read-only checks for an Upgraded Smart+ ad URL write, from my own transcript (exact calls / results).
#   pre   : newest smart_plus/ad/get read before any update call: classify (AlreadyFixed / Write / Skipped), material identities
#   dry   : the dry-run call == expected payload (landing_page_url_list as read with only [i] = new; ad_configuration as read,
#           utm_params set from new only if present); no creative_list sent; preview body == it
#   live  : live call == dry call; API code / message / request id
#   verify: newest read after the live write: URL == new byte for byte; ad_configuration, creative_list, texts, name, status unchanged
import sys, json, re, copy
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply8/work_tiktok_1/scripts')
from common import *
from tr import calls, result_json, sp_reads

ad, mode = sys.argv[1], sys.argv[2]
u = INPD[ad]
assert len(u['changes']) == 1
ch = u['changes'][0]
m = re.fullmatch(r'smart_plus_ad\.landing_page_url_list\[(\d+)\]\.landing_page_url', ch['slot'])
assert m, ch['slot']
i = int(m.group(1))
assert not excluded(ad, ch['slot']), 'EXCLUDED'

ups = calls('tiktok_smart_plus_ad_update')
mine = [(t, inp, r) for t, inp, r in ups if (inp.get('payload') or {}).get('smart_plus_ad_id') == ad]
rr = sp_reads().get(ad) or []
assert rr, 'no read'


def rid_of(txt):
    j = result_json(txt) or {}
    return ((j.get('data') or {}).get('data') or {}).get('request_id') or ''


first_update_rid = None
# pre-read = newest read whose request id time is before the first update call result (dry runs have no TikTok rid,
# so use transcript order: reads listed before the first update tool_use)
from common import tool_events
order = [tid for kind, tid, name, inp in tool_events() if kind == 'use']
first_up_pos = min([order.index(t) for t, _, _ in mine], default=len(order))
pre = None
for tid, inp, txt in calls('tiktok_smart_plus_ad_get'):
    if order.index(tid) < first_up_pos:
        j = result_json(txt)
        if j and j.get('success') and j['data']['data'].get('code') == 0:
            for a in j['data']['data']['data']['list']:
                if a['smart_plus_ad_id'] == ad:
                    pre = (j['data']['data']['request_id'], a)
assert pre, 'no pre-read before the first update'
pre_rid, a = pre
lpl = a.get('landing_page_url_list') or []
ac = a.get('ad_configuration') or {}
url = lpl[i].get('landing_page_url') if len(lpl) > i else None
cur, extra, conflict = eff_url(url, ac.get('utm_params'))
if equiv(cur, ch['new']):
    dec = 'AlreadyFixed'
elif cur == ch['now'] or cur in ch['alt_now']:
    dec = 'Write'
else:
    dec = 'Skipped'
mats = [{"ad_material_id": c.get('ad_material_id'), "fmt": (c.get('creative_info') or {}).get('ad_format'),
         "identity_type": (c.get('creative_info') or {}).get('identity_type'), "identity_id": (c.get('creative_info') or {}).get('identity_id'),
         "bc": (c.get('creative_info') or {}).get('identity_authorized_bc_id'), "item": (c.get('creative_info') or {}).get('tiktok_item_id'),
         "video": ((c.get('creative_info') or {}).get('video_info') or {}).get('video_id'),
         "n_images": len((c.get('creative_info') or {}).get('image_info') or []), "status": c.get('material_operation_status')}
        for c in a.get('creative_list') or []]
lpl_new = copy.deepcopy(lpl)
if len(lpl_new) > i:
    lpl_new[i]['landing_page_url'] = ch['new']
ac_new = copy.deepcopy(ac)
if ac.get('utm_params'):
    ac_new['utm_params'] = utm_from(ch['new'])
expected = {"advertiser_id": u['account_id'], "smart_plus_ad_id": ad, "landing_page_url_list": lpl_new, "ad_configuration": ac_new}


def diff(x, y, p=''):
    out = []
    if isinstance(x, dict) and isinstance(y, dict):
        for k in sorted(set(x) | set(y)):
            if k not in x:
                out.append(p + '.' + k + ' missing in sent')
            elif k not in y:
                out.append(p + '.' + k + ' extra in sent')
            else:
                out += diff(x[k], y[k], p + '.' + k)
    elif isinstance(x, list) and isinstance(y, list) and len(x) == len(y):
        for n, (q, r) in enumerate(zip(x, y)):
            out += diff(q, r, p + '[%d]' % n)
    elif x != y or type(x) != type(y):
        out.append('%s: sent %r expected %r' % (p, x, y))
    return out


if mode == 'pre':
    print('pre-read rid', pre_rid, '| decision', dec, '| cur == now:', cur == ch['now'], '| extra', extra, '| conflict', conflict)
    print('CUR:', cur)
    print('ad_name == plan:', a.get('ad_name') == u['ad_names'][0], '| op/sec:', a.get('operation_status'), a.get('secondary_status'),
          '| modify_time:', a.get('modify_time'))
    print('ad_configuration keys:', sorted(ac.keys()), '| utm_params present:', 'utm_params' in ac)
    print('materials:', mats)
    print('spark push (BC_AUTH_TT + item) in materials:', any(x['identity_type'] == 'BC_AUTH_TT' and x['item'] for x in mats))
    print('EXPECTED PAYLOAD:', json.dumps(expected, ensure_ascii=False))
elif mode in ('dry', 'live'):
    want_dry = mode == 'dry'
    cs = [(t, inp, r) for t, inp, r in mine if bool(inp.get('dry_run', True)) == want_dry]
    assert cs, 'no %s call' % mode
    t, inp, r = cs[-1]
    print('%s calls for this ad: %d' % (mode, len(cs)))
    d = diff(inp.get('payload'), expected)
    print('sent payload == expected:', not d, d)
    print('creative_list sent:', 'creative_list' in (inp.get('payload') or {}), '| other top-level args:',
          sorted(k for k in inp if k not in ('action', 'dry_run', 'payload')))
    j = result_json(r)
    if not j:
        print('RAW:', (r or '')[:1500])
        sys.exit()
    if want_dry:
        body = j['data']['data']['request']['body']
        print('preview body == expected:', not diff(body, expected), diff(body, expected))
        print('preview:', j['data']['data']['request']['method'], j['data']['data']['request']['path'], '| warnings:',
              j['data']['data'].get('warnings'), '| preflightBlocking:', j['data']['data'].get('preflightBlocking'))
    else:
        dd = j.get('data', {}).get('data', {})
        print('success:', j.get('success'), '| code:', dd.get('code'), '| message:', dd.get('message'), '| request_id:', dd.get('request_id'))
        print('resp data:', json.dumps(dd.get('data'), ensure_ascii=False)[:800])
elif mode == 'verify':
    live = [(t, inp, r) for t, inp, r in mine if inp.get('dry_run') is False]
    lrid = rid_of(live[-1][2]) if live else ''
    rid, post = rr[-1]
    print('post-read rid', rid, '| after live write:', rid[:14] > lrid[:14], '| live rid', lrid)
    plpl = post.get('landing_page_url_list') or []
    pac = post.get('ad_configuration') or {}
    purl = plpl[i].get('landing_page_url') if len(plpl) > i else None
    peff, pextra, pconf = eff_url(purl, pac.get('utm_params'))
    print('AFTER_LIVE:', purl)
    print('url field == new (bytes):', purl == ch['new'], '| effective == new:', peff == ch['new'], '| extra', pextra, '| conflict', pconf)
    print('utm_id present:', 'utm_id=' in (purl or '') or any(x['key'] == 'utm_id' for x in pac.get('utm_params') or []))
    print('landing_page_url_list length same:', len(plpl) == len(lpl), '| other entries same:',
          all(plpl[k] == lpl[k] for k in range(min(len(lpl), len(plpl))) if k != i))
    print('ad_configuration == expected:', pac == ac_new, diff(pac, ac_new))
    other = {k: (a.get(k), post.get(k)) for k in sorted(set(a) | set(post))
             if k not in ('landing_page_url_list', 'ad_configuration', 'modify_time') and a.get(k) != post.get(k)}
    print('other fields changed:', other)
    print('modify_time:', a.get('modify_time'), '->', post.get('modify_time'), '| status:', post.get('operation_status'), post.get('secondary_status'))
