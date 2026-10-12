import json, os
# Build output from meta.tsv, totals.json, obs.json (daily observations), ns.json (never-served verifications)
OUT='../serving_out_snapchat_623ccdb3d54642e8908289ff8b59cfd1.json'
ids=json.load(open('../serving_in_snapchat_623ccdb3d54642e8908289ff8b59cfd1.json'))
meta={}
for line in open('meta.tsv'):
    p=line.rstrip('\n').split('\t'); meta[p[0]]={'created':p[1],'squad':p[2],'status':p[3],'review':p[4],'name':p[5]}
tot=json.load(open('totals.json'))
obs=json.load(open('obs.json')) if os.path.exists('obs.json') else {}
ns=json.load(open('ns.json')) if os.path.exists('ns.json') else {}
from datetime import datetime, timedelta, timezone
TZ=timezone(timedelta(hours=3))
out={}
for i in ids:
    m=meta[i]; c=datetime.fromisoformat(m['created'].replace('Z','+00:00')).astimezone(TZ)
    base=f"Ad account timezone Asia/Riyadh (UTC+3). Ad '{m['name'].strip()}' (status {m['status']}, review {m['review']}). Created {m['created']} (local {c:%Y-%m-%d %H:%M})."
    if i in ns:
        out[i]={'first_date':None,'first_day_impressions':None,'status':'never_served','note':base+' '+ns[i]}
        continue
    if i in obs:
        days={}
        wins=[]
        for o in obs[i]:
            wins.append(o['window'])
            for d,v in o['days']: days[d]=v
        pos=sorted(d for d,v in days.items() if v>0)
        if pos:
            fd=pos[0]
            # check all days from creation local day to fd-1 were observed as 0
            cd=c.date(); fdd=datetime.strptime(fd,'%Y-%m-%d').date()
            gaps=[]; d=cd
            while d<fdd:
                ds=d.isoformat()
                if ds not in days: gaps.append(ds)
                d+=timedelta(days=1)
            extra=' | '.join(o.get('extra','') for o in obs[i] if o.get('extra'))
            seq=sorted(days.items())
            # show up to first 10 days around first date
            idx=[k for k,(d,_) in enumerate(seq) if d==fd][0]
            snippet=', '.join(f"{d[5:]}:{v:,}" for d,v in seq[max(0,idx-3):idx+5])
            wtxt='; '.join(f"{a}..{b}" for a,b in wins)
            note=(base+f" GET /v1/ads/{{id}}/stats granularity=DAY fields=impressions windows {wtxt} (local days, end exclusive). "
                  f"Zero impressions every day from creation day {cd} to {fdd-timedelta(days=1)}" if fdd>cd else base+f" GET /v1/ads/{{id}}/stats granularity=DAY fields=impressions windows {wtxt} (local days, end exclusive). First >0 on creation day (earliest possible local day, since the ad did not exist before created_at)")
            if fdd>cd: note+=f"; first >0 on {fd}."
            else: note+='.'
            note+=f" Daily around first day: {snippet}. Lifetime TOTAL (account stats breakdown=ad 2023-09-20..2026-10-13) = {tot[i]['acct_total']:,} impr."
            if extra: note+=' '+extra
            if gaps: note+=f" WARNING unobserved days before first date: {gaps[:5]}"
            out[i]={'first_date':fd,'first_day_impressions':days[fd],'status':'served' if not gaps else 'unknown','note':note}
            continue
    t=tot[i]
    out[i]={'first_date':None,'first_day_impressions':None,'status':'unknown','note':base+f" PENDING daily check. Lifetime TOTAL impressions {t['acct_total']:,}."}
json.dump(out,open(OUT,'w'),indent=1)
from collections import Counter
print(Counter(v['status'] for v in out.values()), len(out))
