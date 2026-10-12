import json
from urllib.parse import urlsplit, parse_qsl
IN='../in_tiktok_10.json'
units={u['unit']:u for u in json.load(open(IN))}
pf=json.load(open('../../payloads/tiktok_spark_tt2_payloads.json'))
live={
 "1840143241069682": dict(ad_name="Bujairi Terrace_Tactical_Bujairi Terrace Summer 2025  Restaurants_LF_KSA_Prospecting_AR_Conversion_Altopiano",
   video_id="v10033g50000d1s9kh7og65mac3urupg", image_ids=["tos-alisg-p-0051c001-sg/oUebIGSTzZJmBgB4eUCOIifmAGLnDQAT8bGg6I"],
   ad_text="دفء إيطاليا يلتقي بأجواء مطل البجيري. تذوّقوا النكهات الريفية الأصيلة في ألتوبيانو", call_to_action_id="7537258537311947783"),
 "1840143241069666": dict(ad_name="Bujairi Terrace_Tactical_Bujairi Terrace Summer 2025  Restaurants_LF_KSA_Prospecting_AR_Conversion_longchim",
   video_id="v10033g50000d211govog65naec3sdlg", image_ids=["tos-alisg-p-0051c001-sg/o0C8bZHDNQpAHQFfueICzBDo8PWFEBjhBgBhGg"],
   ad_text="ينقل مطل البجيري نكهات شوارع بانكوك إلى قلب الدرعية مع لونغ تشِم—مطعم ينقل روح بانكوك بطبق.", call_to_action_id="7537227020175035400"),
}
out={}
for ad,v in live.items():
    new=units[ad]['changes'][0]['new']
    utm=[{"key":k,"value":val} for k,val in parse_qsl(urlsplit(new).query) if k.startswith('utm_')]
    assert all(k['key']!='utm_id' for k in utm)
    cr={"ad_id":ad,"ad_name":v['ad_name'],"identity_type":"BC_AUTH_TT","identity_id":"7d136a20-71e2-5fb6-9927-ad76b915fac7",
        "identity_authorized_bc_id":"6846326855419559942","ad_format":"SINGLE_VIDEO","video_id":v['video_id'],"image_ids":v['image_ids'],
        "ad_text":v['ad_text'],"call_to_action_id":v['call_to_action_id'],"landing_page_url":new,"utm_params":utm,
        "tracking_pixel_id":"7347671240183693330","dark_post_status":"ON","creative_authorized":True,"vast_moat_enabled":False}
    p={"advertiser_id":"7338057963233443842","adgroup_id":"1840143241067666","creatives":[cr]}
    if ad in pf:
        old=pf[ad]['creatives'][0]
        diffs={k:(old.get(k),cr.get(k)) for k in set(old)|set(cr) if old.get(k)!=cr.get(k)}
        print(ad,'diff vs tt2 payload keys:',sorted(diffs))
    print(ad, 'trailing space?', repr(v['ad_text'][-3:]))
    out[ad]=p
    print(json.dumps(p,ensure_ascii=True))
json.dump(out,open('spark_payloads.json','w'),ensure_ascii=False,indent=1)
