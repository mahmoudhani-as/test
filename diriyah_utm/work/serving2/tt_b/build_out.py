import json, sys
base='/tmp/claude-0/-home-user-test/0a7a4347-50ae-5891-a613-ee320c5ab4bb/scratchpad/diriyah_utm/work/serving2/'
ids=json.load(open(base+'serving_in_tiktok_7338057963233443842_b.json'))
ct=json.load(open(base+'tt_b/create_times.json')); lt=json.load(open(base+'tt_b/lifetime.json'))
found={}
for l in open(base+'tt_b/daily_found.txt'):
    if l.startswith('#') or not l.strip(): continue
    p=l.split(); found[p[0]]=p
extra={}
try: extra=json.load(open(base+'tt_b/extra_notes.json'))
except Exception: pass
out={}
for i in ids:
    c=ct[i]; typ='Upgraded Smart+ ad' if c['type']=='smart_plus' else 'Ad'
    rep='report/integrated/get AUCTION_AD dims ad_id_v2+stat_time_day (filter ad_ids_v2)' if c['type']=='smart_plus' else 'report/integrated/get AUCTION_AD dims ad_id+stat_time_day (filter ad_ids)'
    head=f"{typ} create_time {c['create_time']} UTC, status {c['op']}. Lifetime impressions {lt[i]}."
    if i in found:
        p=found[i]
        note=f"{head} Daily {rep} over {p[3]}..{p[4]} (Asia/Riyadh days, window starts before creation): no impressions before {p[1]}; first day {p[1]} = {p[2]}."
        out[i]={'first_date':p[1],'first_day_impressions':int(p[2]),'status':'served','note':note}
    elif lt[i]==0:
        out[i]={'first_date':None,'first_day_impressions':None,'status':'never_served','note':head[:-1]+' (query_lifetime=true).'}
    else:
        out[i]={'first_date':None,'first_day_impressions':None,'status':'unknown','note':head+' Daily first-day check pending.'}
    if i in extra:
        out[i]['note']+=' '+extra[i]
json.dump(out, open(base+'serving_out_tiktok_7338057963233443842_b.json','w'), indent=1)
from collections import Counter
print(len(out), Counter(v['status'] for v in out.values()))
