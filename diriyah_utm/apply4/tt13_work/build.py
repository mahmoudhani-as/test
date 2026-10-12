import json, sys
from urllib.parse import urlsplit, parse_qsl
d=json.loads(open('pre_read_text.json').read())
lst=d['data']['data']['data']['list']
byid={a['ad_id']:a for a in lst}
inp=json.load(open('../in_tiktok_13.json'))
PIX="7347671240183693330"
out={}
for u in inp:
    a=byid[u['unit']]; ch=u['changes'][0]; new=ch['new']
    assert a['landing_page_url']==ch['now']
    q=parse_qsl(urlsplit(new).query, keep_blank_values=True)
    assert all(k.startswith('utm_') and k!='utm_id' for k,v in q) and len(q)==5
    assert a['identity_type']=='BC_AUTH_TT' and a['ad_format']=='CAROUSEL_ADS' and a.get('video_id') is None and a.get('tiktok_item_id') is None
    assert a.get('call_to_action_id') is None and a.get('card_id') is None and a.get('page_id') is None and a.get('deeplink')=='' 
    assert a.get('impression_tracking_url') is None and a.get('click_tracking_url') is None and a.get('playable_url')==''
    assert a['ad_text']==a['ad_text'].strip()
    cr={"ad_id":a['ad_id'],"ad_name":a['ad_name'],
        "identity_type":a['identity_type'],"identity_id":a['identity_id'],"identity_authorized_bc_id":a['identity_authorized_bc_id'],
        "ad_format":a['ad_format'],"image_ids":a['image_ids'],"music_id":a['music_id'],
        "ad_text":a['ad_text'],"call_to_action":a['call_to_action'],
        "landing_page_url":new}
    if a.get('utm_params'):
        cr["utm_params"]=[{"key":k,"value":v} for k,v in q]
    tp=a.get('tracking_pixel_id')
    if tp not in (None,0):
        assert float(tp)==float(int(PIX)); cr["tracking_pixel_id"]=PIX
    cr["dark_post_status"]=a['dark_post_status']
    if a.get('creative_auto_enhancement_strategy_list'):
        cr["creative_auto_enhancement_strategy_list"]=a['creative_auto_enhancement_strategy_list']
    cr["creative_authorized"]=a['creative_authorized']; cr["vast_moat_enabled"]=a['vast_moat_enabled']
    out[a['ad_id']]={"advertiser_id":u['account_id'],"adgroup_id":a['adgroup_id'],"creatives":[cr]}
json.dump(out,open('payloads.json','w'),ensure_ascii=False,indent=1)
if len(sys.argv)>1:
    print(json.dumps(out[sys.argv[1]],ensure_ascii=False))
else:
    for k,v in out.items(): print(k, sorted(v['creatives'][0].keys()))
