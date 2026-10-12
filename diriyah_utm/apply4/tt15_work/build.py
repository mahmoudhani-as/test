import json, copy
from urllib.parse import urlsplit, parse_qsl
units=json.load(open('../in_tiktok_15.json'))
d=json.loads(open('pre_read_text.json').read())
live={a['smart_plus_ad_id']:a for a in d['data']['data']['data']['list']}
out={}
for u in units:
    ad=u['unit']; a=live[ad]; c=u['changes'][0]
    assert c['slot']=='smart_plus_ad.landing_page_url_list[0].landing_page_url'
    assert len(a['landing_page_url_list'])==1
    cur=a['landing_page_url_list'][0]['landing_page_url']
    assert cur==c['now'] or cur in c['alt_now'], ad
    new=c['new']
    q=parse_qsl(urlsplit(new).query,keep_blank_values=True)
    assert all(k.startswith('utm_') and k!='utm_id' for k,_ in q) and len(set(k for k,_ in q))==len(q)
    ac=copy.deepcopy(a['ad_configuration'])
    if 'utm_params' in ac:
        ac['utm_params']=[{"key":k,"value":v} for k,v in q]
    p={"advertiser_id":u['account_id'],"smart_plus_ad_id":ad,"landing_page_url_list":[{"landing_page_url":new}],"ad_configuration":ac}
    out[ad]=p
json.dump(out,open('payloads.json','w'),ensure_ascii=False,indent=1)
print(json.dumps(out['1875491701476546']))
