import json
ids=json.load(open('../chk/serving_in_tiktok_7338074303931449345.json'))
ct=json.load(open('create_times.json'))
lt=json.load(open('lifetime.json'))
df=json.load(open('daily_first.json'))
extra={}
try: extra=json.load(open('extra.json'))
except Exception: pass
out={}
for i in ids:
    if i in extra:
        out[i]=extra[i]; continue
    if i in df:
        d,n,note=df[i]
        out[i]={"first_date":d,"first_day_impressions":n,"status":"served","note":f"TikTok daily report (Asia/Riyadh); create_time {ct[i]}; lifetime impressions {lt.get(i)}; {note}"}
    else:
        out[i]={"first_date":None,"first_day_impressions":None,"status":"unknown","note":"in progress"}
json.dump(out,open('../chk/serving_out_tiktok_7338074303931449345.json','w'),indent=1)
import collections
print(collections.Counter(v['status'] for v in out.values()), len(out))
