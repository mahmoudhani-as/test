"""Builds the final results list (stdout only) from the input file and this agent's own transcript reads."""
import json
import lib11 as L

U0, U1, U2 = '120253029751310058', '120253029751330058', '120252701242030058'
D0 = ("Not written: Meta refused the new creative (spec validation, not a permission reason). Pre-read 13-Oct: ad ACTIVE/ACTIVE on creative "
      "3647475952069524 (= plan; 3-card carousel with parent image_hash a75ec8e8e50f84617195ab9ca057093c + image_crops, page 1245023868693595, IG "
      "17841441699550567, no url_tags); slot = plan 'now'. Exact copy with only the 4 listed URLs = 'new' (one shared copy planned for ads "
      "120253029751310058 / 120253029697900058 / 120253029880450058); dry-run req c7e388b3-d22f-496e-b368-c3e8d07d95cb body = payload. Live POST "
      "/act_2194833637927644/adcreatives (attempt 1 of 2, req e4cc0d50-c0b3-41cd-b0ed-8a5fff00511a) rejected: code 100, subcode 2446581, OAuthException "
      "'Invalid parameter'; user title 'Invalid spec for creative with interactive components'; user msg 'There is a count mismatch between the number of "
      "child attachments in the object_story_spec and the interactive_components_spec'; is_transient false; fbtrace AXZf0-ekoQpX2QuskOGddx8. Nothing "
      "created, ad untouched; not retried. The next canary on this Page (ad 120252701242030058) got 10 / 3858749 Missing Page permission, so this ad needs "
      "the Page access and then the no-parent-image carousel recipe.")
D2 = ("Not written: Meta refused for a Page permission reason (Wadi Safar canary). Pre-read 13-Oct (meta_ad_id_get): ad PAUSED/PAUSED on creative "
      "1531013938284110 (= plan; video_data video 27820019560999513 (confirmed by meta_video_id_get), image_hash 25c2c4aa463f4462894a5ef216209b75, page "
      "1245023868693595, IG 17841441699550567), no url_tags; this slot equalled plan 'now' byte for byte. Payload = exact copy (same name, page/IG, video_id, "
      "title, message, image_hash (derived image_url not sent), CTA LEARN_MORE, degrees_of_freedom_spec, contextual_multi_ads OPT_OUT, threads_user_id, "
      "authorization_category NONE) with only this URL set to 'new'; dry-run (req 3976ecb0-7583-49bd-8b6a-755629b51bd6) body identical to the payload. Live "
      "POST /act_2194833637927644/adcreatives (attempt 1 of max 2; req 4d52910f-ee79-409f-888e-3fd2805a1d23) rejected: Meta error code 10, subcode 3858749, "
      "OAuthException 'Application does not have permission for this action'; error_data {\"page_id\":\"1245023868693595\",\"required_permission\":\"Ads\"}; "
      "user title 'Missing Page permission'; user msg 'To create posts for Page 1245023868693595, contact an admin to get permission for Advertiser role or "
      "higher. Page roles: https://developers.facebook.com/docs/business-management-apis/business-asset-management/guides/pages#pages-add-people'; "
      "is_transient false; fbtrace AszQmcDIt0Nke6cRVi0oBra. No creative created, ad not touched. Wadi Safar canary stopped here (no further calls).")
NA = 'Wadi Safar Page / Instagram access still missing'

reads = {U0: L.ad(U0)['creative'], U1: L.ad(U1)['creative'], U2: L.ad(U2)['creative']}
out = []
for u in L.units():
    cr = reads.get(u['unit'])
    for c in u['changes']:
        cur = L.full_url(cr, c['slot']) if cr is not None else ''
        if cr is not None:
            assert cur == c['now'] or cur in c['alt_now'], (u['unit'], c['slot'], cur)
        if u['unit'] == U0:
            res, det = 'Failed', D0
        elif u['unit'] == U2:
            res, det = 'Failed', D2
        else:
            res, det = 'NotAttempted', NA
        out.append({'platform': 'meta', 'account_id': u['account_id'], 'unit_type': u['unit_type'], 'unit': u['unit'],
                    'ad_ids': u['ad_ids'], 'ad_names': u['ad_names'], 'slot': c['slot'], 'before': cur,
                    'after_expected': c['new'], 'after_live': cur, 'result': res, 'new_entity_ids': '', 'detail': det})
n = len(out)
assert n == sum(len(u['changes']) for u in L.units()) == 92
import collections
print(collections.Counter(r['result'] for r in out), n)
print(json.dumps(out, ensure_ascii=False))
