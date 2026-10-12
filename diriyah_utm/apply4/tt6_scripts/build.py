import json, sys
from urllib.parse import urlsplit, parse_qsl
W='/tmp/claude-0/-home-user-test/0a7a4347-50ae-5891-a613-ee320c5ab4bb/scratchpad/diriyah_utm/apply4/'
d=json.loads(open(W+'tt6_work/pre_read_text.json').read())
lst=d['data']['data']['data']['list']
byid={a['ad_id']:a for a in lst}
inp=json.load(open(W+'in_tiktok_6.json'))
PIX="7347671240183693330"
out={}; notes={}
for u in inp:
    a=byid[u['unit']]; ch=u['changes'][0]
    assert len(u['changes'])==1 and ch['slot']=='ad.landing_page_url'
    new=ch['new']
    assert a['landing_page_url']==ch['now'] or a['landing_page_url'] in ch['alt_now'], u['unit']
    sp=urlsplit(new)
    q=parse_qsl(sp.query, keep_blank_values=True)
    assert all(k.startswith('utm_') and k!='utm_id' for k,v in q) and len(set(k for k,v in q))==len(q)
    assert '%' not in sp.query and '+' not in sp.query
    assert a['advertiser_id']==u['account_id'] and a['ad_name']==u['ad_names'][0] and a['ad_format']=='SINGLE_VIDEO'
    tp=a.get('tracking_pixel_id')
    assert tp in (0,None) or str(tp)=='7347671240183693000'
    for k in ('card_id','page_id','music_id','impression_tracking_url','click_tracking_url','creative_type','ad_texts','carousel_image_labels','landing_page_urls','viewability_vast_url','brand_safety_vast_url'):
        assert a.get(k) in (None,''), (k,a.get(k))
    assert a.get('deeplink') in (None,'') and a.get('playable_url')=='' 
    assert a['viewability_postbid_partner']=='UNSET' and a['brand_safety_postbid_partner']=='UNSET'
    assert a.get('deeplink_type') in (None,'NORMAL')
    for k in ('vertical_video_strategy','fallback_type','dynamic_destination'):
        assert a.get(k) in (None,'UNSET'), (k,a.get(k))
    assert a.get('shopping_ads_fallback_type') in (None,'DEFAULT')
    cr={"ad_id":a['ad_id'],"ad_name":a['ad_name'],"identity_id":a['identity_id'],"identity_type":a['identity_type'],"ad_format":a['ad_format']}
    it=a['identity_type']
    if it=='CUSTOMIZED_USER':
        assert a['video_id'] and a['image_ids'] and not a.get('tiktok_item_id')
        cr["video_id"]=a['video_id']; cr["image_ids"]=a['image_ids']; cr["ad_text"]=a['ad_text']
    elif it=='AUTH_CODE':
        assert a['tiktok_item_id'] and not a.get('video_id') and a['image_ids']==[] and a['ad_text']==''
        cr["tiktok_item_id"]=a['tiktok_item_id']
        cr["promotional_music_disabled"]=a['promotional_music_disabled']
    else:
        raise Exception(it)
    if a.get('call_to_action_id'):
        assert a.get('call_to_action') in (None,'')
        cr["call_to_action_id"]=a['call_to_action_id']
    else:
        assert a['call_to_action']
        cr["call_to_action"]=a['call_to_action']
    cr["landing_page_url"]=new
    cr["utm_params"]=[{"key":k,"value":v} for k,v in q]
    if tp not in (0,None):
        cr["tracking_pixel_id"]=PIX
    if it=='CUSTOMIZED_USER':
        cr["display_name"]=a['display_name']; cr["avatar_icon_web_uri"]=a['avatar_icon_web_uri']
        cr["aigc_disclosure_type"]=a['aigc_disclosure_type']
    if a.get('creative_auto_enhancement_strategy_list'):
        cr["creative_auto_enhancement_strategy_list"]=a['creative_auto_enhancement_strategy_list']
    cr["creative_authorized"]=a['creative_authorized']; cr["vast_moat_enabled"]=a['vast_moat_enabled']
    txt=a.get('ad_text') or ''
    notes[a['ad_id']]={"trailing_ws": txt!=txt.rstrip(), "leading_ws": txt!=txt.lstrip()}
    out[a['ad_id']]={"advertiser_id":u['account_id'],"adgroup_id":a["adgroup_id"],"creatives":[cr]}
json.dump(out,open(W+'tt6_work/payloads.json','w'),ensure_ascii=False,indent=1)
if len(sys.argv)>1:
    print(json.dumps(out[sys.argv[1]],ensure_ascii=False))
else:
    for k,v in out.items(): print(k, notes[k], sorted(v['creatives'][0].keys()))
