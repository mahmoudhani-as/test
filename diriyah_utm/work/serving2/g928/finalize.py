import json
d=json.load(open('../serving_in_google_9282725829.json'))
st=json.load(open('state.json')); mo=json.load(open('months.json'))
firsts={}
for l in open('firsts.txt'):
    p=l.split(); firsts[p[0]]=(p[1],int(p[2]),p[3])
out={}
for a in d:
    if a in st['served_life']:
        fm=mo['first_month'][a]; life=st['served_life'][a]
        if a in firsts:
            dt,imp,chk=firsts[a]
            out[a]={"first_date":dt,"first_day_impressions":imp,"status":"served","note":f"TZ Asia/Riyadh. Daily GAQL (ad_group_ad, impressions>0) first day {dt}; first month {fm} confirmed by monthly query over 2018-01-01..2026-10-12 (no earlier month); daily sum of first month equals monthly total ({chk.split('=')[1]}); lifetime impr {life}"}
        else:
            out[a]={"first_date":None,"first_day_impressions":None,"status":"served","note":f"IN PROGRESS: first month {fm} (lifetime impr {life}); day not yet confirmed"}
    elif a in st['tail_never']:
        out[a]={"first_date":None,"first_day_impressions":None,"status":"never_served","note":"0 impressions 2018-01-01..2026-10-12 at ad level (impressions>0 query and unfiltered segments.year query both returned no rows); parent campaign PAUSED with 0 lifetime impressions at campaign level"}
    else:
        out[a]={"first_date":None,"first_day_impressions":None,"status":"never_served","note":"0 impressions 2018-01-01..2026-10-12 at ad level (impressions>0 query and unfiltered segments.year query both returned no rows); ad exists in ad_group_ad"}
json.dump(out,open('../serving_out_google_9282725829.json','w'),indent=1)
from collections import Counter
print(len(out), Counter(v['status'] for v in out.values()), 'with_date', sum(1 for v in out.values() if v['first_date']))
