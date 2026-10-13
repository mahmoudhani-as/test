# Read-only: print (stdout only, no file) one result object per input change, from my transcript's exact reads / calls.
import sys, json, re
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply8/work_tiktok_1/scripts')
from common import *
from tr import calls, result_json, ad_reads, sp_reads

PIXEL_RID = '20261013174218641469AF6C28E87DA7AC'
pre1 = load_tool_json(W + 'reads/pre_manual_19.json')
pre2 = load_tool_json(W + 'reads/pre2_manual_18.json')
P1 = {a['ad_id']: a for a in pre1['data']['data']['data']['list']}
P2 = {a['ad_id']: a for a in pre2['data']['data']['data']['list']}
R1 = pre1['data']['data']['request_id']
R2 = pre2['data']['data']['request_id']
raw = open(W + 'reads/post_manual_19.txt', encoding='utf-8').read()
fj = json.loads(raw)
FINAL = {a['ad_id']: a for a in fj['data']['data']['data']['list']}
FRID = fj['data']['data']['request_id']
reads = ad_reads()


def rid_of(txt):
    j = result_json(txt) or {}
    return ((j.get('data') or {}).get('data') or {}).get('request_id') or ''


def code_of(txt):
    j = result_json(txt) or {}
    d = (j.get('data') or {}).get('data') or {}
    return d.get('code'), d.get('message'), (d.get('data') or {}).get('need_audit')


out = []
for u in INP:
    ad = u['unit']
    ch = u['changes'][0]
    base = {"platform": "tiktok", "account_id": u['account_id'], "unit_type": u['unit_type'], "unit": ad,
            "ad_ids": u['ad_ids'], "ad_names": u['ad_names'], "slot": ch['slot'], "after_expected": ch['new'], "new_entity_ids": ""}
    if ch['slot'] == 'ad.landing_page_url':
        a = P1[ad]
        before = eff_url(a['landing_page_url'], a.get('utm_params'))[0]
        assert before == ch['now']
        if ad in P2:
            assert P2[ad] == a
        ups = [(t, i, r) for t, i, r in calls('tiktok_ad_update') if i['payload']['creatives'][0]['ad_id'] == ad]
        dry = [x for x in ups if x[1].get('dry_run') is True]
        live = [x for x in ups if x[1].get('dry_run') is False]
        assert len(dry) == 1 and len(live) == 1
        lrid = rid_of(live[0][2])
        code, msg, audit = code_of(live[0][2])
        post_rid, post = reads[ad][-1]
        assert post_rid[:14] > lrid[:14]
        after = post['landing_page_url']
        eff = eff_url(after, post.get('utm_params'))[0]
        fin = FINAL[ad]
        other = {k for k in set(a) | set(post) if k not in ('landing_page_url', 'utm_params', 'modify_time') and a.get(k) != post.get(k)}
        ok = after == ch['new'] and eff == ch['new'] and code == 0 and not other and fin['landing_page_url'] == ch['new']
        pre_txt = 'pre-read ad/get req %s%s' % (R1, (' + re-read req %s (identical)' % R2) if ad in P2 else '')
        detail = ('%s: landing_page_url == now (CUSTOMIZED_USER manual SINGLE_VIDEO ad, no tiktok_item_id, identity %s, adgroup %s, '
                  'call_to_action LEARN_MORE, utm_params had %d keys %s, operation_status %s / %s, modify_time %s). '
                  'dry_run ad/update: call input and preview body == payload built from the read (all creative fields sent back as read; '
                  'only landing_page_url = new and utm_params = the 5 UTMs of new, no utm_id; tracking_pixel_id sent as exact string '
                  '7347671240183693330 = pixel/list req %s; ad_text unchanged, no trailing space). '
                  'live ad/update req %s: code %s %s, need_audit %s. read-back ad/get req %s: landing_page_url == new byte for byte, '
                  'utm_params == UTMs of new, no utm_id, no other field changed (status %s / %s unchanged, modify_time %s). '
                  'Final re-read req %s confirms.') % (
            pre_txt, a['identity_id'], a['adgroup_id'], len(a.get('utm_params') or []), [x['key'] for x in a.get('utm_params') or []],
            a['operation_status'], a['secondary_status'], a['modify_time'], PIXEL_RID, lrid, code, msg, str(audit).lower(), post_rid,
            post['operation_status'], post['secondary_status'], post['modify_time'], FRID)
        r = dict(base, before=before, after_live=after, result='Fixed' if ok else 'Failed', detail=detail)
    else:
        m = re.fullmatch(r'smart_plus_ad\.landing_page_url_list\[(\d+)\]\.landing_page_url', ch['slot'])
        i = int(m.group(1))
        sr = sp_reads()[ad]
        ups = [(t, x, rr) for t, x, rr in calls('tiktok_smart_plus_ad_update') if x['payload']['smart_plus_ad_id'] == ad]
        dry = [x for x in ups if x[1].get('dry_run') is True]
        live = [x for x in ups if x[1].get('dry_run') is False]
        assert len(dry) == 1 and len(live) == 1
        lrid = rid_of(live[0][2])
        code, msg, _ = code_of(live[0][2])
        pre_rid, a = [x for x in sr if x[0][:14] < lrid[:14]][-1]
        post_rid, post = sr[-1]
        assert post_rid[:14] > lrid[:14]
        before = eff_url(a['landing_page_url_list'][i]['landing_page_url'], (a.get('ad_configuration') or {}).get('utm_params'))[0]
        assert before == ch['now']
        after = post['landing_page_url_list'][i]['landing_page_url']
        other = {k for k in set(a) | set(post) if k not in ('landing_page_url_list', 'modify_time') and a.get(k) != post.get(k)}
        ok = after == ch['new'] and code == 0 and not other
        cl = a['creative_list'][0]['creative_info']
        detail = ('pre-read smart_plus/ad/get req %s (also req 2026101317422790F655C80F26AFBD5F11): landing_page_url_list[%d] == now '
                  '(Upgraded Smart+ ad, 1 material %s %s %s identity %s / BC %s, no tiktok_item_id (not a Spark Push), 1 image; '
                  'ad_configuration.utm_params absent; operation_status %s / %s, modify_time %s). dry_run smart_plus/ad/update: call input and '
                  'preview body == payload (smart_plus_ad_id + landing_page_url_list with only [%d].landing_page_url = new + ad_configuration '
                  'exactly as read; creative_list, ad_text_list, ad_name, status not sent). live smart_plus/ad/update req %s: code %s %s. '
                  'read-back smart_plus/ad/get req %s: landing_page_url_list[%d] == new byte for byte, no utm_id, ad_configuration and '
                  'creative_list unchanged (still no tiktok_item_id), status %s / %s unchanged, modify_time %s.') % (
            pre_rid, i, a['creative_list'][0]['ad_material_id'], cl['ad_format'], cl['identity_type'], cl['identity_id'],
            cl['identity_authorized_bc_id'], a['operation_status'], a['secondary_status'], a['modify_time'], i, lrid, code, msg,
            post_rid, i, post['operation_status'], post['secondary_status'], post['modify_time'])
        r = dict(base, before=before, after_live=after, result='Fixed' if ok else 'Failed', detail=detail)
    out.append(r)

print(json.dumps(out, ensure_ascii=False))
print('COUNTS', {k: sum(1 for x in out if x['result'] == k) for k in ('Fixed', 'AlreadyFixed', 'Failed', 'Skipped', 'NotAttempted')}, len(out))
