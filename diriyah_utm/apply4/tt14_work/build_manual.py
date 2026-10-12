import json
from urllib.parse import urlsplit, parse_qsl
units={u['unit']:u for u in json.load(open('../in_tiktok_14.json'))}
d13=json.loads(open('../tt13_work/pre_read_text.json').read())
t13={a['ad_id']:a for a in d13['data']['data']['data']['list']}
AR="منازل الحداوي مكانٌ للعائلات لتتخذ من الدرعية موطناً، حيث يلتقي التراث بأسلوب الحياة المعاصر."
EN="Manazel AlHadawi, a place for families to call home in Diriyah, where heritage shapes modern living."
assert AR==t13['1866981047368769']['ad_text'], 'AR text mismatch vs tt13 raw'
assert EN==t13['1866981055202898']['ad_text'], 'EN text mismatch vs tt13 raw'
# live read req 2026101218003163F10F909FC314CA1CD7
live={
 "1866981029062146":dict(adgroup_id="1866980899041010",ad_name="Manazel_KV1_AR_Awareness",image_ids=["ad-site-i18n-sg/20260607c7c70136b1c84e2d4d7080f7"],ad_text=AR,
   lp="https://www.diriyahcompany.sa/ar/diriyah-living/alhadawi?utm_source=tiktok&utm_medium=paid-social&utm_campaign=ManazelAlHadawi_Jun2026&utm_term=adset-id-BA26CB_manazel-alhadawi_ar_all_mf_prospecting&utm_content=ad-id-D8EEBF_manazel-alhadawi-kv1_display"),
 "1866981015440609":dict(adgroup_id="1866980896932194",ad_name="Manazel_KV1_EN_Awareness",image_ids=["ad-site-i18n-sg/20260607c7c7f63609f0782b4be9a3b4"],ad_text=EN,
   lp="https://www.diriyahcompany.sa/en/diriyah-living/alhadawi?utm_source=tiktok&utm_medium=paid-social&utm_campaign=ManazelAlHadawi_Jun2026&utm_term=adset-id-0DE601_manazel-alhadawi_en_all_mf_prospecting&utm_content=ad-id-A62772_manazel-alhadawi-kv1_display"),
}
out={}
for ad,v in live.items():
    u=units[ad]; ch=u['changes'][0]
    assert u['ad_names'][0]==v['ad_name']
    assert v['lp']==ch['now'], 'not now'
    new=ch['new']
    q=parse_qsl(urlsplit(new).query, keep_blank_values=True)
    assert all(k.startswith('utm_') and k!='utm_id' for k,_ in q)
    cr={"ad_id":ad,"ad_name":v['ad_name'],"identity_type":"BC_AUTH_TT","identity_id":"0f6eebaa-ba16-5ad3-aa97-4171805e2af1",
        "identity_authorized_bc_id":"6807778858780065797","ad_format":"CAROUSEL_ADS","image_ids":v['image_ids'],"music_id":"7647465303001156353",
        "ad_text":v['ad_text'],"call_to_action":"BOOK_NOW","landing_page_url":new,"dark_post_status":"ON","creative_authorized":False,"vast_moat_enabled":False}
    out[ad]={"advertiser_id":"7338074303931449345","adgroup_id":v['adgroup_id'],"creatives":[cr]}
    print(ad); print(json.dumps(out[ad],ensure_ascii=False))
json.dump(out,open('manual_payloads.json','w'),ensure_ascii=False,indent=1)
