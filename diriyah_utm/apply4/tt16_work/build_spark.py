import json, sys
from urllib.parse import urlsplit, parse_qsl
W='/tmp/claude-0/-home-user-test/0a7a4347-50ae-5891-a613-ee320c5ab4bb/scratchpad/diriyah_utm/'
units={u['unit']:u for u in json.load(open(W+'apply4/in_tiktok_16.json'))}
tt2=json.load(open(W+'payloads/tiktok_spark_tt2_payloads.json'))
PIX="7347671240183693330"
# values as read live via ad/get req 20261012182049C6ABE9AA3798AB57BB20 (re-confirmed 202610121821258954989B4D1A102ABEDC)
live={
 "1840143241067698":{"adgroup_id":"1840143241067666","video_id":"v10033g50000d211govog65naec3sdlg","image_ids":["tos-alisg-p-0051c001-sg/o0C8bZHDNQpAHQFfueICzBDo8PWFEBjhBgBhGg"],
   "ad_text":"ينقل مطل البجيري نكهات تايلندية إلى قلب الدرعية مع لونغ تشِم، مطعم ينقل روح تايلاند بطبق","call_to_action_id":"7537227055633550344",
   "lp":"https://www.diriyah.sa/ar/dine?utm_source=tiktok&utm_medium=paid-social&utm_campaign=hs-bujairiterracesummer2025restaurants-2025-jul-lf-conversions&utm_id=5852&utm_term=bujairiterracesummer2025restaurants-ar-all-na&utm_content=longchim-video-aud",
   "text_src":"1839630361766065"},
 "1840143241067682":{"adgroup_id":"1840143241067666","video_id":"v10033g50000d211i2vog65okdjblb2g","image_ids":["tos-alisg-p-0051c001-sg/ogIcEo1DfBhAvgNsx1QA0FEBkMDGWgCMRfKLjQ"],
   "ad_text":"من نيويورك إلى مطل البجيري، يقدم سارابيث روح البرنش الأمريكي الكلاسيكي بأجواء لا تُنسى","call_to_action_id":"7537258496643910674",
   "lp":"https://www.diriyah.sa/ar/dine?utm_source=tiktok&utm_medium=paid-social&utm_campaign=hs-bujairiterracesummer2025restaurants-2025-jul-lf-conversions&utm_id=6092&utm_term=bujairiterracesummer2025restaurants-ar-all-na&utm_content=sarabeth-video-ret",
   "text_src":"1840143241067682"},
}
out={}
for aid,a in live.items():
    u=units[aid]; ch=u['changes'][0]
    assert ch['slot']=='ad.landing_page_url' and a['lp']==ch['now']
    new=ch['new']; q=parse_qsl(urlsplit(new).query, keep_blank_values=True)
    assert all(k.startswith('utm_') and k!='utm_id' for k,v in q) and len(set(k for k,v in q))==len(q)
    assert a['ad_text']==tt2[a['text_src']]['creatives'][0]['ad_text'] and a['ad_text']==a['ad_text'].strip()
    assert a['video_id']==tt2[a['text_src']]['creatives'][0]['video_id'] and a['image_ids']==tt2[a['text_src']]['creatives'][0]['image_ids']
    cr={"ad_id":aid,"ad_name":u['ad_names'][0],"identity_type":"BC_AUTH_TT","identity_id":"7d136a20-71e2-5fb6-9927-ad76b915fac7",
        "identity_authorized_bc_id":"6846326855419559942","ad_format":"SINGLE_VIDEO","video_id":a['video_id'],"image_ids":a['image_ids'],
        "ad_text":a['ad_text'],"call_to_action_id":a['call_to_action_id'],"landing_page_url":new,
        "utm_params":[{"key":k,"value":v} for k,v in q],"tracking_pixel_id":PIX,"dark_post_status":"ON","creative_authorized":True,"vast_moat_enabled":False}
    if aid in tt2:
        old=tt2[aid]['creatives'][0]
        print(aid,'diff vs tt2:',sorted(k for k in set(old)|set(cr) if old.get(k)!=cr.get(k)))
    out[aid]={"advertiser_id":u['account_id'],"adgroup_id":a['adgroup_id'],"creatives":[cr]}
json.dump(out,open('spark_payloads.json','w'),ensure_ascii=False,indent=1)
if len(sys.argv)>1: print(json.dumps(out[sys.argv[1]],ensure_ascii=False))
