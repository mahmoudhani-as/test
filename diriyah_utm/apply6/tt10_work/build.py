# Build exact /v1.3/ad/update/ payloads for the BC_AUTH_TT carousel ads (no tiktok_item_id) of in_tiktok_10.json
# from the live pre-read (pre_all.json). Spark Push ads (BC_AUTH_TT + tiktok_item_id) are HELD (never built).
# usage: python3 build.py            -> builds payloads.json + notes.json, prints summary
#        python3 build.py <ad_id>    -> prints that ad's payload with invisible / non-letter non-ASCII chars \u-escaped
import json, sys, unicodedata
from urllib.parse import urlsplit, parse_qsl
W='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/'
pre=json.load(open(W+'tt10_work/pre_all.json'))
inp=json.load(open(W+'in_tiktok_10.json'))
excl=json.load(open('/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/work/excl_platform_refused_v2.json'))
PIX='7347671240183693330'   # exact, pixel/list req 202610122214425D71483FA52312114C00 (Visit Diriyah - Base Pixel)
PIX_OTHER='7610705877289091089'
assert float(PIX)==float(7347671240183693000) and float(PIX_OTHER)!=float(7347671240183693000)
out={}; notes={}; held={}
for u in inp:
    a=pre[u['unit']]
    assert len(u['changes'])==1
    ch=u['changes'][0]; assert ch['slot']=='ad.landing_page_url'
    assert not any(e['platform']=='tiktok' and str(e.get('ad_id'))==u['unit'] and e['slot']==ch['slot'] for e in excl)
    assert a['ad_id']==u['unit'] and a['advertiser_id']==u['account_id'] and a['ad_name']==u['ad_names'][0], u['unit']
    assert a['landing_page_url']==ch['now'], u['unit']
    if a['identity_type']=='BC_AUTH_TT' and a.get('tiktok_item_id'):
        held[a['ad_id']]=a['tiktok_item_id']; continue
    new=ch['new']
    sp=urlsplit(new); q=parse_qsl(sp.query, keep_blank_values=True)
    assert all(k.startswith('utm_') and k!='utm_id' for k,v in q) and len(set(k for k,v in q))==len(q)
    assert '%' not in sp.query and '+' not in sp.query and sp.fragment=='' and '#' not in new
    assert a['campaign_automation_type']=='MANUAL' and a['is_aco'] is False
    assert a['identity_type']=='BC_AUTH_TT' and a['ad_format']=='CAROUSEL_ADS' and not a.get('tiktok_item_id') and not a.get('video_id')
    assert a['identity_authorized_bc_id'] and a['image_ids'] and a['music_id'] and isinstance(a['music_id'],str)
    for k in ('card_id','page_id','impression_tracking_url','click_tracking_url','creative_type','ad_texts','carousel_image_labels','landing_page_urls','viewability_vast_url','brand_safety_vast_url'):
        assert a.get(k) in (None,''), (u['unit'],k,a.get(k))
    assert a.get('deeplink') in (None,'') and a.get('playable_url') in (None,'')
    assert a['viewability_postbid_partner']=='UNSET' and a['brand_safety_postbid_partner']=='UNSET'
    assert a.get('deeplink_type') in (None,'NORMAL')
    assert a.get('fallback_type') in (None,'UNSET')
    assert a.get('avatar_icon_web_uri') in (None,'')
    pi=a.get('product_info')
    assert pi is None or all(v is None for v in pi.values()), pi
    tp=a.get('tracking_pixel_id')
    assert tp in (0,None) or tp==7347671240183693000, tp
    utm=a.get('utm_params') or []
    assert all(x['key']!='utm_id' for x in utm)
    cr={"ad_id":a['ad_id'],"ad_name":a['ad_name'],"identity_type":a['identity_type'],"identity_id":a['identity_id'],
        "identity_authorized_bc_id":a['identity_authorized_bc_id'],"ad_format":a['ad_format'],
        "image_ids":a['image_ids'],"music_id":a['music_id'],"ad_text":a['ad_text']}
    if a.get('call_to_action_id'):
        assert a.get('call_to_action') in (None,'') and isinstance(a['call_to_action_id'],str)
        cr["call_to_action_id"]=a['call_to_action_id']
    else:
        assert a['call_to_action']
        cr["call_to_action"]=a['call_to_action']
    cr["landing_page_url"]=new
    if utm:
        cr["utm_params"]=[{"key":k,"value":v} for k,v in q]
    cr["dark_post_status"]=a['dark_post_status']
    if a.get('creative_auto_enhancement_strategy_list'):
        cr["creative_auto_enhancement_strategy_list"]=a['creative_auto_enhancement_strategy_list']
    cr["creative_authorized"]=a['creative_authorized']; cr["vast_moat_enabled"]=a['vast_moat_enabled']
    if tp not in (0,None):
        cr["tracking_pixel_id"]=PIX
    txt=a.get('ad_text') or ''
    notes[a['ad_id']]={"trailing_ws":txt!=txt.rstrip(),"leading_ws":txt!=txt.lstrip(),
        "nonprint":sorted({'U+%04X'%ord(c) for c in txt if unicodedata.category(c) in ('Cf','Cc','Zs','Mn') and c!=' '}),
        "utm_before":[x['key'] for x in utm],"enh":a.get('creative_auto_enhancement_strategy_list','<absent>'),
        "pixel":tp,"cta":a.get('call_to_action_id') or a.get('call_to_action')}
    out[a['ad_id']]={"advertiser_id":u['account_id'],"adgroup_id":a['adgroup_id'],"creatives":[cr]}
json.dump(out,open(W+'tt10_work/payloads.json','w'),ensure_ascii=False,indent=1)
json.dump(notes,open(W+'tt10_work/notes.json','w'),ensure_ascii=False,indent=1)
json.dump(held,open(W+'tt10_work/held.json','w'),ensure_ascii=False,indent=1)

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
    print('held', len(held), held)
    for k,v in out.items(): print(k, notes[k], sorted(v['creatives'][0].keys()))
