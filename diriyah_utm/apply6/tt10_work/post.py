# usage: python3 post.py <post_read_request_id> <ad_id> [<ad_id> ...]
# Saves the post-read (exact text from transcript), compares each ad with its pre-read and target.
import json, sys, subprocess
from urllib.parse import urlsplit, parse_qsl
W='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/'
rid=sys.argv[1]; ads=sys.argv[2:]
fn=W+f'tt10_work/post_{rid}.json'
subprocess.run(['python3','-I', W+'tt10_work/extract.py', rid, fn], check=True, capture_output=True)
d=json.load(open(fn))
assert d['data']['data']['code']==0
lst=[a for a in d['data']['data']['data']['list'] if isinstance(a,dict)]
post={a['ad_id']:a for a in lst}
pre=json.load(open(W+'tt10_work/pre_all.json'))
inp={u['unit']:u for u in json.load(open(W+'in_tiktok_10.json'))}
res={}
for ad in ads:
    a=post.get(ad)
    if a is None: print(ad,'NOT IN POST-READ'); res[ad]=None; continue
    new=inp[ad]['changes'][0]['new']
    q=parse_qsl(urlsplit(new).query, keep_blank_values=True)
    url_ok = a['landing_page_url']==new
    up=[(x['key'],x['value']) for x in (a.get('utm_params') or [])]
    utm_ok = sorted(up)==sorted(q) and len(up)==len(q)
    utm_order = up==q
    diffs=[]
    p=pre[ad]
    for k in sorted(set(p)|set(a)):
        if k in ('landing_page_url','utm_params','modify_time'): continue
        if p.get(k)!=a.get(k): diffs.append((k,p.get(k,'<absent>'),a.get(k,'<absent>')))
    res[ad]={'url_ok':url_ok,'utm_ok':utm_ok,'utm_order':utm_order,'diffs':diffs,'after_live':a['landing_page_url'],
             'modify_time':a['modify_time'],'pre_modify_time':p['modify_time'],'op':a['operation_status'],'sec':a['secondary_status'],'utm_keys':len(up),
             'nkeys_pre':len(p),'nkeys_post':len(a)}
    print(ad, 'url_ok=',url_ok,'utm_ok=',utm_ok,'utm_order=',utm_order,'other_field_diffs=',diffs,'modify_time',p['modify_time'],'->',a['modify_time'],'status',p['operation_status'],p['secondary_status'],'->',a['operation_status'],a['secondary_status'],'keys',len(p),'->',len(a))
json.dump(res, open(W+f'tt10_work/postcheck_{rid}.json','w'), ensure_ascii=False, indent=1)
