# usage: python3 -I post.py <post_read_request_id> <pre_read_file> <ad_id>
# Saves the post-read (exact text from transcript) and compares the ad with its pre-read and target.
import json, sys, subprocess
sys.path.insert(0,'/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/tt9_work')
from common import *
rid, pref, ad = sys.argv[1], sys.argv[2], sys.argv[3]
fn=T+f'read_{rid}.json'
subprocess.run(['python3','-I',T+'extract.py',rid,fn],check=True,capture_output=True)
post,_=load_list(fn); pre,prid=load_list(T+pref if not pref.startswith('/') else pref)
a=post[ad]; p=pre[ad]; new=INPD[ad]['changes'][0]['new']
url_ok=a['landing_page_url']==new
up=[(x['key'],x['value']) for x in (a.get('utm_params') or [])]
q=[(x['key'],x['value']) for x in utm_from(new)]
utm_ok=sorted(up)==sorted(q) and len(up)==len(q); utm_order=up==q
eff,extra,conflict=effective(a)
diffs=[(k,p.get(k,'<absent>'),a.get(k,'<absent>')) for k in sorted(set(p)|set(a)) if k not in ('landing_page_url','utm_params','modify_time') and p.get(k,'<absent>')!=a.get(k,'<absent>')]
res={'ad':ad,'post_rid':rid,'pre_rid':prid,'url_ok':url_ok,'utm_ok':utm_ok,'utm_order':utm_order,'eff_equals_new':eff==new,'extra':extra,'conflict':conflict,
     'diffs':diffs,'after_live':a['landing_page_url'],'modify_time':(p['modify_time'],a['modify_time']),'status':((p['operation_status'],p['secondary_status']),(a['operation_status'],a['secondary_status'])),
     'nkeys':(len(p),len(a)),'utm_keys_after':[k for k,v in up]}
json.dump(res,open(T+f'postcheck_{ad}.json','w'),ensure_ascii=False,indent=1)
print(json.dumps(res,ensure_ascii=False))
