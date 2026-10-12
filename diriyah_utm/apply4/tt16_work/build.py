import json, copy, sys
from urllib.parse import urlsplit, parse_qsl
pre=json.load(open('sp_pre.json'))
units=json.load(open('../in_tiktok_16.json'))
def norm(u):
    s=urlsplit(u); return (s.scheme,s.netloc,s.path,s.fragment,sorted(parse_qsl(s.query,keep_blank_values=True)))
out={}
for u in units:
    ch=u['changes'][0]
    if not ch['slot'].startswith('smart_plus'): continue
    assert len(u['changes'])==1 and ch['slot']=='smart_plus_ad.landing_page_url_list[0].landing_page_url'
    a=pre[u['unit']]
    cur=a['lp']
    if norm(cur)==norm(ch['new']): st='AlreadyFixed'
    elif cur==ch['now'] or cur in ch['alt_now']: st='write'
    else: st='Skipped'
    # sanity: utm_params as read should be subset of LP query
    lpq=dict(parse_qsl(urlsplit(cur).query))
    for p in a['ac']['utm_params']: assert lpq.get(p['key'])==p['value'], (u['unit'],p)
    new=ch['new']
    q=parse_qsl(urlsplit(new).query, keep_blank_values=True)
    assert all(k.startswith('utm_') and k!='utm_id' for k,_ in q) and len(set(k for k,_ in q))==len(q)
    ac=copy.deepcopy(a['ac'])
    ac['utm_params']=[{"key":k,"value":v} for k,v in q]
    p={"advertiser_id":u['account_id'],"smart_plus_ad_id":u['unit'],"landing_page_url_list":[{"landing_page_url":new}],"ad_configuration":ac}
    out[u['unit']]=p
    print(u['unit'], st, 'old keys', [x['key'] for x in a['ac']['utm_params']], '-> new', [k for k,_ in q])
json.dump(out,open('sp_payloads.json','w'),ensure_ascii=False,indent=1)
if len(sys.argv)>1: print(json.dumps(out[sys.argv[1]],ensure_ascii=False))
