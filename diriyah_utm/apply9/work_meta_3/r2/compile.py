import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply9/work_meta_3/r2')
from lib9b import *

DET = {
 '120250837203070058': ('Fixed', '1463789968940834',
  'Pre-read rid af498a04-3975-42c3-a18f-807a7a8b4c12: slot == now (boosted IG post creative 1343805547279420; ad ACTIVE / ADSET_PAUSED). Attached creative 1463789968940834 instead of creating another: created for this exact change at 11:37 UTC by the earlier apply9 in_meta_3 run (wf_4c644ce9-3b9, create rid 06996461-340a-470a-a8b8-86877d9bd2a7; never attached there after a denied local step); its create input == payload rebuilt now from the live creative; read-back rid 0922b00c-e1d0-4f80-88de-fb4952205f0a identical except link = new and Meta-set fields (DoF all OPT_OUT, name auto-set from caption + 2026-10-13 suffix, new FB-side story 111467331865347_1111087461780512; same IG media 18401371108157770). Attach (creative only, no status) dry rid 0ae3de26-61dd-4d52-b4c6-1b86a110010e, live rid ebeafd95-045e-4b5b-9002-d0951caf5409 success. Verify rid dc2a703e-d2a7-496a-a214-786c804accfb: == new byte for byte; ad ACTIVE, effective IN_PROCESS (review).'),
 '120251640486710058': ('Fixed', '1501028818519265',
  'Pre-read rid b2d82907-5900-428c-933b-a53a1711e0f0: slot == now (creative 1357975345811706). Exact copy with only this URL changed; deprecated DoF standard_enhancements (OPT_OUT) not sent. Create dry rid 0a17d1a8-c603-4c9e-b11b-6b91513d0650 (body == payload), live rid 3ec18437-21b4-4ce2-9c79-c6e0bcc4f1b7 -> 1501028818519265; read rid 7c0f5674-dd45-47d0-b4cb-faca7fa21a50 identical except URL, Meta DoF defaults (all OPT_OUT) and name suffix. Attach dry rid 8acee804-c422-4072-8c79-9bf2bc6285f7, live rid cc08087f-8485-47e0-9773-d331c64ea150 success. Verify rid a7874d60-0a9c-4a61-a352-9701655e3e5e: == new; ad ACTIVE, effective IN_PROCESS (review).'),
 '120252925092860058': ('AlreadyFixed', '',
  'Re-read rid d5099b1e-6d76-4c09-928a-ab448fa88ca7: ad already on creative 1094704503143112 with both link_urls == new byte for byte; no write in this run. Written for this same change at 11:42-11:43 UTC by the earlier apply9 in_meta_3 run (wf_4c644ce9-3b9: create rid 942cb886-1a77-49fc-b58d-9c716905cf6d, attach rid 584ba64d-5640-4b17-b8ff-7e6b8495fc45). Ad ACTIVE, effective ACTIVE (review passed).'),
 '120252926501150058': ('Fixed', '1784997465881174',
  'Pre-read rid f01810e1-fdb9-4548-ba36-335769d865e1: slot == now (creative 1402286615380460). Attached creative 1784997465881174 instead of creating another: created for this exact change at 11:44 UTC by the earlier apply9 in_meta_3 run (wf_4c644ce9-3b9, create rid 88e50581-fbd4-4d38-8568-eb5363650819; that run stopped before attaching); its create input == payload rebuilt now; read-back rid 1107000d-1fca-4f74-a1be-86c6031ce99c identical except URL, Meta DoF defaults (all OPT_OUT) and name suffix. Attach dry rid 0011f708-c476-48c9-9544-271238345299, live rid 641d6814-c144-4d2c-8aba-da35b01f5f99 success. Verify rid 869f34bb-6e59-4e74-94f4-9169bd79dc6a: == new; ad ACTIVE, effective IN_PROCESS (review).'),
 '120253101798820058': ('Fixed', '1109735604785564',
  'Pre-read rid 06e24237-0789-4b7e-8d46-9fe9be29fede: slot == now (video creative 1406053448328258). Exact copy with only this link changed; derived video_data.image_url not sent (same image_hash sent). Create dry rid dfa3cff2-39b1-40db-8171-3696b92800d9 (body == payload), live rid 50ba23a3-4169-4823-b58b-9537260f58eb -> 1109735604785564; read rid 6f2463b1-12f8-4c65-b9b7-9c9249b893b2 identical except link (+ its derived top-level CTA mirror), re-signed image_url for the same hash, name suffix. Attach dry rid 2b58a225-15da-4708-994a-0adebbaf86b8, live rid 69cd3bce-d032-4955-975e-c8be0067cd39 success. Verify rid fb57585a-3e56-4942-a8c3-9896a6049114: == new; ad ACTIVE, effective IN_PROCESS (review).'),
 'SHARED_1421339153512972': ('Fixed', '1108773658514036',
  'Ads 120251976401220058 + 120251890583050058 shared carousel creative 1421339153512972 with the same 6 changes: ONE new creative attached to both (they keep sharing one post). Pre-reads rid 7bf77839-286f-4d56-be9d-2816cd4909b5 / eed0fff3-6446-4292-b1b6-788ce5022aab: all 6 links == now. Create dry rid 941a8767-b3b8-471f-b636-e19c6e0e773b (body == payload), live rid b17000a8-f755-414e-8b80-6a76e9c199d0 -> 1108773658514036; read rid bfe9fd37-29d7-4aee-a857-7cfa5a0d1842: no diff except the 6 links (Meta cut the stored name to 100 chars + suffix). Attach 120251976401220058 dry rid c98657e2-2b4f-459f-aaf5-88247818ad7a live rid e9882297-7575-4be9-8412-d6475ee7fd5d; 120251890583050058 dry rid 3d0f6c22-e428-493e-9817-6b00c3dbcdbe live rid 3021917c-0ffa-4ad1-a2d1-83c3f9d25feb. Verify rids 6e7f238e-5dc6-4c17-9c51-5c4396df13d3 / bd177a08-ac7b-47d3-8e97-a7954614dfc8: all 6 links == new on both; ACTIVE, effective IN_PROCESS (was ADSET_PAUSED).'),
 '120250238408240058': ('Fixed', '2342801556520183',
  'Pre-read rid 4ba325fb-6b95-4793-96ad-8040b9bf78c3: both link_urls == now (ad PAUSED; creative 1442950770931553, carousel asset feed). Exact copy with only link_urls[0]/[1] changed. Create dry rid a2709aa4-175d-4e12-b0e2-b9d180012663 (body == payload), live rid f7adca79-9a11-4891-b2f3-bf63080749ce -> 2342801556520183; read rid 81fd742e-1627-4d32-847b-3d7734c3e273 identical except URLs, Meta defaults (DoF all OPT_OUT, destination_screenshot OPT_OUT), name suffix. Attach dry rid 29d272a3-d8a4-4094-abf8-9855bb2191b4, live rid 204dcd00-0cde-49cb-b971-d0f0aca2e690 success. Verify rid 9e9d9d16-669f-44d4-9726-ec52777afb4c: both == new (Meta lists the two in swapped order, same URL); ad still PAUSED, effective IN_PROCESS.'),
 'SHARED_1632863468347851': ('Fixed', '1744787543489978',
  'Ads 120253320140850058 + 120253320140450058 + 120253320135390058 shared creative 1632863468347851 with the same change: ONE new creative attached to all three (they keep sharing one post). Pre-reads rid a442de92-c5d5-4e3c-96f9-ef863763c718 / 1d3b9017-460c-4ac7-aabb-8fe45f8ece0d / 3b75ebfd-89f2-4fdc-a529-39fefb0e8471: == now. Create dry rid 3ebfc3c7-b4aa-40e4-8bbd-8f6b47fff2d8 (body == payload), live rid 17ea9a4f-5d29-4b61-961c-e12acd02cf57 -> 1744787543489978; read rid 07fc8713-0b76-46a8-89d2-1089e2b75a4c: no diff except the link (name cut to 100 chars + suffix by Meta). Attach live rids cf140b34-5cb2-435a-8eb0-21e9fcc7df55 / b5719d61-ee5a-4e22-a410-abd04d802053 / 52ff73df-27b9-4122-8d4f-897fc2752615 (dry d60e87dc / 431582db / f6d4426c). Verify rids c279dd8c-5a45-44f5-88d9-2c75d27fd7bf / e4ce381c-888b-4061-b8bb-2fb58b9cbf60 / 7652beb7-a3af-4f87-9c5f-05ab68808de1: == new; ACTIVE, effective IN_PROCESS.'),
 '120252926433540058': ('Fixed', '1924555665195780',
  'Pre-read rid 0841f58a-8d37-440e-99bd-52bacdcbac99: slot == now (creative 1666258391533804). Exact copy with only this URL changed; deprecated DoF standard_enhancements (OPT_OUT) not sent. Create dry rid 346261e6-da1c-4aa9-a944-bbc0acde2114 (body == payload), live rid 605d1e68-71e5-4b4d-afe3-3067313ffeaa -> 1924555665195780; reads rid 4a86749d-348c-4640-ab8a-4e70a22db195 + 91dbeaed-0a81-4c0b-b638-d22e9d0171ae identical except URL, Meta DoF defaults (all OPT_OUT), name suffix. Attach dry rid 34267499-a00e-4ff4-8f23-701d23776d3e, live rid 2014628c-6854-499d-9442-b54bafa0b30f success. Verify rid 938a7855-132a-4064-8670-6de56f9550b7: == new; ad ACTIVE, effective IN_PROCESS (review).'),
}
SHARED = {'120251976401220058': 'SHARED_1421339153512972', '120251890583050058': 'SHARED_1421339153512972',
          '120253320140850058': 'SHARED_1632863468347851', '120253320140450058': 'SHARED_1632863468347851',
          '120253320135390058': 'SHARED_1632863468347851'}

