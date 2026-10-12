import json
D='/tmp/claude-0/-home-user-test/0a7a4347-50ae-5891-a613-ee320c5ab4bb/scratchpad/diriyah_utm/work/serving2/'
ids=json.load(open(D+'serving_in_tiktok_7338057963233443842_a.json'))
ct=json.load(open(D+'tt_a/create_times.json'))
lt=json.load(open(D+'tt_a/lifetime.json'))
found=json.load(open(D+'tt_a/found.json'))
never=json.load(open(D+'tt_a/never.json'))
ver=json.load(open(D+'tt_a/verified.json'))
out={}
for i in ids:
    c=ct[i]; L=lt[i]
    if i in found:
        d,imp,win=found[i]
        out[i]={"first_date":d,"first_day_impressions":imp,"status":"served",
          "note":f"create_time {c} UTC (advertiser tz Asia/Riyadh, UTC+3). Daily report/integrated/get (AUCTION_AD, ad_id+stat_time_day) checked continuously {win} (Asia/Riyadh days); no impressions before {d}. Lifetime impressions {L} (query_lifetime). "+ver.get(i,"")}
    elif i in never:
        out[i]={"first_date":None,"first_day_impressions":None,"status":"never_served","note":f"create_time {c} UTC. Lifetime impressions 0 (query_lifetime). "+never[i]}
    else:
        out[i]={"first_date":None,"first_day_impressions":None,"status":"unknown","note":f"create_time {c} UTC. Lifetime impressions {L}. Daily check pending."}
json.dump(out,open(D+'serving_out_tiktok_7338057963233443842_a.json','w'),indent=1)
import collections
print(len(out), collections.Counter(v['status'] for v in out.values()))
