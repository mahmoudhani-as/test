import json,glob,sys
d='/tmp/claude-0/-home-user-test/0a7a4347-50ae-5891-a613-ee320c5ab4bb/scratchpad/diriyah_utm/work/serving2/'
t=d+'meta_1198_tmp/'
ids=json.load(open(d+'serving_in_meta_1198625455580757.json'))
first=json.load(open(t+'first_month.json'))
daily={}
for f in sorted(glob.glob(t+'daily_*.json')):
    for a,dt,imp in json.load(open(f)):
        if a not in daily or dt<daily[a][0]: daily[a]=(dt,imp)
extra={}
try: extra=json.load(open(t+'extra.json'))
except FileNotFoundError: pass
out=json.load(open(d+'serving_out_meta_1198625455580757.json'))
for a in ids:
    if a in daily:
        dt,imp=daily[a]
        assert dt[:7]==first[a], (a,dt,first[a])
        out[a]={"first_date":dt,"first_day_impressions":int(imp),"status":"served","note":f"Confirmed with daily insights (time_increment=1) for {first[a]}; monthly insights show no impressions in any earlier month back to 2023-09-13 (Meta 37-month limit; account created 2026-01-12). Account tz Asia/Riyadh."}
    elif a in extra:
        out[a]=extra[a]
json.dump(out,open(d+'serving_out_meta_1198625455580757.json','w'),indent=1)
from collections import Counter
print(Counter(v['status'] for v in out.values()), len(out))
print('pending daily:',[a for a in first if a not in daily])
