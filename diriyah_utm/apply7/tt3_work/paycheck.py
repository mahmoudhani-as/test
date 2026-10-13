# usage: python3 -I paycheck.py <pre_read_file[,file2]> <ad_id> ...
# Checks every payload creative field equals the pre-read value, except landing_page_url (= new), utm_params (= UTMs of new) and tracking_pixel_id (exact string of the rounded read).
import json, sys
sys.path.insert(0,'/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply7/tt3_work')
from common import *
pre={}
for fn in sys.argv[1].split(','):
    m,rid=load_list(fn if fn.startswith('/') else T+fn); pre.update(m)
for ad in sys.argv[2:]:
    P=json.load(open(T+f'payload_{ad}.json')); cr=P['creatives'][0]; a=pre[ad]; new=INPD[ad]['changes'][0]['new']
    bad=[]
    for k,v in cr.items():
        if k=='landing_page_url':
            if v!=new: bad.append(k)
        elif k=='utm_params':
            if v!=utm_from(new) or any(x['key']=='utm_id' for x in v): bad.append(k)
        elif k=='tracking_pixel_id':
            if float(int(v))!=float(a.get('tracking_pixel_id')): bad.append(k)
        elif a.get(k)!=v: bad.append(k)
    if P['advertiser_id']!=a['advertiser_id'] or P['adgroup_id']!=a['adgroup_id']: bad.append('top')
    notsent=[k for k in a if k not in cr]
    print(ad,'OK' if not bad else 'BAD '+str(bad),'| sent:',list(cr.keys()))
