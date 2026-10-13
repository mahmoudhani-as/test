# usage: python3 -I build_reg.py <pre_read_file> <ad_id> [<ad_id> ...]
# Regular (non Smart+) ads: classify from the exact pre-read text, decide AlreadyFixed / Write / Skipped / Hold,
# and build the full /v1.3/ad/update/ payload (creative fields as read; only landing_page_url = new and utm_params = UTMs of new).
import json, sys, os
sys.path.insert(0,'/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply7/tt6_work')
from common import *
PIX={7347671240183693330:"7347671240183693330", 7610705877289091089:"7610705877289091089"}  # exact strings, pixel/list req 20261012222006D041C4FD11D0938CEAE8
def pixel_exact(v):
    if v in (None,0,'0',''): return None
    for exact,s in PIX.items():
        if float(v)==float(exact): return s
    raise SystemExit('UNKNOWN PIXEL %r'%v)
def load_list(path):
    j=json.loads(open(path,encoding='utf-8').read())
    assert j['success'] and j['data']['data']['code']==0, j
    lst=j['data']['data']['data']['list']
    for a in lst:
        assert isinstance(a,dict) and '__mcp_truncated_keys' not in a, 'truncated'
    return {a['ad_id']:a for a in lst}, j['data']['data']['request_id']
