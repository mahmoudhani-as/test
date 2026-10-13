import json,sys
sys.path.insert(0,'/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply11/work_snapchat_snap_split_8/')
from lib import *
U=units()
# ---- unit 1 facts
u1sub_url="https://www.diriyahcompany.sa/ar/life-in-diriyah?utm_content=cr1&utm_source=snapchat&utm_medium=paid-social&utm_term=adset-id-9a4d62_life-in-diriyah_ar_all_mf_prospecting&utm_campaign=lifeindiriyah_jun2026"
cr=json.load(open(W+'u1_created_subs.json'))
copymap={o:n for o,n,_ in cr['map']}
# re-read after the failed attach: every original sub URL (req ids)
u1_after={"3864d4f7-b493-46dc-af94-6dcd20ea8a3c":"062d1a01-9316-470f-8d0a-94b8e4b122fa","186ec042-b20e-419a-88f2-51963737a89f":"fbe03a3c-1eed-4a25-b775-3587da21ee8c","c3ee3d39-8723-4067-842a-9313d81eb257":"c72b8d9c-cb1a-414b-b5e7-b6612298e13c","d1caa22d-4eb9-46e1-8127-12f135157bfe":"416b632d-b6fe-451f-b9cb-26e4aa08077b","0fc2aeb8-4922-4bdd-a707-353ba83b2f65":"a15b4790-1a5c-4f25-8dc0-42b2d7606513","9ebe2063-bbbc-46ef-b5b4-9cb326eb9af1":"dc9cbeb8-9b73-4e5a-8734-3eb91df2d75e"}
# ---- units 2-8 re-reads (13-Oct, read-only)
ads={
 "ccf1d318-fd86-4b32-a70c-c096073b7752":("d61bba60-e7cb-452c-a372-39ea25d4b303","4b5b819c-5c9a-47e3-9256-ad3f29b7ef27","PAUSED","f26d9458-5bd8-4596-90a2-dd9d77299b4b"),
 "d07f22e2-0f91-4b95-9853-881e5b2300e7":("852ca250-88c3-4f3d-a83b-352b726ed137","3b2997d1-5386-47c1-9b08-6cfd76304b56","PAUSED","6374c378-819a-45ca-abd2-bbdd95945b8b"),
 "db056e55-656c-4ef1-93b0-6449550b910f":("fbd7bd19-bbe3-49fa-b2c2-dca6d583e823","92d70bb2-4218-44ac-847d-d94ef096f63d","PAUSED","b70a0c1e-07da-4943-b161-6ee4efb29706"),
 "e110837b-3b17-4150-bb0e-8b161b592440":("fbd7bd19-bbe3-49fa-b2c2-dca6d583e823","43846fdb-7b9f-4f9e-be81-440b3682709e","ACTIVE","f1551811-05c5-42f2-8bb6-ab02dfbacd27"),
 "f3a74b14-082f-446d-bb8a-ed6fba406d5f":("ba21ea80-b5cb-4c08-b226-ea96bed265d5","2ec7ffd5-0d76-4476-ad1b-98ddd741ce46","ACTIVE","36bf12df-aba2-4ead-8f23-1a9d57a1f39d"),
 "f97aff65-bdc8-41ea-864a-8081ae64dc5c":("3eb87287-2d13-441f-bcb8-ee1e2d9446a5","3b2997d1-5386-47c1-9b08-6cfd76304b56","PAUSED","bb8c963f-f1a2-4bbb-a516-5def6079f52e"),
 "ffd6c9a7-55aa-46a8-a42d-1f16c6147d42":("3eb87287-2d13-441f-bcb8-ee1e2d9446a5","3b2997d1-5386-47c1-9b08-6cfd76304b56","PAUSED","8395f4ae-7c5d-4ba7-beb1-df3e759a8645"),
 "fa635afe-f646-4c38-93a5-fd80239f980c":("8fadf2c1-eae2-4f3c-ad76-f5ebed001943","e6788c94-9c10-44ed-b61b-1f350b494851","PAUSED","6bea22f0-c585-4306-a5d9-7aaccdb1f1b0"),
}
crs={
 "4b5b819c-5c9a-47e3-9256-ad3f29b7ef27":("https://www.diriyahcompany.sa/ar/diriyah-living/alhadawi?utm_source=snapchat&utm_medium=paid-social&utm_campaign=ManazelAlHadawi_Jun2026&utm_term=adset-id-6AA7C3_manazel-alhadawi_ar_all_mf_prospecting&utm_content=ad-id-FBF5EC_manazel-alhadawi-kv1_display","d6a1c7bd-76d0-4ae5-9326-502edd2aa5f9"),
 "3b2997d1-5386-47c1-9b08-6cfd76304b56":("https://www.diriyahcompany.sa/ar/diriyah-living/alhadawi?utm_source=snapchat&utm_medium=paid-social&utm_campaign=ManazelAlHadawi_Jun2026&utm_term=manazel-alhadawi_ar_all_mf_prospecting&utm_content=manazel-alhadawi-kv2_display","bc8ce40f-72f7-4afc-a5fa-0ca5080a5760"),
 "92d70bb2-4218-44ac-847d-d94ef096f63d":("https://www.diriyahcompany.sa/ar/diriyah-living/alhadawi?utm_source=snapchat&utm_medium=paid-social&utm_campaign=ManazelAlHadawi_Jun2026&utm_term=manazel-alhadawi_ar_all_mf_prospecting&utm_content=manazel-alhadawi-kv1_display","804fa2d2-afd4-48ee-a09a-bddfd1b3bf78"),
 "43846fdb-7b9f-4f9e-be81-440b3682709e":("https://www.diriyahcompany.sa/ar/diriyah-living/alhadawi?utm_source=snapchat&utm_medium=paid-social&utm_campaign=ManazelAlHadawi_Jun2026&utm_term=adset-id-6AA7C3_manazel-alhadawi_ar_all_mf_prospecting&utm_content=ad-id-4F05A1_manazel-alhadawi-kv2_display","8bcff095-5fce-4e1b-8a8a-f65d91c55a66"),
 "2ec7ffd5-0d76-4476-ad1b-98ddd741ce46":("https://www.diriyahcompany.sa/ar/life-in-diriyah?utm_source=snapchat&utm_medium=paid-social&utm_campaign=2c0ef446_diriyah-living_sep26&utm_term=3e71b680_residential_ar&utm_content=fa60e06a_resi-patio-kv1_display_ar","65c6f177-1dc7-4c21-95c4-ac84bed78c63"),
 "e6788c94-9c10-44ed-b61b-1f350b494851":("https://www.diriyahcompany.sa/en/diriyah-living/alhadawi?utm_source=snapchat&utm_medium=paid-social&utm_campaign=ManazelAlHadawi_Jun2026&utm_term=manazel-alhadawi_en_all_mf_prospecting&utm_content=manazel-alhadawi-kv2_display","750564de-29e0-4a55-a278-54ff425de691"),
}
res=[]
E1008="Error code: E1008, message: Request cannot be processed due to validation error : [This field cannot be updated. Field creativeId: original value 92f0f5a1-6405-489c-bbe4-a76e8893d354 does not match update value 38c1b89c-8601-4147-8592-35598229412e.]"
for ui,u in enumerate(U):
    for ch in u['changes']:
        r={"platform":"snapchat","account_id":u['account_id'],"unit_type":u['unit_type'],"unit":u['unit'],"ad_ids":u['ad_ids'],"ad_names":u['ad_names'],"slot":ch['slot'],"after_expected":ch['new']}
        if ui==0:
            sid=ch['slot'].split('(')[1].split(')')[0]
            assert classify(u1sub_url,ch)=='write'
            r.update(before=u1sub_url, after_live=u1sub_url, result="Failed",
              new_entity_ids="sub-creative copy %s (copy of %s, web_view_properties.url = new); composite copy 38c1b89c-8601-4147-8592-35598229412e (both unattached)"%(copymap[sid],sid),
              detail=("Before = now (sub-creative %s, APPROVED). Created copy %s (every settable field as read, only web_view_properties.url = new; bulk POST /v1/adaccounts/ebe8d66e-0e3e-4b71-9d37-5c53118d6481/creatives, Snap req d345e0e8-0fb6-4a24-acd2-c357864b7a6f, SUCCESS, response URL = new, PENDING_REVIEW) and COMPOSITE copy 38c1b89c-8601-4147-8592-35598229412e of 92f0f5a1 (6 copies, same order; req 7565f185-a87b-4963-b287-852cb91bffdb, PENDING_REVIEW). "
                      "Switching ad ba4a051d to it was refused by Snapchat: (1) PUT /v1/adsquads/03a34ce5-12ba-4e19-b56c-338a4b4050d9/ads, full ad object as read, only creative_id changed (status PAUSED kept) -> req 5abcc46c-48ff-42cf-b621-830837a1b1b8 ERROR \"%s\"; (2) PATCH same ad, JSON-Patch replace /creative_id -> req 5f4129e2-5081-43bf-bf8c-2cc209c6a163, same E1008. Both attempts used. "
                      "Re-read: ad unchanged (creative_id 92f0f5a1-6405-489c-bbe4-a76e8893d354, PAUSED, APPROVED, updated_at 2026-10-06T17:20:31.807Z, req c3aff977-1a9b-4578-896a-ca7b2736a7ee); sub-creative %s unchanged, URL = now, APPROVED (req %s). The new creatives are unattached; nothing deleted.")%(sid,copymap[sid],E1008,sid,u1_after[sid]))
        else:
            ad_reads=[ads[a] for a in u['ad_ids']]
            cids={a[1] for a in ad_reads}
            assert cids=={u['creative_id']}, (u['unit'],cids)
            cur,creq=crs[u['creative_id']]
            assert ch['slot']=='creative.web_view_properties.url'
            cls=classify(cur,ch); assert cls=='write' and cur==ch['now'], (u['unit'],cls)
            adtxt="; ".join("ad %s: ad squad %s, creative_id %s, status %s, review APPROVED (req %s)"%(a,ads[a][0],ads[a][1],ads[a][2],ads[a][3]) for a in u['ad_ids'])
            r.update(before=cur, after_live=cur, result="NotAttempted", new_entity_ids="",
              detail=("Not attempted: stopped after unit 1 (ad ba4a051d) hit a systemic Snapchat refusal: an existing ad's creative_id cannot be changed (E1008 'This field cannot be updated. Field creativeId', via full-object PUT and JSON-Patch PATCH), and every snap_split unit needs that switch. "
                      "Read-only re-read 13-Oct: %s; creative %s web_view_properties.url = plan 'now' byte for byte, APPROVED (req %s). Nothing created or written.")%(adtxt,u['creative_id'],creq))
        res.append(r)
print(json.dumps(res,ensure_ascii=False))
from collections import Counter
print(len(res), Counter(x['result'] for x in res))
