import json, sys
from urllib.parse import urlsplit, parse_qsl
d=json.load(open('pre_read_text.json'))
lst=d['data']['data']['data']['list']
byid={a['ad_id']:a for a in lst}
inp=json.load(open('../in_tiktok_12.json'))
PIX="7491594641231462418"
assert float(int(PIX))==float(7491594641231462000)
out={}
ALLOWED_DIFF=set()
for u in inp:
    a=byid[u['unit']]; ch=u['changes'][0]
    assert len(u['changes'])==1 and ch['slot']=='ad.landing_page_url'
    assert a['landing_page_url']==ch['now'], u['unit']
    new=ch['new']
    q=parse_qsl(urlsplit(new).query, keep_blank_values=True)
    assert all(k.startswith('utm_') and k!='utm_id' for k,v in q), q
    assert len(set(k for k,v in q))==len(q)
    assert a['identity_type']=='BC_AUTH_TT' and a['ad_format']=='CAROUSEL_ADS' and not a.get('tiktok_item_id') and not a.get('video_id')
    assert a['ad_text']==a['ad_text'].strip(), ('ws', u['unit'], repr(a['ad_text'][-3:]))
    for k in ('card_id','page_id','impression_tracking_url','click_tracking_url','creative_type','ad_texts','carousel_image_labels','landing_page_urls'):
        assert a.get(k) in (None,''), (k,a.get(k))
    assert a['deeplink']=='' and a['playable_url']=='' and a['avatar_icon_web_uri']==''
    cr={"ad_id":a['ad_id'],"ad_name":a['ad_name'],
        "identity_type":a['identity_type'],"identity_id":a['identity_id'],"identity_authorized_bc_id":a['identity_authorized_bc_id'],
        "ad_format":a['ad_format'],"image_ids":a['image_ids'],"music_id":a['music_id'],"ad_text":a['ad_text']}
    if a.get('call_to_action_id'):
        cr['call_to_action_id']=a['call_to_action_id']
    else:
        cr['call_to_action']=a['call_to_action']
    cr['landing_page_url']=new
    cr['utm_params']=[{"key":k,"value":v} for k,v in q]
    cr['dark_post_status']=a['dark_post_status']
    if a.get('creative_auto_enhancement_strategy_list'):
        cr['creative_auto_enhancement_strategy_list']=a['creative_auto_enhancement_strategy_list']
    cr['creative_authorized']=a['creative_authorized']
    cr['vast_moat_enabled']=a['vast_moat_enabled']
    pix=a.get('tracking_pixel_id')
    if pix not in (None,0,'0'):
        assert pix==7491594641231462000
        cr['tracking_pixel_id']=PIX
    out[a['ad_id']]={"advertiser_id":u['account_id'],"adgroup_id":a['adgroup_id'],"creatives":[cr]}
json.dump(out,open('payloads.json','w'),ensure_ascii=False,indent=1)
if len(sys.argv)>1:
    print(json.dumps(out[sys.argv[1]],ensure_ascii=False))
else:
    for k,v in out.items():
        c=v['creatives'][0]; print(k, c['ad_name'], 'pix' if 'tracking_pixel_id' in c else '-', 'cta_id' if 'call_to_action_id' in c else 'cta', 'enh' if 'creative_auto_enhancement_strategy_list' in c else '-', len(c['utm_params']), [p['key'] for p in c['utm_params']])
