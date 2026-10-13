# usage: python3 -I post.py <post_read_request_id> <pre_read_file> <ad_id>
# Saves the post-read (exact text from transcript) and compares the ad with its pre-read and target.
import json, sys
sys.path.insert(0,'/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply7/tt4_work')
from common import *
rid, pref, ad = sys.argv[1], sys.argv[2], sys.argv[3]
fn=T+f'read_{rid}.json'
extract(rid, fn)
post,_=load_list(fn); pre,prid=load_list(pref if pref.startswith('/') else T+pref)
a=post[ad]; p=pre[ad]; new=INPD[ad]['changes'][0]['new']
url_ok=a['landing_page_url']==new
up=[(x['key'],x['value']) for x in (a.get('utm_params') or [])]
had_utm=bool(p.get('utm_params'))
q=[(x['key'],x['value']) for x in utm_from(new)]
utm_ok=(sorted(up)==sorted(q) and len(up)==len(q)) if had_utm else (up==[])
utm_order=up==q
eff,extra,conflict=effective(a)
IGN=('landing_page_url','utm_params','modify_time')
diffs=[(k,p.get(k,'<absent>'),a.get(k,'<absent>')) for k in sorted(set(p)|set(a)) if k not in IGN and p.get(k,'<absent>')!=a.get(k,'<absent>')]
text_only_trim = (len(diffs)==1 and diffs[0][0]=='ad_text' and isinstance(diffs[0][1],str) and diffs[0][1].rstrip()==diffs[0][2] and diffs[0][1]!=diffs[0][2])
res={'ad':ad,'post_rid':rid,'pre_rid':prid,'url_ok':url_ok,'utm_ok':utm_ok,'utm_order':utm_order,'had_utm':had_utm,'eff_equals_new':eff==new,'extra':extra,'conflict':conflict,
     'diffs':diffs,'text_only_trim':text_only_trim,'after_live':a['landing_page_url'],'after_eff':eff,'modify_time':(p.get('modify_time'),a.get('modify_time')),
     'status':((p.get('operation_status'),p.get('secondary_status')),(a.get('operation_status'),a.get('secondary_status'))),
     'nkeys':(len(p),len(a)),'utm_keys_after':[k for k,v in up],'item_after':a.get('tiktok_item_id'),'identity_after':(a.get('identity_type'),a.get('identity_id'))}
json.dump(res,open(T+f'postcheck_{ad}.json','w'),ensure_ascii=False,indent=1)
print(json.dumps(res,ensure_ascii=False))
