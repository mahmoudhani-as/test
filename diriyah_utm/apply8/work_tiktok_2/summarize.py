import json, sys
sys.path.insert(0, '.')
import tt2
from tt2 import units, update_calls, pre_read_for, latest, reads, build, resp_summary, classify, eff, materials, SP_RE, new_utms, diff_fields
import copy

ins = json.load(open(tt2.INP))
R = reads()
out = []
for u in ins:
    ad = u['unit']; ch = u['changes'][0]
    calls = update_calls(ad)
    dry = [c for c in calls if c['dry']]; live = [c for c in calls if not c['dry']]
    first = calls[0]
    pre = pre_read_for(ad, first['order'])
    cls = classify(ad, pre)
    lc = live[-1]
    post = latest(ad, after_order=lc['order'], R=R)
    i = int(SP_RE.match(ch['slot']).group(1))
    url = post['rec']['landing_page_url_list'][i]['landing_page_url']
    ups = (post['rec'].get('ad_configuration') or {}).get('utm_params')
    after, extra, conflict = eff(url, ups)
    built = build(ad, pre)
    d_ok = dry[-1]['input'].get('payload') == built
    d_prev = resp_summary(dry[-1]['txt']).get('preview_body') == built
    l_ok = live[-1]['input'].get('payload') == built
    ls = resp_summary(live[-1]['txt'])
    def norm(r):
        r = copy.deepcopy(r); r['creative_list'] = sorted(r.get('creative_list') or [], key=lambda c: str(c.get('ad_material_id'))); return r
    dd = diff_fields(norm(pre['rec']), norm(post['rec']))
    other = [x[0] for x in dd if x[0] != 'modify_time' and not x[0].startswith('landing_page_url_list[%d].landing_page_url' % i) and not x[0].startswith('ad_configuration.utm_params')]
    mats = materials(pre['rec'])
    from collections import Counter as C
    grp = C((m['fmt'], m['identity_type'], m['identity_id']) for m in mats)
    mdesc = ', '.join('%s%s %s identity %s' % (('%dx ' % n) if n > 1 else '', f, it, iid) for (f, it, iid), n in grp.items())
    had_utm = cls['utm_params'] is not None
    old_utm_id = had_utm and any(p['key'] == 'utm_id' for p in cls['utm_params'])
    utm_note = ('ad_configuration.utm_params = the 5 UTMs of new (old set replaced%s)' % (', utm_id removed' if old_utm_id else '')) if had_utm else 'no utm_params on the ad (none added)'
    ok_all = d_ok and d_prev and l_ok and ls.get('code') == 0 and not other and post['rec'].get('operation_status') == pre['rec'].get('operation_status')
    result = 'Fixed' if (after == ch['new'] and url == ch['new'] and ls.get('code') == 0) else 'Failed'
    detail = ('Upgraded Smart+ ad: %s, no tiktok_item_id (not a Spark post). Pre-read smart_plus/ad/get req %s: URL == now (%s / %s). '
              'smart_plus/ad/update with landing_page_url_list[%d].landing_page_url = new and %s; rest of ad_configuration as read; creative_list/ad_text_list/ad_name/status not sent. '
              'Dry run: input and preview == built payload. Live attempt 1: code %s %s req %s. '
              'Read-back req %s: landing_page_url == new byte for byte, %s, still no tiktok_item_id, no other field changed, status unchanged (%s / %s), modify_time %s -> %s.') % (
        mdesc, pre['request_id'], cls['op'], cls['sec'], i, utm_note, ls.get('code'), ls.get('message'), ls.get('request_id'),
        post['request_id'], ('utm_params match new' if had_utm else 'no utm_params'),
        post['rec'].get('operation_status'), post['rec'].get('secondary_status'), pre['rec'].get('modify_time'), post['rec'].get('modify_time'))
    assert ok_all, ad
    assert (ups == new_utms(ch['new'])) if had_utm else (not ups), ad
    out.append({'platform': 'tiktok', 'account_id': u['account_id'], 'unit_type': u['unit_type'], 'unit': ad, 'ad_ids': u['ad_ids'], 'ad_names': u['ad_names'],
                'slot': ch['slot'], 'before': cls['cur'], 'after_expected': ch['new'], 'after_live': after, 'result': result, 'new_entity_ids': '', 'detail': detail})
    assert cls['cur'] == ch['now'], ad
print(json.dumps(out, ensure_ascii=False))
from collections import Counter
print(Counter(o['result'] for o in out), len(out))
