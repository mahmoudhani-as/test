# usage: python3 -I post_sp.py <post_read_request_id> <pre_read_file>[,<file>...] <ad_id> [<ad_id> ...]
# Saves the Smart+ post-read (exact text from my transcript) and compares each ad with its pre-read and the target.
import json, sys, subprocess, re
sys.path.insert(0,'/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply7/tt6_work')
from common import *
rid, pref, ads = sys.argv[1], sys.argv[2], sys.argv[3:]
fn=T+f'spread_{rid}.json'
subprocess.run(['python3','-I',T+'extract.py',rid,fn],check=True,capture_output=True)
def load_sp(path):
    j=json.loads(open(path,encoding='utf-8').read())
    assert j['success'] and j['data']['data']['code']==0, j
    return {a['smart_plus_ad_id']:a for a in j['data']['data']['data']['list']}, j['data']['data']['request_id']
post,_=load_sp(fn)
pre={}; prids={}
for f in pref.split(','):
    d,r=load_sp(f if f.startswith('/') else T+f)
    for k,v in d.items(): pre[k]=v; prids[k]=r
for ad in ads:
    ch=INPD[ad]['changes'][0]; new=ch['new']
    i=int(re.fullmatch(r'smart_plus_ad\.landing_page_url_list\[(\d+)\]\.landing_page_url', ch['slot']).group(1))
    a=post[ad]; p=pre[ad]
    lp=a['landing_page_url_list'][i]['landing_page_url']
    url_ok=lp==new
    ac=a.get('ad_configuration') or {}; pac=p.get('ad_configuration') or {}
    up=[(x['key'],x['value']) for x in (ac.get('utm_params') or [])]
    q=[(x['key'],x['value']) for x in utm_from(new)]
    had=bool(pac.get('utm_params'))
    utm_ok=(sorted(up)==sorted(q) and len(up)==len(q)) if had else (up==[(x['key'],x['value']) for x in (pac.get('utm_params') or [])])
    eff,extra,conflict=eff_url(lp, ac.get('utm_params'))
    diffs=[]
    for k in sorted(set(p)|set(a)):
        if k in ('modify_time','landing_page_url_list','ad_configuration'): continue
        if p.get(k,'<absent>')!=a.get(k,'<absent>'): diffs.append((k,p.get(k,'<absent>'),a.get(k,'<absent>')))
    for k in sorted(set(pac)|set(ac)):
        if k=='utm_params': continue
        if pac.get(k,'<absent>')!=ac.get(k,'<absent>'): diffs.append(('ad_configuration.'+k,pac.get(k,'<absent>'),ac.get(k,'<absent>')))
    lpl_p=[dict(x) for x in p['landing_page_url_list']]; lpl_a=[dict(x) for x in a['landing_page_url_list']]
    if len(lpl_p)!=len(lpl_a): diffs.append(('landing_page_url_list length',len(lpl_p),len(lpl_a)))
    else:
        for j,(x,y) in enumerate(zip(lpl_p,lpl_a)):
            if j==i:
                x=dict(x); y=dict(y); x.pop('landing_page_url',None); y.pop('landing_page_url',None)
            if x!=y: diffs.append(('landing_page_url_list[%d]'%j,x,y))
    res={'ad':ad,'post_rid':rid,'pre_rid':prids[ad],'url_ok':url_ok,'utm_ok':utm_ok,'had_utm_params':had,'eff_equals_new':eff==new,'extra':extra,'conflict':conflict,
         'diffs':diffs,'after_live':lp,'after_eff':eff,'modify_time':(p.get('modify_time'),a.get('modify_time')),
         'status':((p.get('operation_status'),p.get('secondary_status')),(a.get('operation_status'),a.get('secondary_status'))),
         'utm_keys_after':[k for k,v in up],
         'items_before':[(c.get('creative_info') or {}).get('tiktok_item_id') for c in p.get('creative_list') or []],
         'items_after':[(c.get('creative_info') or {}).get('tiktok_item_id') for c in a.get('creative_list') or []]}
    json.dump(res,open(T+f'postcheck_{ad}.json','w'),ensure_ascii=False,indent=1)
    print(json.dumps(res,ensure_ascii=False))
