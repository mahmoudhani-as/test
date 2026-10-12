# Build exact ad/update payloads for in_tiktok_6.json from the live pre-read (pre_all.json).
import json, sys, unicodedata
from urllib.parse import urlsplit, parse_qsl
W='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/'
pre=json.load(open(W+'tt6_work/pre_all.json'))
inp=json.load(open(W+'in_tiktok_6.json'))
PIX='7347671240183693330'   # exact, pixel/list req 20261012215557605D74043B9DCE940E99 (Visit Diriyah - Base Pixel)
assert int(float(PIX))==int(float(7347671240183693000))
out={}; notes={}
for u in inp:
    a=pre[u['unit']]
    assert len(u['changes'])==1
    ch=u['changes'][0]; assert ch['slot']=='ad.landing_page_url'
    new=ch['new']
    sp=urlsplit(new); q=parse_qsl(sp.query, keep_blank_values=True)
    assert all(k.startswith('utm_') and k!='utm_id' for k,v in q) and len(set(k for k,v in q))==len(q)
    assert '%' not in sp.query and '+' not in sp.query and sp.fragment==''
    assert a['ad_id']==u['unit'] and a['advertiser_id']==u['account_id'] and a['ad_name']==u['ad_names'][0], u['unit']
    assert a['campaign_automation_type']=='MANUAL' and a['ad_format']=='SINGLE_VIDEO' and a['is_aco'] is False
    for k in ('card_id','page_id','music_id','impression_tracking_url','click_tracking_url','creative_type','ad_texts','carousel_image_labels','landing_page_urls','viewability_vast_url','brand_safety_vast_url'):
        assert a.get(k) in (None,''), (u['unit'],k,a.get(k))
    assert a.get('deeplink') in (None,'') and a.get('playable_url') in (None,'')
    assert a['viewability_postbid_partner']=='UNSET' and a['brand_safety_postbid_partner']=='UNSET'
    assert a.get('deeplink_type') in (None,'NORMAL')
    for k in ('vertical_video_strategy','fallback_type','dynamic_destination'):
        assert a.get(k) in (None,'UNSET'), (u['unit'],k,a.get(k))
    assert a.get('shopping_ads_fallback_type') in (None,'DEFAULT')
    assert not a.get('creative_auto_enhancement_strategy_list')
    tp=a.get('tracking_pixel_id')
    assert tp in (0,None) or int(tp)==7347671240183693000, tp
    it=a['identity_type']
    cr={"ad_id":a['ad_id'],"ad_name":a['ad_name'],"identity_id":a['identity_id'],"identity_type":it,"ad_format":a['ad_format']}
    if it=='CUSTOMIZED_USER':
        assert a['video_id'] and a['image_ids'] and not a.get('tiktok_item_id') and a.get('app_name') in ('',None)
        cr["video_id"]=a['video_id']; cr["image_ids"]=a['image_ids']; cr["ad_text"]=a['ad_text']
    elif it=='AUTH_CODE':
        assert a['tiktok_item_id'] and not a.get('video_id') and a['image_ids']==[]
        cr["tiktok_item_id"]=a['tiktok_item_id']
        cr["promotional_music_disabled"]=a['promotional_music_disabled']
        cr["ad_text"]=a['ad_text']
    else:
        raise SystemExit('unexpected identity '+it)
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
    cr["creative_authorized"]=a['creative_authorized']; cr["vast_moat_enabled"]=a['vast_moat_enabled']
    txt=a.get('ad_text') or ''
    notes[a['ad_id']]={"identity_type":it,"trailing_ws":txt!=txt.rstrip(),"leading_ws":txt!=txt.lstrip(),
        "nonprint":sorted({'U+%04X'%ord(c) for c in txt if unicodedata.category(c) in ('Cf','Cc','Zs','Mn') and c!=' '})}
    out[a['ad_id']]={"advertiser_id":u['account_id'],"adgroup_id":a['adgroup_id'],"creatives":[cr]}
json.dump(out,open(W+'tt6_work/payloads.json','w'),ensure_ascii=False,indent=1)
json.dump(notes,open(W+'tt6_work/notes.json','w'),ensure_ascii=False,indent=1)

def safe_dumps(o):
    s=json.dumps(o,ensure_ascii=False)
    r=[]
    for c in s:
        cat=unicodedata.category(c)
        if ord(c)>0xFFFF:
            v=ord(c)-0x10000; r.append('\\u%04x\\u%04x'%(0xD800+(v>>10),0xDC00+(v&0x3FF)))
        elif ord(c)>127 and (cat in ('Cf','Cc','Zs','Mn','Me','Co','Cs','So','Sk') or not cat.startswith('L')):
            r.append('\\u%04x'%ord(c))
        else:
            r.append(c)
    t=''.join(r)
    assert json.loads(t)==o
    return t
if len(sys.argv)>1:
    print(safe_dumps(out[sys.argv[1]]))
else:
    for k,v in out.items(): print(k, notes[k], sorted(v['creatives'][0].keys()))