def first_ad_read(ad):
    hits = find_calls('meta_ad_id_get', lambda i: str((i.get('path_params') or {}).get('ad_id')) == ad)
    return data_of(hits[0][2])

out = []
for u in units():
    ad = u['unit']
    key = SHARED.get(ad, ad)
    res, newid, det = DET[key]
    pre = first_ad_read(ad)['creative']
    post = last_ad_read(ad)['creative']
    for c in u['changes']:
        before = full_url(pre, c['slot'])
        after = full_url(post, c['slot'])
        # every change must match its recorded result
        if res == 'Fixed':
            assert (before == c['now'] or before in c['alt_now']) and after == c['new'], (ad, c['slot'])
        elif res == 'AlreadyFixed':
            assert same_url(before, c['new']) and after == before, (ad, c['slot'])
        out.append({'platform': 'meta', 'account_id': u['account_id'], 'unit_type': u['unit_type'], 'unit': ad,
                    'ad_ids': u['ad_ids'], 'ad_names': u['ad_names'], 'slot': c['slot'], 'before': before,
                    'after_expected': c['new'], 'after_live': after, 'result': res, 'new_entity_ids': newid,
                    'detail': det})
n = len(out)
from collections import Counter
print('changes', n, Counter(x['result'] for x in out), 'input changes', sum(len(u['changes']) for u in units()))
json.dump(out, sys.stdout if len(sys.argv) < 2 else open(sys.argv[1], 'w'), ensure_ascii=False)
