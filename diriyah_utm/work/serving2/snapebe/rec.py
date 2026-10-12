import json, sys, os
# usage: rec.py src ws we "ad=d1:v1;d2:v2|ad2=..."   (omit_empty: listed days are the only days with impressions>0 in window)
P='obs.json'
obs=json.load(open(P)) if os.path.exists(P) else {}
src, ws, we, blob = sys.argv[1:5]
for part in [p for p in blob.split('|') if p]:
    ad, series = part.split('=')
    pts=[]
    for kv in [x for x in series.split(';') if x]:
        d,v=kv.split(':'); pts.append([d,int(v)])
    obs.setdefault(ad,[]).append({'src':src,'window':[ws,we],'days':pts})
json.dump(obs,open(P,'w'),indent=1)
print('recorded', len(obs))
