import json, datetime as dt
ids=json.load(open('../serving_in_x_18ce55o46uh.json'))
c=json.load(open('created.json')); ae=json.load(open('ae_first.json')); li=json.load(open('lineitems.json'))
log=json.load(open('daily_log.json'))
tz=dt.timedelta(hours=3)
P=lambda s: dt.datetime.strptime(s,'%Y-%m-%dT%H:%M:%SZ')
loc=lambda s: (P(s)+tz)
D=lambda s: dt.date.fromisoformat(s)
out={}
for i in ids:
    days={}  # date -> impressions (ALL_ON_TWITTER)
    covered=[]; pn_any=False; pn_cov=[]
    for e in log:
        if i not in e['data']: continue
        s=D(e['start']); v=e['data'][i]
        if e['placement']=='ALL_ON_TWITTER':
            covered.append(s)
            for k in range(7):
                days[s+dt.timedelta(days=k)] = (v[k] if v is not None else None)
        else:
            pn_cov.append(s)
            if v is not None and any(x and x>0 for x in v): pn_any=True
    cd=loc(c[i][0]).date()
    first=None
    for d in sorted(days):
        if days[d] and days[d]>0: first=d; break
    # verify continuous coverage from creation day to first day
    gaps=[]
    if first:
        d=cd
        while d<first:
            if d not in days: gaps.append(str(d))
            d+=dt.timedelta(days=1)
    lin=c[i][1]
    wins=', '.join(f"{s}..{s+dt.timedelta(days=6)}" for s in sorted(covered))
    zero_note = (f"no impressions {cd}..{first-dt.timedelta(days=1)} (daily rows null/0)" if first and first>cd else "first day = creation day")
    note=(f"Daily ALL_ON_TWITTER stats (ENGAGEMENT, DAY, Asia/Riyadh days) windows [{wins}]; first impressions>0 on {first}; {zero_note}. "
          f"PUBLISHER_NETWORK daily stats over same windows: no data. "
          f"promoted_tweet created_at {c[i][0]} (local {loc(c[i][0]):%Y-%m-%d %H:%M}); active_entities first activity_start_time {ae[i]} (local {loc(ae[i]):%Y-%m-%d %H:%M}); "
          f"line item {lin} placements {li[lin][0]}, start {li[lin][1]}.")
    if gaps: note+=f" COVERAGE GAP {gaps}"
    if pn_any: note+=" PN HAS DATA"
    out[i]={"first_date": str(first) if first else None, "first_day_impressions": days[first] if first else None,
            "status": "served" if first else "unknown", "note": note}
json.dump(out, open('../serving_out_x_18ce55o46uh.json','w'), indent=1)
import collections
print(len(out), collections.Counter(v['status'] for v in out.values()))
for i,v in out.items():
    flag = ' <-- first day after creation' if v['first_date']!=str(loc(c[i][0]).date()) else ''
    mflag = ' MONTH DIFFERS FROM CREATION' if v['first_date'][:7]!=str(loc(c[i][0]).date())[:7] else ''
    adiff = '' if v['first_date']==str(loc(ae[i]).date()) else f' AE-local {loc(ae[i]).date()}'
    print(i, v['first_date'], v['first_day_impressions'], flag, mflag, adiff, 'GAP' if 'GAP' in v['note'] else '')
