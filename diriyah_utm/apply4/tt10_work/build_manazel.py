import json
from urllib.parse import urlsplit, parse_qsl
units={u['unit']:u for u in json.load(open('../in_tiktok_10.json'))}
EN_TXT="Own a home in Diriyah, where heritage, community and everyday life come together."
live={
 "1875518266298689": dict(adgroup_id="1866980923591713", ad_name="ManazelAlHadawi_CR3_EN", cta="7682124967667878933", ad_text=EN_TXT,
   image_ids=["ad-site-i18n-sg/202609025d0d1bf383737681411ab77e","ad-site-i18n-sg/202609025d0dcc9b8ad13bc446739b71","ad-site-i18n-sg/202609025d0d2934adec124842b5840b","ad-site-i18n-sg/202609025d0da59c613770e542268d6c","ad-site-i18n-sg/202608305d0d0c64f2d3e8194da18a33"]),
 "1875517732804737": dict(adgroup_id="1866980923591713", ad_name="ManazelAlHadawi_CR2_EN", cta="7682123011272543252", ad_text=EN_TXT,
   image_ids=["ad-site-i18n-sg/202609025d0d25bb51a095844fae87fc","ad-site-i18n-sg/202609025d0dcc9b8ad13bc446739b71","ad-site-i18n-sg/202609025d0dc77176fb8c784ed88ffd","ad-site-i18n-sg/202609025d0d03c374aa645f4f85ad0a","ad-site-i18n-sg/202608305d0d2d1e26f398f94384a804"]),
 "1875517614095538": dict(adgroup_id="1866980923591713", ad_name="Manazel AlHadawi_KV3_EN", cta="7682120606724148244",
   ad_text="Manazel AlHadawi, a place for families to call home in Diriyah, where heritage shapes modern living.",
   image_ids=["ad-site-i18n-sg/202608305d0dd538352b7bae47cea145"]),
 "1875517253114161": dict(adgroup_id="1866980925443409", ad_name="ManazelAlHadawi_CR3_AR", cta="7682119848196983829",
   ad_text="امتلك منزلاً في الدرعية، حيث يلتقي التراث بالمجتمع والحياة اليومية.",
   image_ids=["ad-site-i18n-sg/202609025d0d3cde74034eb14358ae83","ad-site-i18n-sg/202609025d0d61b1be44d8db447ebd2a","ad-site-i18n-sg/202608305d0d235b4a95fc7340948590","ad-site-i18n-sg/202609025d0d678e4937b2124fe6ad9a","ad-site-i18n-sg/202609025d0da52b3185dfe845a0b8c9"]),
 "1875516837301810": dict(adgroup_id="1866980925443409", ad_name="ManazelAlHadawi_CR2_AR", cta="7682118812627373077",
   ad_text="امتلك منزلاً في الدرعية، حيث يلتقي التراث بالمجتمع والحياة اليومية.",
   image_ids=["ad-site-i18n-sg/202608305d0d25c7ad37068a4806a832","ad-site-i18n-sg/202608305d0d2e9a597b338249ed8d33","ad-site-i18n-sg/202608305d0d8ec9c229cf924a7db585","ad-site-i18n-sg/202608305d0d6a09071de91c43f89862","ad-site-i18n-sg/202608305d0d68c4ed16cdf246f998b2"]),
 "1875516626259026": dict(adgroup_id="1866980925443409", ad_name="Manaze AlHadawi_KV3_AR", cta="7682117134457130005",
   ad_text="منازل الحداوي مكانٌ للعائلات لتتخذ من الدرعية موطناً، حيث يلتقي التراث بأسلوب الحياة المعاصر.",
   image_ids=["ad-site-i18n-sg/202609025d0d8dcaf84052da41ea9a8b"]),
}
out={}
for ad,v in live.items():
    u=units[ad]; assert u['ad_names'][0]==v['ad_name'], (u['ad_names'],v['ad_name'])
    new=u['changes'][0]['new']
    utm=[{"key":k,"value":val} for k,val in parse_qsl(urlsplit(new).query) if k.startswith('utm_')]
    assert len(utm)==len(parse_qsl(urlsplit(new).query)) and all(x['key']!='utm_id' for x in utm)
    cr={"ad_id":ad,"ad_name":v['ad_name'],"identity_type":"BC_AUTH_TT","identity_id":"0f6eebaa-ba16-5ad3-aa97-4171805e2af1",
        "identity_authorized_bc_id":"6807778858780065797","ad_format":"CAROUSEL_ADS","image_ids":v['image_ids'],"music_id":"7647465303001156353",
        "ad_text":v['ad_text'],"call_to_action_id":v['cta'],"landing_page_url":new,"utm_params":utm,
        "dark_post_status":"ON","creative_auto_enhancement_strategy_list":["IMAGE_QUALITY","IMAGE_RESIZE"],"creative_authorized":False,"vast_moat_enabled":False}
    p={"advertiser_id":"7338074303931449345","adgroup_id":v['adgroup_id'],"creatives":[cr]}
    out[ad]=p
    print(ad, repr(v['ad_text'][-2:]))
    print(json.dumps(p,ensure_ascii=True))
json.dump(out,open('manazel_payloads.json','w'),ensure_ascii=False,indent=1)
