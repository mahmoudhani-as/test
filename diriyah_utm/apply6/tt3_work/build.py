# Build exact ad/update payloads for the writable CUSTOMIZED_USER ads of in_tiktok_3.json from the live pre-read.
import json, sys, unicodedata
from urllib.parse import urlsplit, parse_qsl
W='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/'
pre=json.load(open(W+'tt3_work/pre_all.json'))['pre']
cls=json.load(open(W+'tt3_work/classes.json'))
inp=json.load(open(W+'in_tiktok_3.json'))
PIX='7347671240183693330'   # exact, pixel/list req 202610122211045CADADFD1529D9BD7B37 (Visit Diriyah - Base Pixel)
assert float(PIX)==float(7347671240183693000) and float('7610705877289091089')!=float(7347671240183693000)
out={}; notes={}
for u in inp:
    c=cls[u['unit']]
    if not (c['state']=='writable' and c['kind']=='CUSTOMIZED_USER'): continue
    a=pre[u['unit']]
    ch=u['changes'][0]; assert ch['slot']=='ad.landing_page_url'
    assert a['landing_page_url']==ch['now']
    new=ch['new']
    sp=urlsplit(new); q=parse_qsl(sp.query, keep_blank_values=True)
    assert all(k.startswith('utm_') and k!='utm_id' for k,v in q) and len(set(k for k,v in q))==len(q)
    assert '%' not in sp.query and '+' not in sp.query and sp.fragment==''
    assert a['ad_id']==u['unit'] and a['advertiser_id']==u['account_id'] and a['ad_name']==u['ad_names'][0], u['unit']
    assert a['campaign_automation_type']=='MANUAL' and a['ad_format']=='SINGLE_VIDEO' and a['is_aco'] is False
    for k in ('card_id','page_id','music_id','impression_tracking_url','click_tracking_url','creative_type','ad_texts','carousel_image_labels','landing_page_urls','viewability_vast_url','brand_safety_vast_url','tiktok_item_id','call_to_action_id'):
        assert a.get(k) in (None,''), (u['unit'],k,a.get(k))
    assert a.get('deeplink') in (None,'') and a.get('playable_url') in (None,'') and a.get('app_name') in (None,'')
    assert a['viewability_postbid_partner']=='UNSET' and a['brand_safety_postbid_partner']=='UNSET'
    assert a.get('deeplink_type') in (None,'NORMAL')
    for k in ('vertical_video_strategy','fallback_type','dynamic_destination','dark_post_status','identity_authorized_bc_id','shopping_ads_fallback_type','ad_ref_pixel_id','branded_content_disabled'):
        assert k not in a, (u['unit'],k,a.get(k))
    assert not a.get('creative_auto_enhancement_strategy_list')
    tp=a.get('tracking_pixel_id')
    assert tp==7347671240183693000, tp
    assert a['identity_type']=='CUSTOMIZED_USER' and a['video_id'] and len(a['image_ids'])==1 and a['call_to_action']
    cr={"ad_id":a['ad_id'],"ad_name":a['ad_name'],"identity_id":a['identity_id'],"identity_type":a['identity_type'],"ad_format":a['ad_format'],
        "video_id":a['video_id'],"image_ids":a['image_ids'],"ad_text":a['ad_text'],
        "display_name":a['display_name'],"avatar_icon_web_uri":a['avatar_icon_web_uri'],"aigc_disclosure_type":a['aigc_disclosure_type'],
        "creative_authorized":a['creative_authorized'],"vast_moat_enabled":a['vast_moat_enabled'],
        "call_to_action":a['call_to_action'],
        "landing_page_url":new,
        "utm_params":[{"key":k,"value":v} for k,v in q],
        "tracking_pixel_id":PIX}
    txt=a.get('ad_text') or ''
    notes[a['ad_id']]={"trailing_ws":txt!=txt.rstrip(),"leading_ws":txt!=txt.lstrip(),
        "nonascii":sorted({'U+%04X %s'%(ord(ch_),unicodedata.category(ch_)) for ch_ in txt if ord(ch_)>127 and not unicodedata.category(ch_).startswith('L')}),
        "old_utm":[(x['key'],x['value']) for x in a.get('utm_params') or []]}
    out[a['ad_id']]={"advertiser_id":u['account_id'],"adgroup_id":a['adgroup_id'],"creatives":[cr]}
json.dump(out,open(W+'tt3_work/payloads.json','w'),ensure_ascii=False,indent=1)
json.dump(notes,open(W+'tt3_work/notes.json','w'),ensure_ascii=False,indent=1)
if len(sys.argv)>1:
    print(json.dumps(out[sys.argv[1]],ensure_ascii=False))
else:
    for k,v in out.items(): print(k, notes[k]['trailing_ws'], notes[k]['nonascii'], sorted(v['creatives'][0].keys()))
