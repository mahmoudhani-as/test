import json, sys, os
# usage: rec.py ad_id win_start win_end start_date "v1,v2,..." [extra note]  (consecutive daily values from start_date)
from datetime import date, timedelta
P=os.path.join(os.path.dirname(os.path.abspath(__file__)),'obs.json')
obs=json.load(open(P)) if os.path.exists(P) else {}
ad, ws, we, sd, series = sys.argv[1:6]
extra = sys.argv[6] if len(sys.argv)>6 else ''
d=date.fromisoformat(sd); pts=[]
for v in series.split(','):
    pts.append([d.isoformat(),int(v)]); d+=timedelta(days=1)
assert pts[-1][0] == (date.fromisoformat(we)-timedelta(days=1)).isoformat(), ('window mismatch', pts[-1][0], we)
obs.setdefault(ad,[]).append({'window':[ws,we],'days':pts,'extra':extra})
json.dump(obs,open(P,'w'),indent=1)
print(ad, 'recorded', len(pts),'days; first>0:', next((p for p in pts if p[1]>0),None))