pre, rid = load_list(sys.argv[1])
DEC=T+'decisions.json'
dec=json.load(open(DEC)) if os.path.exists(DEC) else {}
for ad in sys.argv[2:]:
    u=INPD[ad]; assert len(u['changes'])==1; ch=u['changes'][0]; assert ch['slot']=='ad.landing_page_url'
    assert not excluded(ad, ch['slot']), 'EXCLUDED'
    a=pre[ad]
    assert a['ad_id']==ad and a['advertiser_id']==u['account_id'], ad
    probs=[]
    if a['ad_name']!=u['ad_names'][0]: probs.append('ad_name differs from plan: %r'%a['ad_name'])
    cur, extra, conflict = eff_url(a.get('landing_page_url'), a.get('utm_params'))
    if conflict: probs.append('utm_params conflict with URL: %r'%conflict)
    new=ch['new']
    it=a['identity_type']; item=a.get('tiktok_item_id')
    cls = ('SPARK_PUSH_HOLD' if it=='BC_AUTH_TT' and item else
           'BC_AUTH_TT_NO_ITEM' if it=='BC_AUTH_TT' else
           'CUSTOMIZED_USER' if it=='CUSTOMIZED_USER' else
           'SPARK_PULL' if it=='AUTH_CODE' else 'OTHER:'+str(it))
    if a.get('campaign_automation_type')!='MANUAL': probs.append('campaign_automation_type=%r'%a.get('campaign_automation_type'))
    if equiv(cur,new): decision='AlreadyFixed'
    elif cur==ch['now'] or cur in ch['alt_now']: decision='Write'
    else: decision='Skipped'
    if decision=='Write' and cls=='SPARK_PUSH_HOLD': decision='Hold'
    info={"rid":rid,"cls":cls,"decision":decision,"cur":cur,"url_field":a.get('landing_page_url'),"utm_before":[(x['key'],x['value']) for x in (a.get('utm_params') or [])],
          "extra_utm":extra,"identity_type":it,"identity_id":a.get('identity_id'),"bc":a.get('identity_authorized_bc_id'),"item":item,"ad_format":a.get('ad_format'),
          "video_id":a.get('video_id'),"image_ids":a.get('image_ids'),"music_id":a.get('music_id'),"cta":a.get('call_to_action_id') or a.get('call_to_action'),
          "pixel":a.get('tracking_pixel_id'),"op":a.get('operation_status'),"sec":a.get('secondary_status'),"modify_time":a.get('modify_time'),
          "adgroup_id":a.get('adgroup_id'),"text":text_notes(a.get('ad_text')),"nkeys":len(a),"enh":a.get('creative_auto_enhancement_strategy_list','<absent>'),
          "dark_post":a.get('dark_post_status','<absent>')}
    payload=None
    if decision=='Write':
        EMPTY=('card_id','page_id','impression_tracking_url','click_tracking_url','creative_type','ad_texts','carousel_image_labels','landing_page_urls',
               'viewability_vast_url','brand_safety_vast_url','deeplink','playable_url','cpp_url','video_view_tracking_url','tracking_app_id',
               'tracking_offline_event_set_ids','disclaimer_type','disclaimer_text','disclaimer_clickable_texts','shopping_ads_video_package_id',
               'product_specific_type','item_group_ids','product_set_id','sku_ids','dynamic_format','carousel_image_index','end_card_cta',
               'deeplink_utm_params','instant_product_page_used','page_image_index','promotional_music_disabled','item_duet_status','item_stitch_status')
        for k in EMPTY:
            if a.get(k) not in (None,'',[],{}): probs.append('non-empty %s=%r'%(k,a.get(k)))
        for k,ok in (('vertical_video_strategy',(None,'UNSET')),('fallback_type',(None,'UNSET')),('dynamic_destination',(None,'UNSET')),
                     ('shopping_ads_fallback_type',(None,'DEFAULT')),('deeplink_type',(None,'NORMAL')),('viewability_postbid_partner',(None,'UNSET')),
                     ('brand_safety_postbid_partner',(None,'UNSET'))):
            if a.get(k) not in ok: probs.append('unexpected %s=%r'%(k,a.get(k)))
        pi=a.get('product_info')
        if not (pi is None or all(v is None for v in pi.values())): probs.append('product_info=%r'%pi)
        if a.get('is_aco') not in (False,None): probs.append('is_aco=%r'%a.get('is_aco'))
        cr={"ad_id":a['ad_id'],"ad_name":a['ad_name']}
        if cls=='CUSTOMIZED_USER':
            cr["identity_id"]=a['identity_id']; cr["identity_type"]=it
            cr["ad_format"]=a['ad_format']
            if a['ad_format']!='SINGLE_VIDEO': probs.append('CUSTOMIZED_USER ad_format=%r'%a['ad_format'])
            if a.get('video_id'): cr["video_id"]=a['video_id']
            if a.get('image_ids'): cr["image_ids"]=a['image_ids']
            if a.get('music_id'): probs.append('music_id on CUSTOMIZED_USER %r'%a.get('music_id'))
            cr["ad_text"]=a['ad_text']
            for k in ('display_name','avatar_icon_web_uri','aigc_disclosure_type'):
                if a.get(k) not in (None,''): cr[k]=a[k]
            for k in ('creative_authorized','vast_moat_enabled'):
                if k in a and a[k] is not None: cr[k]=a[k]
            if a.get('identity_authorized_bc_id'): probs.append('bc id on CUSTOMIZED_USER')
            if a.get('dark_post_status') not in (None,): probs.append('dark_post_status on CUSTOMIZED_USER %r'%a.get('dark_post_status'))
        else:
            probs.append('class not handled by this builder: '+cls)
        if a.get('call_to_action_id'):
            if a.get('call_to_action') not in (None,''): probs.append('both CTA and CTA id')
            cr["call_to_action_id"]=a['call_to_action_id']
        else:
            cr["call_to_action"]=a['call_to_action']
        cr["landing_page_url"]=new
        if a.get('utm_params'):
            cr["utm_params"]=utm_from(new)
        px=pixel_exact(a.get('tracking_pixel_id'))
        if px: cr["tracking_pixel_id"]=px
        payload={"advertiser_id":u['account_id'],"adgroup_id":a['adgroup_id'],"creatives":[cr]}
        json.dump(payload,open(T+f'payload_{ad}.json','w'),ensure_ascii=False,indent=1)
    info['probs']=probs
    dec[ad]=info
    print('==',ad,cls,decision,'probs:',probs)
    print('   cur:',cur)
    print('   info:',json.dumps({k:v for k,v in info.items() if k not in ('cur',)},ensure_ascii=False))
    if payload: print('   PAYLOAD:',safe_dumps(payload))
json.dump(dec,open(DEC,'w'),ensure_ascii=False,indent=1)
