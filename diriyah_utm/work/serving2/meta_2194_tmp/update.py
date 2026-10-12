import json,glob
d='/tmp/claude-0/-home-user-test/0a7a4347-50ae-5891-a613-ee320c5ab4bb/scratchpad/diriyah_utm/work/serving2/'
t=d+'meta_2194_tmp/'
ids=json.load(open(d+'serving_in_meta_2194833637927644.json'))
first=json.load(open(t+'first_month.json'))
meta=json.load(open(t+'ad_meta.json'))
daily={}
for f in sorted(glob.glob(t+'daily_*.json')):
    for a,dt,imp in json.load(open(f)):
        if a not in daily or dt<daily[a][0]: daily[a]=(dt,imp)
extra={}
try: extra=json.load(open(t+'extra.json'))
except FileNotFoundError: pass
out=json.load(open(d+'serving_out_meta_2194833637927644.json'))
for a in ids:
    m=meta.get(a,{})
    mi=f" Ad created {m['created_time'][:10]}, effective_status {m['effective_status']}." if m else ""
    if a in daily:
        dt,imp=daily[a]
        assert dt[:7]==first[a], (a,dt,first[a])
        out[a]={"first_date":dt,"first_day_impressions":int(imp),"status":"served","note":f"Account tz Asia/Riyadh. First month {first[a]} from monthly ad insights 2023-10-01..2026-10-12 (filter incl. ARCHIVED/DELETED effective_status; account created 2026-04-14, so this covers the ad's whole life); exact day confirmed with time_increment=1 daily insights (daily rows sum to the monthly total).{mi}"}
    elif a in extra:
        out[a]=extra[a]
json.dump(out,open(d+'serving_out_meta_2194833637927644.json','w'),indent=1)
from collections import Counter
print(Counter(v['status'] for v in out.values()), len(out))
print('pending daily:',[a for a in first if a not in daily])
