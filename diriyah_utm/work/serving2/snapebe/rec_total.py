import json, sys, os
# usage: rec_total.py source window "id:imps,id:imps"
P='totals.json'
t=json.load(open(P)) if os.path.exists(P) else {}
src, win, series = sys.argv[1:4]
for kv in [x for x in series.split(',') if x]:
    i,v=kv.split(':'); t.setdefault(i,[]).append({'src':src,'win':win,'imps':int(v)})
json.dump(t,open(P,'w'),indent=1)
print('ok', len(t))
