import json, copy, sys
from urllib.parse import urlsplit, parse_qsl
t=json.load(open('sp_pre_read_text.json'))
by={a['smart_plus_ad_id']:a for a in t['data']['data']['data']['list']}
units=json.load(open('../in_tiktok_14.json'))
out={}
for u in units:
    ch=u['changes'][0]
    if not ch['slot'].startswith('smart_plus'): continue
    assert ch['slot']=='smart_plus_ad.landing_page_url_list[0].landing_page_url'
    a=by[u['unit']]
    assert len(a['landing_page_url_list'])==1 and a['landing_page_url_list'][0]['landing_page_url']==ch['now']
    new=ch['new']
    q=parse_qsl(urlsplit(new).query, keep_blank_values=True)
    assert all(k.startswith('utm_') and k!='utm_id' for k,_ in q) and len(set(k for k,_ in q))==len(q)
    ac=copy.deepcopy(a['ad_configuration'])
    assert 'utm_params' in ac
    old_keys=sorted(x['key'] for x in ac['utm_params'])
    ac['utm_params']=[{"key":k,"value":v} for k,v in q]
    p={"advertiser_id":u['account_id'],"smart_plus_ad_id":u['unit'],"landing_page_url_list":[{"landing_page_url":new}],"ad_configuration":ac}
    out[u['unit']]=p
    print(u['unit'], 'old utm keys', old_keys, 'new', [k for k,_ in q], 'pixel', ac['tracking_info'].get('tracking_pixel_id'))
json.dump(out,open('sp_payloads.json','w'),ensure_ascii=False,indent=1)
