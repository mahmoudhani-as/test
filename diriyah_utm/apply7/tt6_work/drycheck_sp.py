# usage: python3 -I drycheck_sp.py <ad_id> <pre_read_file>
# After cmpcall: checks the dry-run preview body differs from the live read only in landing_page_url_list[i].landing_page_url and ad_configuration.utm_params.
import json, sys, re
sys.path.insert(0,'/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply7/tt6_work')
from common import *
ad, pref = sys.argv[1], sys.argv[2]
pre={a['smart_plus_ad_id']:a for a in json.load(open(T+pref))['data']['data']['data']['list']}
a=pre[ad]; body=json.load(open(T+f'resp_dry_{ad}.json'))['data']['data']['request']['body']
ch=INPD[ad]['changes'][0]; i=int(re.fullmatch(r'smart_plus_ad\.landing_page_url_list\[(\d+)\]\.landing_page_url', ch['slot']).group(1))
ok=True
if sorted(body)!=['ad_configuration','advertiser_id','landing_page_url_list','smart_plus_ad_id']: ok=False; print('unexpected top keys', sorted(body))
acb=dict(body['ad_configuration']); aca=dict(a['ad_configuration'])
ub=acb.pop('utm_params',None); ua=aca.pop('utm_params',None)
if acb!=aca: ok=False; print('ad_configuration differs beyond utm_params')
if ua: 
    if ub!=utm_from(ch['new']): ok=False; print('utm_params not = UTMs of new')
elif ub is not None: ok=False; print('utm_params added although absent/empty')
lb=body['landing_page_url_list']; la=a['landing_page_url_list']
if len(lb)!=len(la): ok=False; print('lpl length differs')
for j,(x,y) in enumerate(zip(lb,la)):
    x=dict(x); y=dict(y)
    if j==i:
        if x.get('landing_page_url')!=ch['new']: ok=False; print('lpl[i] != new')
        x.pop('landing_page_url'); y.pop('landing_page_url')
    if x!=y: ok=False; print('lpl entry differs', j)
print('dry preview vs live read: only URL (+utm_params) differ:', ok, '| utm_params', 'replaced' if ua else 'absent (left absent)')
