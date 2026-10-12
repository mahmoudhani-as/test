import json, sys
from urllib.parse import urlsplit, parse_qsl
W='/tmp/claude-0/-home-user-test/0a7a4347-50ae-5891-a613-ee320c5ab4bb/scratchpad/diriyah_utm/apply4/tt8_work'
d=json.loads(open(W+'/pre_read_text.json').read())
lst=d['data']['data']['data']['list']
byid={a['ad_id']:a for a in lst}
inp=json.load(open(W+'/../in_tiktok_8.json'))
out={}
for u in inp:
    a=byid[u['unit']]; ch=u['changes'][0]
    assert len(u['changes'])==1 and ch['slot']=='ad.landing_page_url'
    assert a['landing_page_url']==ch['now'], u['unit']
    new=ch['new']
    q=parse_qsl(urlsplit(new).query, keep_blank_values=True)
    assert all(k!='utm_id' for k,v in q) and len(set(k for k,v in q))==len(q)
    assert a['call_to_action_id'] in (None,'') and a.get('music_id') in (None,'') and a.get('card_id') in (None,'') and a.get('page_id') in (None,'',0)
    assert a.get('deeplink','')=='' and a.get('impression_tracking_url') in (None,'') and a.get('click_tracking_url') in (None,'') and a.get('playable_url','')==''
    assert a.get('tracking_pixel_id') in (None,0,'0')
    assert a.get('ad_texts') in (None,[])
    assert a.get('viewability_postbid_partner')=='UNSET' and a.get('brand_safety_postbid_partner')=='UNSET'
    assert a['campaign_automation_type']=='MANUAL' and a['ad_format']=='SINGLE_VIDEO'
    assert a['creative_type'] is None and a['deeplink_type']=='NORMAL'
    it=a['identity_type']
    utm=[{"key":k,"value":v} for k,v in q]
    cr={"ad_id":a['ad_id'],"ad_name":a['ad_name'],"identity_id":a['identity_id'],"identity_type":it,"ad_format":a['ad_format']}
    if it=='CUSTOMIZED_USER':
        assert a['video_id'] and a['image_ids'] and a['identity_id']=='7350277519361425409'
        cr.update({"video_id":a['video_id'],"image_ids":a['image_ids'],"ad_text":a['ad_text'],"call_to_action":a['call_to_action'],
                   "landing_page_url":new,"utm_params":utm,
                   "display_name":a['display_name'],"avatar_icon_web_uri":a['avatar_icon_web_uri'],
                   "aigc_disclosure_type":a['aigc_disclosure_type'],"creative_authorized":a['creative_authorized'],"vast_moat_enabled":a['vast_moat_enabled']})
    elif it=='BC_AUTH_TT':
        assert a['video_id'] and a['image_ids'] and a['identity_authorized_bc_id']=='6846326855419559942' and a['identity_id']=='7d136a20-71e2-5fb6-9927-ad76b915fac7'
        cr.update({"identity_authorized_bc_id":a['identity_authorized_bc_id'],"video_id":a['video_id'],"image_ids":a['image_ids'],"ad_text":a['ad_text'],
                   "call_to_action":a['call_to_action'],"landing_page_url":new,"utm_params":utm,
                   "dark_post_status":a['dark_post_status'],"creative_authorized":a['creative_authorized'],"vast_moat_enabled":a['vast_moat_enabled']})
    else:
        raise SystemExit('unexpected identity '+it)
    if a.get('creative_auto_enhancement_strategy_list'):
        cr['creative_auto_enhancement_strategy_list']=a['creative_auto_enhancement_strategy_list']
    out[a['ad_id']]={"advertiser_id":u['account_id'],"adgroup_id":a['adgroup_id'],"creatives":[cr]}
json.dump(out,open(W+'/payloads.json','w'),ensure_ascii=False,indent=1)
if len(sys.argv)>1:
    print(json.dumps(out[sys.argv[1]],ensure_ascii=False))
else:
    print(len(out),'payloads built')
