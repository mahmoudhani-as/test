# usage: python3 -I postcheck.py <post_read_request_id> <pre_read_file[,file2]> <ad_id> [<ad_id> ...]
# Saves the post-read (exact text from this agent's transcript) and compares each ad with its pre-read and its target.
import json, sys, subprocess
sys.path.insert(0,'/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply7/tt3_work')
from common import *
rid, prefs, ads = sys.argv[1], sys.argv[2], sys.argv[3:]
fn=T+f'read_{rid}.json'
import os
if not os.path.exists(fn):
    subprocess.run(['python3','-I',T+'extract.py',rid,fn],check=True,capture_output=True)
post,_=load_list(fn)
pre={}; prids={}
for f in prefs.split(','):
    m,r=load_list(f if f.startswith('/') else T+f)
    for k,v in m.items(): pre[k]=v; prids[k]=r
for ad in ads:
    a=post[ad]; p=pre[ad]; new=INPD[ad]['changes'][0]['new']
    url_ok=a['landing_page_url']==new
    up=[(x['key'],x['value']) for x in (a.get('utm_params') or [])]
    q=[(x['key'],x['value']) for x in utm_from(new)]
    had_utm=bool(p.get('utm_params'))
    utm_ok=(sorted(up)==sorted(q) and len(up)==len(q)) if had_utm else (up==[])
    eff,extra,conflict=effective(a)
    diffs=[(k,p.get(k,'<absent>'),a.get(k,'<absent>')) for k in sorted(set(p)|set(a)) if k not in ('landing_page_url','utm_params','modify_time') and p.get(k,'<absent>')!=a.get(k,'<absent>')]
    res={'ad':ad,'post_rid':rid,'pre_rid':prids[ad],'url_ok':url_ok,'utm_ok':utm_ok,'utm_order':up==q,'eff_equals_new':eff==new,'extra':extra,'conflict':conflict,
         'diffs':diffs,'after_live':a['landing_page_url'],'modify_time':(p['modify_time'],a['modify_time']),
         'status':((p['operation_status'],p.get('secondary_status')),(a['operation_status'],a.get('secondary_status'))),
         'nkeys':(len(p),len(a)),'utm_keys_after':[k for k,v in up],'item_after':a.get('tiktok_item_id','<absent>')}
    json.dump(res,open(T+f'postcheck_{ad}.json','w'),ensure_ascii=False,indent=1)
    print(json.dumps(res,ensure_ascii=False))
