import json, sys
from urllib.parse import urlsplit, parse_qsl
d=json.loads(open('pre_read_text.json').read())
lst=d['data']['data']['data']['list']
byid={a['ad_id']:a for a in lst}
inp=json.load(open('../in_tiktok_7.json'))
out={}
notes={}
UPD_FIELDS=set("ad_name identity_id identity_type identity_authorized_bc_id ad_format video_id image_ids music_id tiktok_item_id promotional_music_disabled item_duet_status item_stitch_status dark_post_status ad_text ad_texts call_to_action call_to_action_id card_id landing_page_url utm_params page_id deeplink deeplink_type aigc_disclosure_type tracking_pixel_id tracking_app_id vast_moat_enabled viewability_postbid_partner brand_safety_postbid_partner impression_tracking_url click_tracking_url video_view_tracking_url playable_url creative_type app_name display_name avatar_icon_web_uri creative_authorized".split())
for u in inp:
    a=byid[u['unit']]; ch=u['changes'][0]
    new=ch['new']
    q=parse_qsl(urlsplit(new).query, keep_blank_values=True)
    assert all(k!='utm_id' for k,v in q) and len(set(k for k,v in q))==len(q)
    # guard: fields we do not send must be empty / default
    assert a['call_to_action_id'] in (None,'') and a.get('music_id') in (None,'') and a.get('card_id') in (None,'') and a.get('page_id') in (None,'',0)
    assert a.get('deeplink','')=='' and a.get('impression_tracking_url') in (None,'') and a.get('click_tracking_url') in (None,'') and a.get('playable_url','')==''
    assert a.get('tracking_pixel_id') in (None,0,'0'), a.get('tracking_pixel_id')
    assert a.get('ad_texts') in (None,[])
    assert a.get('viewability_postbid_partner')=='UNSET' and a.get('brand_safety_postbid_partner')=='UNSET'
    assert a['campaign_automation_type']=='MANUAL'
    it=a['identity_type']
    cr={"ad_id":a['ad_id'],"ad_name":a['ad_name'],"identity_id":a['identity_id'],"identity_type":it,"ad_format":a['ad_format']}
    if it=='CUSTOMIZED_USER':
        cr.update({"video_id":a['video_id'],"image_ids":a['image_ids'],"ad_text":a['ad_text'],"call_to_action":a['call_to_action'],
                   "landing_page_url":new,"utm_params":[{"key":k,"value":v} for k,v in q],
                   "display_name":a['display_name'],"avatar_icon_web_uri":a['avatar_icon_web_uri'],
                   "aigc_disclosure_type":a['aigc_disclosure_type'],"creative_authorized":a['creative_authorized'],"vast_moat_enabled":a['vast_moat_enabled']})
        assert a['video_id'] and a['image_ids']
    elif it=='BC_AUTH_TT':
        cr.update({"identity_authorized_bc_id":a['identity_authorized_bc_id'],"video_id":a['video_id'],"image_ids":a['image_ids'],"ad_text":a['ad_text'],
                   "call_to_action":a['call_to_action'],"landing_page_url":new,"utm_params":[{"key":k,"value":v} for k,v in q],
                   "dark_post_status":a['dark_post_status'],"creative_authorized":a['creative_authorized'],"vast_moat_enabled":a['vast_moat_enabled']})
        assert a['video_id'] and a['image_ids'] and a['identity_authorized_bc_id']=='6846326855419559942' and a['identity_id']=='7d136a20-71e2-5fb6-9927-ad76b915fac7'
    elif it=='AUTH_CODE':
        assert not a['video_id'] and not a['image_ids'] and a['ad_text']==''
        cr.update({"tiktok_item_id":a['tiktok_item_id'],"call_to_action":a['call_to_action'],"landing_page_url":new,
                   "utm_params":[{"key":k,"value":v} for k,v in q],"promotional_music_disabled":a['promotional_music_disabled'],
                   "creative_authorized":a['creative_authorized'],"vast_moat_enabled":a['vast_moat_enabled']})
    else:
        raise SystemExit('unexpected identity '+it)
    ts = a['ad_text'] is not None and a['ad_text']!=a['ad_text'].rstrip()
    notes[a['ad_id']]={"trailing_ws":ts,"identity_type":it}
    out[a['ad_id']]={"advertiser_id":u['account_id'],"adgroup_id":a['adgroup_id'],"creatives":[cr]}
json.dump(out,open('payloads.json','w'),ensure_ascii=False,indent=1)
json.dump(notes,open('notes.json','w'),indent=1)
if len(sys.argv)>1:
    print(json.dumps(out[sys.argv[1]],ensure_ascii=False))
else:
    for k,v in notes.items(): print(k,v)
