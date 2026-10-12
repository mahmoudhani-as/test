# usage: python3 post.py <post_read_request_id> <ad_id> [<ad_id> ...]
# Saves the post-read (exact text from this agent's transcript), compares each ad with its pre-read and with the target.
import json, sys, subprocess
from urllib.parse import urlsplit, parse_qsl
W='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/'
X=W+'tt6_work2/'
rid=sys.argv[1]; ads=sys.argv[2:]
fn=X+f'post_{rid}.json'
subprocess.run(['python3','-I',X+'extract.py', rid, fn], check=True, capture_output=True)
d=json.load(open(fn))
assert d['data']['data']['code']==0
lst=[a for a in d['data']['data']['data']['list'] if isinstance(a,dict)]
post={a['ad_id']:a for a in lst}
pre=json.load(open(X+'pre_all.json'))
inp={u['unit']:u for u in json.load(open(W+'in_tiktok_6.json'))}
try: res=json.load(open(X+'postcheck.json'))
except FileNotFoundError: res={}
for ad in ads:
    a=post.get(ad)
    if a is None: print(ad,'NOT IN POST-READ'); continue
    new=inp[ad]['changes'][0]['new']
    q=parse_qsl(urlsplit(new).query, keep_blank_values=True)
    up=[(x['key'],x['value']) for x in (a.get('utm_params') or [])]
    p=pre[ad]
    diffs=[(k,p.get(k),a.get(k)) for k in sorted(set(p)|set(a)) if not k.startswith('_') and k not in ('landing_page_url','utm_params','modify_time') and p.get(k)!=a.get(k)]
    r={'req':rid,'url_ok':a['landing_page_url']==new,'utm_ok':sorted(up)==sorted(q) and len(up)==len(q),'utm_order':up==q,'utm_has_id':any(k=='utm_id' for k,v in up),
       'diffs':diffs,'after_live':a['landing_page_url'],'modify_time':a['modify_time'],'pre_modify_time':p['modify_time'],
       'op':a['operation_status'],'sec':a.get('secondary_status'),'pre_op':p['operation_status'],'pre_sec':p.get('secondary_status'),'utm_keys':len(up),
       'item':a.get('tiktok_item_id'),'pre_item':p.get('tiktok_item_id'),'identity':(a.get('identity_type'),a.get('identity_id'))}
    res[ad]=r
    print(ad,'url_ok=',r['url_ok'],'utm_ok=',r['utm_ok'],'utm_order=',r['utm_order'],'utm_id=',r['utm_has_id'],'other_field_diffs=',diffs,
          'modify_time',p['modify_time'],'->',a['modify_time'],'status',p['operation_status'],'->',a['operation_status'],'/',a.get('secondary_status'),
          'item',p.get('tiktok_item_id'),'->',a.get('tiktok_item_id'))
json.dump(res, open(X+'postcheck.json','w'), ensure_ascii=False, indent=1)
