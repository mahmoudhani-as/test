import json, sys, os
# usage: rec.py ad_id win_start win_end "d1:v1,d2:v2,..." [extra note]
P='obs.json'
obs=json.load(open(P)) if os.path.exists(P) else {}
ad, ws, we, series = sys.argv[1:5]
extra = sys.argv[5] if len(sys.argv)>5 else ''
pts=[]
for kv in series.split(','):
    d,v=kv.split(':'); pts.append([d,int(v)])
obs.setdefault(ad,[]).append({'window':[ws,we],'days':pts,'extra':extra})
json.dump(obs,open(P,'w'),indent=1)
print(ad, 'recorded', len(pts),'days')
