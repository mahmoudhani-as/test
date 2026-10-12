import json, sys, os
# usage: recp.py ad ws we "d:v;d:v;..."  (per-ad GET /v1/ads/{id}/stats DAY; full series incl zeros unless noted)
P='perad.json'
p=json.load(open(P)) if os.path.exists(P) else {}
ad, ws, we, series = sys.argv[1:5]
note = sys.argv[5] if len(sys.argv)>5 else 'explicit zeros (omit_empty not set)'
pts=[[kv.split(':')[0],int(kv.split(':')[1])] for kv in series.split(';') if kv]
p.setdefault(ad,[]).append({'window':[ws,we],'days':pts,'note':note})
json.dump(p,open(P,'w'),indent=1)
nz=[d for d in pts if d[1]>0]
print(ad[:8],'days',len(pts),'first>0',nz[0] if nz else None)
