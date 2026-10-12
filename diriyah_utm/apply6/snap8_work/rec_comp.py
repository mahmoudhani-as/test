import sys, re, glob; sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/snap8_work')
from lib import *

ALLOWED = ('.review_status', '.review_status_details', '.semantic_id', '.updated_at')

def rec_composite(i, parent_pre_req, dry_req, live_req, post_reqs, parent_post_req):
    U = units(); u = U[i]
    meta = json.load(open(os.path.join(WD, 'meta_u%d.json' % i)))
    exp = json.load(open(os.path.join(WD, 'payload_u%d_subs.json' % i)))
    dr = raw_result(dry_req)['data']['data']['request']
    assert dr['body'] == exp, 'dry-run body mismatch'
    lv = raw_result(live_req)['data']['data']
    assert lv['request_status'] == 'SUCCESS'
    sub_status = {x['creative']['id']: x['sub_request_status'] for x in lv['creatives']}
    ppre = creatives_from(raw_result(parent_pre_req))[0]
    ppost = creatives_from(raw_result(parent_post_req))[0]
    save('post_u%d_parent_%s.json' % (i, u['unit'][:8]), ppost)
    pd = diff(ppre, ppost)
    p_unexp = [x for x in pd if x[0] not in ALLOWED]
    psc = '; '.join("%s %r->%r" % (p, a, b) for p, a, b in pd)
    rows = []
    for ch, m, post_req in zip(u['changes'], meta, post_reqs):
        sid = m['sid']
        idx = int(re.search(r'creative_ids\[(\d+)\]', ch['slot']).group(1))
        pre = json.load(open(glob.glob(os.path.join(WD, 'pre_u%d_sub%d_%s.json' % (i, idx, sid[:8])))[0]))
        assert creatives_from(raw_result(m['pre_req']))[0] == pre
        post = creatives_from(raw_result(post_req))[0]
        assert post['id'] == sid
        save('post_u%d_sub%d_%s.json' % (i, idx, sid[:8]), post)
        after = post['web_view_properties']['url']
        ok = after == ch['new'] and sub_status.get(sid) == 'SUCCESS'
        d = [x for x in diff(pre, post) if x[0] != '.web_view_properties.url']
        unexp = [x for x in d if x[0] not in ALLOWED]
        before = pre['web_view_properties']['url']
        which = 'now' if before == ch['now'] else ('alt_now[%d]' % ch['alt_now'].index(before) if before in ch['alt_now'] else 'now/alt_now (param order differs)')
        sc = '; '.join("%s %r->%r" % (p, a, b) for p, a, b in d)
        detail = ("COMPOSITE sub-creative %s (creative_ids[%d] of %s); pre-read (req %s) url == plan %s; PUT /v1/adaccounts/{id}/creatives "
                  "(snapchat_adaccounts_ad_account_id_creatives_update) with the full creative object as read, only web_view_properties.url changed "
                  "(%d sub-creatives of this composite in one PUT); dry_run preview checked first (req %s: sent body byte-identical to the reads except url, verified from raw tool results); "
                  "live request_status SUCCESS, sub_request %s, req %s; read-back (req %s) url %s; review_status after write: %s (re-review triggered by the PUT); "
                  "server changed: %s; %s; side effect: parent composite %s (not written) %s%s") % (
            sid, idx, u['unit'], m['pre_req'], which, len(meta), dry_req, sub_status.get(sid), live_req, post_req,
            'matches new byte for byte' if ok else 'DOES NOT match new', post.get('review_status'), sc,
            'all other fields unchanged on re-read' if not unexp else 'UNEXPECTED other changes: %r' % unexp,
            u['unit'], psc, '' if not p_unexp else ' UNEXPECTED parent changes: %r' % p_unexp)
        row = dict(platform='snapchat', account_id=u['account_id'], unit_type=u['unit_type'], unit=u['unit'], ad_ids=u['ad_ids'], ad_names=u['ad_names'],
                   slot=ch['slot'], before=before, after_expected=ch['new'], after_live=after,
                   result='Fixed' if ok else 'Failed', new_entity_ids='', detail=detail)
        record(row)
        rows.append(row)
        print(i, sid[:8], row['result'], post.get('review_status'), 'unexpected=', unexp)
    print('parent diffs:', [(p, a, b) for p, a, b in pd], 'unexpected parent:', p_unexp)
    return rows
