#!/usr/bin/env python3
"""Build the per-change result rows from the parsed reads (prints JSON; writes nothing).
   res13.py <unit_index>|summary"""
import json, sys
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply13/work_snapchat_1')
import h13

U = h13.units()
plan0 = json.load(open(h13.plan_path(0)))
comp_after = h13.get_one(h13.creatives('u0_comp_after'), U[0]['creative_id'], 'creative')
subs_after = h13.creatives('u0_subs_after')
snap = h13.creatives('rest_snapshot')
allsubs = subs_after + snap
al = h13.ads('ads_p1') + h13.ads('ads_p2') + h13.ads('ads_p3')
ERR = "Error code: E2003, message: Property could not be updated after the Ad is in flight : [creative_ids]"
assert ERR == h13.find_key(h13.load_raw('u0_comp_live')['result'], 'sub_request_error_reason')
assert h13.find_key(h13.load_raw('u0_comp_live')['result'], 'request_id') == 'e782bf1c-ac85-4a93-90d9-d5c81aa69577'


def rows():
    res = []
    for ui, u in enumerate(U):
        users = [a['id'] for a in al if a.get('creative_id') == u['creative_id']]
        assert users == u['ad_ids'], (ui, users)
        for ch in u['changes']:
            i, sid = h13.parse_slot(ch['slot'])
            base = {'platform': 'snapchat', 'account_id': u['account_id'], 'unit_type': u['unit_type'], 'unit': u['unit'],
                    'ad_ids': u['ad_ids'], 'ad_names': u['ad_names'], 'slot': ch['slot']}
            if ui == 0:
                pc = [c for c in plan0['changes'] if c['index'] == i][0]
                assert pc['src']['id'] == sid and pc['state'] == 'NOW'
                at = comp_after['composite_properties']['creative_ids'][i]
                assert at == sid
                after = h13.get_one(subs_after, at, 'creative')['web_view_properties']['url']
                cp = h13.get_one(subs_after, pc['copy_id'], 'creative')
                assert cp['web_view_properties']['url'] == ch['new']
                det = ("Snapchat refused the composite update (PUT /v1/adaccounts/%s/creatives, full composite %s as read, only composite_properties.creative_ids changed; "
                       "dry run d6b4a2c8-a622-45a7-9e97-b37da63f3f86 matched): request_id e782bf1c-ac85-4a93-90d9-d5c81aa69577 (gateway e3c7a368-b2ae-4306-aed6-b3b1e0cd0a83) "
                       "'%s'. Stopped per recipe step 5: no retry, no other route. Copy %s of %s was created (request_id 8ed8b77d-cd73-469b-85e2-56feb0641841, "
                       "URL == new, review %s) and stays UNATTACHED (not deleted). Re-read after: ad unchanged (creative_id %s, %s, review %s; req 9d192fa0-d2ce-495a-9f41-fe1516a6fc77), "
                       "composite unchanged (original ids, review %s; req 33c06a08-90e5-4ca8-b3e2-1f27eb2eaa17), index %d still %s with URL == now (req f7f0324b-99b9-4117-8cd7-d6ccf343210a).") % (
                    u['account_id'], u['creative_id'], ERR, pc['copy_id'], sid, cp['review_status'],
                    plan0['ad']['creative_id'], plan0['ad']['status'], plan0['ad']['review_status'], comp_after['review_status'], i, at)
                res.append(dict(base, before=pc['cur'], after_expected=ch['new'], after_live=after, result='Failed', new_entity_ids=pc['copy_id'], detail=det))
            else:
                comp = h13.get_one(snap, u['creative_id'], 'creative')
                at = comp['composite_properties']['creative_ids'][i]
                assert at == sid
                cur = h13.get_one(allsubs, at, 'creative')['web_view_properties']['url']
                assert h13.classify(cur, ch) == 'NOW'
                rq = 'de7fba33-5b83-499e-90f2-53b0cb823be9' if at in [c['id'] for c in snap] else 'f7f0324b-99b9-4117-8cd7-d6ccf343210a'
                det = ("not attempted: Snapchat refused the composite update on the first unit | read-only snapshot: composite %s (used only by this ad) still holds %s at index %d, URL == now "
                       "(req de7fba33-5b83-499e-90f2-53b0cb823be9%s). No copy created.") % (
                    u['creative_id'], at, i, '' if rq.startswith('de7f') else ', f7f0324b-99b9-4117-8cd7-d6ccf343210a')
                res.append(dict(base, before=cur, after_expected=ch['new'], after_live=cur, result='NotAttempted', new_entity_ids='', detail=det))
    assert len(res) == sum(len(u['changes']) for u in U) == 36
    return res


if __name__ == '__main__':
    R = rows()
    if sys.argv[1] == 'summary':
        print({r: sum(1 for x in R if x['result'] == r) for r in sorted(set(x['result'] for x in R))}, 'total', len(R), 'bytes', len(json.dumps(R, ensure_ascii=False)))
    else:
        ui = int(sys.argv[1])
        print(json.dumps([x for x in R if x['unit'] == U[ui]['unit']], ensure_ascii=False))
