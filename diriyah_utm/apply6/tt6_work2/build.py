# Classify every unit of in_tiktok_6.json from the relaunch pre-read and build exact ad/update payloads.
# usage: python3 build.py            -> summary
#        python3 build.py <ad_id>    -> print the escaped payload JSON for that ad (for the tool call)
import json, sys, unicodedata
from urllib.parse import urlsplit, parse_qsl
W='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/'
X=W+'tt6_work2/'
pre={}
for fn in ('pre_read_1.json','pre_read_2.json'):
    d=json.load(open(X+fn))
    assert d['data']['data']['code']==0
    rid=d['data']['data']['request_id']
    for a in d['data']['data']['data']['list']:
        a['_req']=rid; pre[a['ad_id']]=a
json.dump(pre, open(X+'pre_all.json','w'), ensure_ascii=False, indent=1)
inp=json.load(open(W+'in_tiktok_6.json'))
excl=json.load(open('/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/work/excl_platform_refused_v2.json'))
EXCL={(e['platform'],str(e['ad_id']),e['slot']) for e in excl}
PIX='7347671240183693330'   # exact, pixel/list req 202610122212132E88409C2F319BA417F7 ("Visit Diriyah - Base Pixel"); other pixel 7610705877289091089 renders differently
assert int(float(PIX))==int(float(7347671240183693000)) and int(float('7610705877289091089'))!=int(float(7347671240183693000))
def norm(u):
    p=urlsplit((u or '').strip())
    return (p.scheme, p.netloc.lower(), p.path, p.fragment, tuple(sorted(parse_qsl(p.query, keep_blank_values=True))))
