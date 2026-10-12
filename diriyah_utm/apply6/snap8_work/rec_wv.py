import sys; sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/snap8_work')
from lib import *

def rec_webview(i, pre_req, dry_req, live_req, post_req):
    U = units(); u = U[i]; ch = u['changes'][0]
    tag = 'u%d_%s' % (i, u['unit'][:8])
    pre = json.load(open(os.path.join(WD, 'pre_%s.json' % tag)))
    exp = json.load(open(os.path.join(WD, 'payload_%s.json' % tag)))
    assert creatives_from(raw_result(pre_req))[0] == pre
    dr = raw_result(dry_req)['data']['data']['request']
    assert dr['body'] == exp, 'dry-run body mismatch'
    lv = raw_result(live_req)['data']['data']
    assert lv['request_status'] == 'SUCCESS' and lv['creatives'][0]['sub_request_status'] == 'SUCCESS'
    post = creatives_from(raw_result(post_req))[0]
    assert post['id'] == u['unit']
    save('post_%s.json' % tag, post)
    after = post['web_view_properties']['url']
    ok = after == ch['new']
    d = [x for x in diff(pre, post) if x[0] != '.web_view_properties.url']
    unexpected = [x for x in d if x[0] not in ('.review_status', '.review_status_details', '.semantic_id', '.updated_at')]
    before = pre['web_view_properties']['url']
    which = 'now' if before == ch['now'] else ('alt_now[%d]' % ch['alt_now'].index(before) if before in ch['alt_now'] else 'now/alt_now (param order differs)')
    sc = '; '.join("%s %r->%r" % (p, a, b) for p, a, b in d)
    detail = ("WEB_VIEW creative; pre-read (req %s) url == plan %s; PUT /v1/adaccounts/{id}/creatives "
              "(snapchat_adaccounts_ad_account_id_creatives_update) with the full creative object as read, only web_view_properties.url changed; "
              "dry_run preview checked first (req %s: sent body byte-identical to the read except url, verified from raw tool results); "
              "live request_status SUCCESS, sub_request SUCCESS, req %s; read-back (req %s) url %s; "
              "review_status after write: %s (re-review triggered by the PUT); server changed: %s; %s") % (
        pre_req, which, dry_req, live_req, post_req, 'matches new byte for byte' if ok else 'DOES NOT match new',
        post.get('review_status'), sc,
        'all other fields unchanged on re-read' if not unexpected else 'UNEXPECTED other changes: %r' % unexpected)
    row = dict(platform='snapchat', account_id=u['account_id'], unit_type=u['unit_type'], unit=u['unit'], ad_ids=u['ad_ids'], ad_names=u['ad_names'],
               slot=ch['slot'], before=before, after_expected=ch['new'], after_live=after,
               result='Fixed' if ok else 'Failed', new_entity_ids='', detail=detail)
    record(row)
    print(i, u['unit'][:8], row['result'], post.get('review_status'), 'unexpected=', unexpected)
    return row
