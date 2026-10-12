import json, sys
from urllib.parse import urlsplit, parse_qsl
W='/tmp/claude-0/-home-user-test/0a7a4347-50ae-5891-a613-ee320c5ab4bb/scratchpad/diriyah_utm/apply4/'
d=json.loads(open(W+'tt17_work/pre_read_text.json').read())
byid={a['ad_id']:a for a in d['data']['data']['data']['list']}
inp=json.load(open(W+'in_tiktok_17.json'))
pf=json.load(open(W+'../payloads/tiktok_spark_tt2_payloads.json'))
PIX="7347671240183693330"
out={}; notes={}
for u in inp:
    a=byid[u['unit']]; ch=u['changes'][0]
    assert len(u['changes'])==1 and ch['slot']=='ad.landing_page_url'
    new=ch['new']
    assert a['landing_page_url']==ch['now'] or a['landing_page_url'] in ch['alt_now'], u['unit']
    sp=urlsplit(new); q=parse_qsl(sp.query, keep_blank_values=True)
    assert all(k.startswith('utm_') and k!='utm_id' for k,v in q) and len(set(k for k,v in q))==len(q)
    assert '%' not in sp.query and '+' not in sp.query
    assert a['advertiser_id']==u['account_id'] and a['ad_name']==u['ad_names'][0] and a['ad_format']=='SINGLE_VIDEO'
    assert a['identity_type']=='BC_AUTH_TT' and a['video_id'] and a['image_ids']
    tp=a.get('tracking_pixel_id')
    assert tp in (0,None) or str(tp)=='7347671240183693000'
    for k in ('card_id','page_id','music_id','impression_tracking_url','click_tracking_url','creative_type','ad_texts','carousel_image_labels','landing_page_urls','viewability_vast_url','brand_safety_vast_url'):
        assert a.get(k) in (None,''), (k,a.get(k))
    assert a.get('deeplink') in (None,'') and a.get('playable_url')==''
    assert a['viewability_postbid_partner']=='UNSET' and a.get('brand_safety_postbid_partner') in (None,'UNSET')
    assert a.get('deeplink_type') in (None,'NORMAL')
    for k in ('vertical_video_strategy','fallback_type','dynamic_destination'):
        assert a.get(k) in (None,'UNSET'), (k,a.get(k))
    assert a.get('shopping_ads_fallback_type') in (None,'DEFAULT')
    assert a.get('creative_auto_enhancement_strategy_list') in (None,[])
    cr={"ad_id":a['ad_id'],"ad_name":a['ad_name'],"identity_type":a['identity_type'],"identity_id":a['identity_id'],
        "identity_authorized_bc_id":a['identity_authorized_bc_id'],"ad_format":a['ad_format'],
        "video_id":a['video_id'],"image_ids":a['image_ids'],"ad_text":a['ad_text']}
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
    cr["dark_post_status"]=a['dark_post_status']
    cr["creative_authorized"]=a['creative_authorized']; cr["vast_moat_enabled"]=a['vast_moat_enabled']
    txt=a['ad_text']
    notes[a['ad_id']]={"trailing_ws": txt!=txt.rstrip(), "leading_ws": txt!=txt.lstrip()}
    if a['ad_id'] in pf:
        old=pf[a['ad_id']]['creatives'][0]
        notes[a['ad_id']]['tt2_diff']=sorted(k for k in set(old)|set(cr) if old.get(k)!=cr.get(k))
        assert pf[a['ad_id']]['adgroup_id']==a['adgroup_id']
    out[a['ad_id']]={"advertiser_id":u['account_id'],"adgroup_id":a["adgroup_id"],"creatives":[cr]}
json.dump(out,open(W+'tt17_work/payloads.json','w'),ensure_ascii=False,indent=1)
json.dump(notes,open(W+'tt17_work/notes.json','w'),ensure_ascii=False,indent=1)
if len(sys.argv)>1:
    print(json.dumps(out[sys.argv[1]],ensure_ascii=False))
else:
    for k,v in out.items(): print(k, notes[k], sorted(v['creatives'][0].keys()))
