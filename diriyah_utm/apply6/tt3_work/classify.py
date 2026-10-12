# Merge the two pre-reads, classify each unit vs now/alt_now/new.
import json, unicodedata
from urllib.parse import urlsplit, parse_qsl
W='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/'
pre={}; rid={}
for fn in ('pre_read_1.json','pre_read_2.json'):
    j=json.load(open(W+'tt3_work/'+fn))
    r=j['data']['data']['request_id']
    for a in j['data']['data']['data']['list']:
        pre[a['ad_id']]=a; rid[a['ad_id']]=r
json.dump({'pre':pre,'rid':rid}, open(W+'tt3_work/pre_all.json','w'), ensure_ascii=False, indent=1)
inp=json.load(open(W+'in_tiktok_3.json'))
def same(a,b):
    A=urlsplit(a); B=urlsplit(b)
    return (A.scheme,A.netloc,A.path,A.fragment)==(B.scheme,B.netloc,B.path,B.fragment) and sorted(parse_qsl(A.query,keep_blank_values=True))==sorted(parse_qsl(B.query,keep_blank_values=True))
cls={}
for u in inp:
    a=pre.get(u['unit'])
    assert a is not None, u['unit']
    assert len(u['changes'])==1 and u['changes'][0]['slot']=='ad.landing_page_url'
    ch=u['changes'][0]; cur=a['landing_page_url']
    assert a['advertiser_id']==u['account_id'] and a['ad_name']==u['ad_names'][0] and a['campaign_name']==u['campaign_name'], u['unit']
    if same(cur,ch['new']): st='AlreadyFixed'
    elif cur==ch['now'] or same(cur,ch['now']) or any(cur==x or same(cur,x) for x in ch.get('alt_now',[])): st='writable'
    else: st='changed'
    spark = a['identity_type']=='BC_AUTH_TT' and bool(a.get('tiktok_item_id'))
    kind = 'SPARK_PUSH' if spark else a['identity_type']+('/item' if a.get('tiktok_item_id') else '')
    which = 'now' if cur==ch['now'] else ('new' if cur==ch['new'] else ('alt' if cur in ch.get('alt_now',[]) else 'other/reordered'))
    txt=a.get('ad_text') or ''
    np_=sorted({'U+%04X'%ord(c) for c in txt if unicodedata.category(c) in ('Cf','Cc','Zs','Mn','Zl','Zp') and c!=' '})
    cls[u['unit']]={'state':st,'kind':kind,'cur_is':which,'trailing_ws':txt!=txt.rstrip(),'nonprint':np_,'op':a['operation_status'],'sec':a['secondary_status'],'modify_time':a['modify_time'],'item':a.get('tiktok_item_id'),'cta_id':a.get('call_to_action_id'),'rid':rid[u['unit']]}
    print(u['unit'], st, kind, 'cur==', which, 'item', a.get('tiktok_item_id'), 'cta_id', a.get('call_to_action_id'), 'trail_ws', txt!=txt.rstrip(), np_, a['operation_status'], a['modify_time'])
json.dump(cls, open(W+'tt3_work/classes.json','w'), indent=1)
