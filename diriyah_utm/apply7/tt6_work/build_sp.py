# usage: python3 -I build_sp.py <read_file>[,<read_file>...] <ad_id> [<ad_id> ...]
# Upgraded Smart+ ads: decide AlreadyFixed / Write / Skipped from the exact smart_plus/ad/get text and build the
# smart_plus/ad/update payload: landing_page_url_list as read with only [i].landing_page_url = new, ad_configuration as read
# with only utm_params = UTMs of new (when the ad has utm_params). creative_list / ad_text_list / ad_name / status are NOT sent.
import json, sys, os, re, copy
sys.path.insert(0,'/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply7/tt6_work')
from common import *
def load_sp(path):
    j=json.loads(open(path,encoding='utf-8').read())
    assert j['success'] and j['data']['data']['code']==0, j
    lst=j['data']['data']['data']['list']
    for a in lst:
        assert isinstance(a,dict) and '__mcp_truncated_keys' not in json.dumps(a), 'truncated'
    return {a['smart_plus_ad_id']:a for a in lst}, j['data']['data']['request_id']
pre={}; rids={}
for f in sys.argv[1].split(','):
    d,rid=load_sp(f if f.startswith('/') else T+f)
    for k,v in d.items(): pre[k]=v; rids[k]=rid
DEC=T+'decisions.json'
dec=json.load(open(DEC)) if os.path.exists(DEC) else {}
def bigints(o,path=''):
    out=[]
    if isinstance(o,dict):
        for k,v in o.items(): out+=bigints(v,path+'.'+k)
    elif isinstance(o,list):
        for i,v in enumerate(o): out+=bigints(v,path+'[%d]'%i)
    elif isinstance(o,(int,float)) and not isinstance(o,bool):
        out.append((path,o))
    return out
for ad in sys.argv[2:]:
    u=INPD[ad]; assert len(u['changes'])==1; ch=u['changes'][0]
    m=re.fullmatch(r'smart_plus_ad\.landing_page_url_list\[(\d+)\]\.landing_page_url', ch['slot']); assert m, ch['slot']
    i=int(m.group(1))
    assert not excluded(ad, ch['slot']), 'EXCLUDED'
    a=pre[ad]
    assert a['smart_plus_ad_id']==ad and a['advertiser_id']==u['account_id'], ad
    probs=[]
    if a.get('ad_name')!=u['ad_names'][0]: probs.append('ad_name differs from plan: %r'%a.get('ad_name'))
    lpl=a.get('landing_page_url_list') or []
    ac=a.get('ad_configuration') or {}
    if len(lpl)<=i: probs.append('landing_page_url_list has %d entries'%len(lpl)); url=None
    else: url=lpl[i].get('landing_page_url')
    cur, extra, conflict = eff_url(url, ac.get('utm_params'))
    if conflict: probs.append('utm_params conflict with URL: %r'%conflict)
    new=ch['new']
    if equiv(cur,new): decision='AlreadyFixed'
    elif cur==ch['now'] or cur in ch['alt_now']: decision='Write'
    else: decision='Skipped'
    cl=a.get('creative_list') or []
    mats=[{"ad_material_id":c.get('ad_material_id'),"fmt":(c.get('creative_info') or {}).get('ad_format'),"identity_type":(c.get('creative_info') or {}).get('identity_type'),
           "identity_id":(c.get('creative_info') or {}).get('identity_id'),"bc":(c.get('creative_info') or {}).get('identity_authorized_bc_id'),
           "item":(c.get('creative_info') or {}).get('tiktok_item_id'),"video":((c.get('creative_info') or {}).get('video_info') or {}).get('video_id'),
           "n_images":len(((c.get('creative_info') or {}).get('image_info') or [])),"status":c.get('material_operation_status')} for c in cl]
    nums=bigints(ac)
    for p,v in nums:
        if abs(v)>2**53: probs.append('big number in ad_configuration %s=%r (precision!)'%(p,v))
    info={"rid":rids[ad],"cls":"SMART_PLUS","slot_index":i,"decision":decision,"cur":cur,"url_field":url,"n_lp":len(lpl),
          "utm_before":[(x['key'],x['value']) for x in (ac.get('utm_params') or [])],"has_utm_params":'utm_params' in ac,"extra_utm":extra,
          "ac_keys":sorted(ac.keys()),"ac_numbers":nums,"materials":mats,"n_text":len(a.get('ad_text_list') or []),
          "op":a.get('operation_status'),"sec":a.get('secondary_status'),"modify_time":a.get('modify_time'),"adgroup_id":a.get('adgroup_id'),
          "pixel":(ac.get('tracking_info') or {}).get('tracking_pixel_id'),"cta_id":ac.get('call_to_action_id')}
    payload=None
    if decision=='Write':
        lpl_new=copy.deepcopy(lpl); lpl_new[i]['landing_page_url']=new
        ac_new=copy.deepcopy(ac)
        if ac.get('utm_params'):
            ac_new['utm_params']=utm_from(new)
        elif 'utm_params' in ac:
            probs.append('utm_params present but empty: left as read')
        payload={"advertiser_id":u['account_id'],"smart_plus_ad_id":ad,"landing_page_url_list":lpl_new,"ad_configuration":ac_new}
        json.dump(payload,open(T+f'payload_{ad}.json','w'),ensure_ascii=False,indent=1)
    info['probs']=probs
    dec[ad]=info
    print('==',ad,'SMART_PLUS',decision,'probs:',probs)
    print('   cur:',cur)
    print('   info:',json.dumps({k:v for k,v in info.items() if k not in ('cur',)},ensure_ascii=False))
    if payload: print('   PAYLOAD:',json.dumps(payload,ensure_ascii=True))
json.dump(dec,open(DEC,'w'),ensure_ascii=False,indent=1)
