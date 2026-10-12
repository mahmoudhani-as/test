import json, datetime as dt
OUT='/tmp/claude-0/-home-user-test/0a7a4347-50ae-5891-a613-ee320c5ab4bb/scratchpad/diriyah_utm/work/serving2/chk/serving_out_snapchat_ebe8d66e0e3e4b719d375c53118d6481.json'
ids=json.load(open('../chk/serving_in_snapchat_ebe8d66e0e3e4b719d375c53118d6481.json'))
m={l.split()[0]:l.split()[1:] for l in open('meta.tsv') if l.strip()}
o=json.load(open('obs.json')); t=json.load(open('totals.json'))
try: p=json.load(open('perad.json'))
except Exception: p={}
def loc(z): return dt.datetime.fromisoformat(z.replace('Z','+00:00'))+dt.timedelta(hours=3)
res={}
for ad in ids:
    c,sq=m[ad]; cl=loc(c)
    tots=t.get(ad,[]); tot=max([x['imps'] for x in tots]) if tots else None
    sqdays=sorted(d for w in o.get(ad,[]) for d in w['days'] if d[1]>0)
    pdays=sorted(d for w in p.get(ad,[]) for d in w['days'] if d[1]>0)
    base=f"Ad account timezone Asia/Riyadh (UTC+3); ad created_at {c} (local {cl.strftime('%Y-%m-%d %H:%M')}); ad squad {sq}. "
    if tot==0 and not sqdays and not pdays:
        srcs='; '.join(f"{x['src']} {x['win']}={x['imps']}" for x in tots)
        res[ad]={'first_date':None,'first_day_impressions':None,'status':'never_served',
                 'note':base+f"Lifetime impressions = 0 verified: {srcs} (ad absent/zero in squad breakdown=ad TOTAL, i.e. zero for whole life from creation day to 2026-10-13 00:00 local; data finalized to 2026-10-12T06:00Z); also no day with impressions>0 in squad breakdown=ad DAY omit_empty series."}
        continue
    if not sqdays:
        res[ad]={'first_date':None,'first_day_impressions':None,'status':'unknown','note':base+'no daily data collected yet'}; continue
    f=sqdays[0]
    note=base+(f"Daily impressions via GET /v1/adsquads/{{id}}/stats breakdown=ad granularity=DAY omit_empty=true (zero days omitted), windows starting at the ad creation day: first day with impressions>0 = {f[0]} ({f[1]})")
    nxt=[d for d in sqdays if d[0]>f[0]][:1]
    if nxt: note+=f", next {nxt[0][0]} ({nxt[0][1]})"
    note+=f". Lifetime impressions {tot} (squad breakdown=ad TOTAL creation day..2026-10-13)."
    if pdays:
        pw=p[ad][0]['window']; zeros=[d[0] for w in p[ad] for d in w['days'] if d[1]==0 and d[0]<pdays[0][0]]
        agree = pdays[0]==f
        note+=f" Cross-check GET /v1/ads/{{id}}/stats granularity=DAY (explicit zero rows) {pw[0]}..{pw[1]}: first>0 = {pdays[0][0]} ({pdays[0][1]})" + (f", {len(zeros)} zero days before it from creation day" if zeros else ", first day = creation day") + (" - MATCH." if agree else " - MISMATCH!")
        if not agree: print('MISMATCH',ad,f,pdays[0])
    else:
        note+=" (first day equals creation day)" if f[0]==str(cl.date()) else ""
    if f[0][:7]!=str(cl.date())[:7]: note+=f" NOTE: first-served month {f[0][:7]} differs from creation month {str(cl.date())[:7]}."
    res[ad]={'first_date':f[0],'first_day_impressions':f[1],'status':'served','note':note}
json.dump(res,open(OUT,'w'),indent=1)
from collections import Counter
print(len(res), Counter(v['status'] for v in res.values()), 'perad checked', sum(1 for a in ids if a in p))