plan={}; payloads={}
for u in inp:
    ad=u['unit']; a=pre.get(ad)
    assert len(u['changes'])==1
    ch=u['changes'][0]; assert ch['slot']=='ad.landing_page_url'
    new=ch['new']; sp=urlsplit(new); q=parse_qsl(sp.query, keep_blank_values=True)
    assert all(k.startswith('utm_') and k!='utm_id' for k,v in q) and len({k for k,v in q})==len(q)
    assert sp.fragment=='' and '+' not in sp.query and '%' not in sp.query
    if ('tiktok',ad,ch['slot']) in EXCL:
        plan[ad]={'action':'EXCLUDED'}; continue
    if a is None:
        plan[ad]={'action':'NOT_FOUND'}; continue
    assert a['ad_id']==ad and a['advertiser_id']==u['account_id'] and a['ad_name']==u['ad_names'][0], ad
    cur=a['landing_page_url']
    it=a['identity_type']; item=a.get('tiktok_item_id')
    up=[(x['key'],x['value']) for x in (a.get('utm_params') or [])]
    info={'identity_type':it,'tiktok_item_id':item,'cur':cur,'utm_params':up,'modify_time':a['modify_time'],
          'op':a['operation_status'],'sec':a['secondary_status'],'adgroup_id':a['adgroup_id'],'req':a['_req'],
          'cta':a.get('call_to_action'),'cta_id':a.get('call_to_action_id'),'creative_authorized':a.get('creative_authorized')}
    txt=a.get('ad_text') or ''
    info['ad_text_trailing_ws']=txt!=txt.rstrip(); info['ad_text_leading_ws']=txt!=txt.lstrip()
    info['ad_text_special']=sorted({'U+%04X'%ord(c) for c in txt if unicodedata.category(c) in ('Cf','Cc','Zs','Mn') and c!=' ' or ord(c)>0xFFFF})
    info['ad_text_double_space']='  ' in txt
    if it=='BC_AUTH_TT' and item:
        info['action']='HOLD_SPARK_PUSH'
    elif norm(cur)==norm(new):
        info['action']='ALREADY'; info['exact']=(cur==new)
        info['utm_matches_new']=sorted(up)==sorted(q) and len(up)==len(q)
    elif cur==ch['now'] or cur in (ch.get('alt_now') or []):
        info['action']='WRITE'; info['matched']='now' if cur==ch['now'] else 'alt_now'
    elif norm(cur)==norm(ch['now']) or any(norm(cur)==norm(x) for x in (ch.get('alt_now') or [])):
        info['action']='WRITE'; info['matched']='now/alt_now (same params, different order/encoding)'
    else:
        info['action']='SKIP'
    plan[ad]=info
    if info['action']!='WRITE': continue
    # ---- build full update from the creative fields as read ----
    assert a['campaign_automation_type']=='MANUAL' and a['is_aco'] is False and a['ad_format']=='SINGLE_VIDEO', ad
    for k in ('card_id','page_id','music_id','impression_tracking_url','click_tracking_url','creative_type','ad_texts','carousel_image_labels','landing_page_urls','viewability_vast_url','brand_safety_vast_url'):
        assert a.get(k) in (None,''), (ad,k,a.get(k))
    assert a.get('deeplink') in (None,'') and a.get('playable_url') in (None,'') and a.get('deeplink_type') in (None,'NORMAL')
    assert a['viewability_postbid_partner']=='UNSET' and a['brand_safety_postbid_partner']=='UNSET'
    assert not a.get('creative_auto_enhancement_strategy_list') and not a.get('dark_post_status') and not a.get('identity_authorized_bc_id')
    tp=a.get('tracking_pixel_id')
    assert tp in (0,None) or int(tp)==7347671240183693000, tp
    cr={"ad_id":a['ad_id'],"ad_name":a['ad_name'],"identity_id":a['identity_id'],"identity_type":it,"ad_format":a['ad_format']}
    if it=='CUSTOMIZED_USER':
        assert a['video_id'] and a['image_ids'] and not item and a.get('app_name') in ('',None)
        cr["video_id"]=a['video_id']; cr["image_ids"]=a['image_ids']; cr["ad_text"]=a['ad_text']
    elif it=='AUTH_CODE':
        assert item and not a.get('video_id') and a['image_ids']==[]
        cr["tiktok_item_id"]=item
        cr["promotional_music_disabled"]=a['promotional_music_disabled']
        cr["ad_text"]=a['ad_text']
    else:
        raise SystemExit('unexpected identity '+it+' '+ad)
    if a.get('call_to_action_id'):
        assert a.get('call_to_action') in (None,'')
        cr["call_to_action_id"]=a['call_to_action_id']
    else:
        assert a['call_to_action']
        cr["call_to_action"]=a['call_to_action']
    cr["landing_page_url"]=new
    cr["utm_params"]=[{"key":k,"value":v} for k,v in q]
    if tp not in (0,None): cr["tracking_pixel_id"]=PIX
    if it=='CUSTOMIZED_USER':
        cr["display_name"]=a['display_name']; cr["avatar_icon_web_uri"]=a['avatar_icon_web_uri']
        cr["aigc_disclosure_type"]=a['aigc_disclosure_type']
    for k in ('vertical_video_strategy','fallback_type','dynamic_destination','shopping_ads_fallback_type'):
        if k in a and a[k] is not None: cr[k]=a[k]
    cr["creative_authorized"]=a['creative_authorized']; cr["vast_moat_enabled"]=a['vast_moat_enabled']
    payloads[ad]={"advertiser_id":u['account_id'],"adgroup_id":a['adgroup_id'],"creatives":[cr]}
json.dump(plan, open(X+'plan.json','w'), ensure_ascii=False, indent=1)
json.dump(payloads, open(X+'payloads.json','w'), ensure_ascii=False, indent=1)

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
    print(safe_dumps(payloads[sys.argv[1]]))
else:
    for u in inp:
        p=plan[u['unit']]
        print(u['unit'], p.get('action'), p.get('matched',''), p.get('identity_type'), 'item=',p.get('tiktok_item_id'), 'cta=',p.get('cta'), p.get('cta_id'), 'op=',p.get('op'), 'mod=',p.get('modify_time'),
              'utm_keys=',len(p.get('utm_params') or []), 'trail_ws=',p.get('ad_text_trailing_ws'), 'special=',p.get('ad_text_special'), 'dbl=',p.get('ad_text_double_space'),
              ('exact=%s utm_ok=%s'%(p.get('exact'),p.get('utm_matches_new')) if p.get('action')=='ALREADY' else ''))
    for k,v in payloads.items(): print(k, sorted(v['creatives'][0].keys()))
