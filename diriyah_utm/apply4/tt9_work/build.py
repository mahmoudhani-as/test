import json, sys
from urllib.parse import urlsplit, parse_qsl
W='/tmp/claude-0/-home-user-test/0a7a4347-50ae-5891-a613-ee320c5ab4bb/scratchpad/diriyah_utm/apply4/'
d=json.loads(open(W+'tt9_work/pre_read_text.json').read())
lst=d['data']['data']['data']['list']
byid={a['ad_id']:a for a in lst}
inp=json.load(open(W+'in_tiktok_9.json'))
PIX='7347671240183693330'  # exact, from pixel/list req 20261012181100A71FC271E0316D92CA48
out={}; notes={}
for u in inp:
    a=byid[u['unit']]; ch=u['changes'][0]; new=ch['new']
    assert a['landing_page_url']==ch['now']
    q=parse_qsl(urlsplit(new).query, keep_blank_values=True)
    assert all(k!='utm_id' for k,v in q) and len(set(k for k,v in q))==len(q)
    assert a.get('music_id') in (None,'') and a.get('card_id') in (None,'') and a.get('page_id') in (None,'',0)
    assert a.get('deeplink','')=='' and a.get('impression_tracking_url') in (None,'') and a.get('click_tracking_url') in (None,'') and a.get('playable_url','')==''
    assert a.get('ad_texts') in (None,[]) and a['viewability_postbid_partner']=='UNSET' and a['brand_safety_postbid_partner']=='UNSET'
    assert a['campaign_automation_type']=='MANUAL' and a['ad_format']=='SINGLE_VIDEO'
    pix=a.get('tracking_pixel_id')
    assert pix in (0,7347671240183693000), pix
    it=a['identity_type']
    cr={"ad_id":a['ad_id'],"ad_name":a['ad_name'],"identity_id":a['identity_id'],"identity_type":it,"ad_format":a['ad_format']}
    if it=='CUSTOMIZED_USER':
        assert a['video_id'] and a['image_ids']
        cr.update({"video_id":a['video_id'],"image_ids":a['image_ids'],"ad_text":a['ad_text']})
        if a.get('call_to_action_id'): cr["call_to_action_id"]=a['call_to_action_id']
        if a.get('call_to_action'): cr["call_to_action"]=a['call_to_action']
        cr.update({"landing_page_url":new,"utm_params":[{"key":k,"value":v} for k,v in q],
                   "display_name":a['display_name'],"avatar_icon_web_uri":a['avatar_icon_web_uri'],
                   "aigc_disclosure_type":a['aigc_disclosure_type'],"creative_authorized":a['creative_authorized'],"vast_moat_enabled":a['vast_moat_enabled']})
    elif it=='AUTH_CODE':
        assert not a['video_id'] and not a['image_ids'] and a['ad_text']==''
        cr.update({"tiktok_item_id":a['tiktok_item_id']})
        if a.get('call_to_action_id'): cr["call_to_action_id"]=a['call_to_action_id']
        if a.get('call_to_action'): cr["call_to_action"]=a['call_to_action']
        cr.update({"landing_page_url":new,"utm_params":[{"key":k,"value":v} for k,v in q],
                   "promotional_music_disabled":a['promotional_music_disabled'],
                   "creative_authorized":a['creative_authorized'],"vast_moat_enabled":a['vast_moat_enabled']})
    else:
        raise SystemExit('unexpected identity '+it)
    if pix: cr["tracking_pixel_id"]=PIX
    ts = a['ad_text']!=a['ad_text'].rstrip()
    notes[a['ad_id']]={"trailing_ws":ts,"identity_type":it,"ad_text_repr_tail":repr(a['ad_text'][-6:])}
    out[a['ad_id']]={"advertiser_id":u['account_id'],"adgroup_id":a['adgroup_id'],"creatives":[cr]}
json.dump(out,open(W+'tt9_work/payloads.json','w'),ensure_ascii=False,indent=1)
json.dump(notes,open(W+'tt9_work/notes.json','w'),indent=1,ensure_ascii=False)
if len(sys.argv)>1:
    print(json.dumps(out[sys.argv[1]],ensure_ascii=False))
else:
    for k,v in notes.items(): print(k,v)
