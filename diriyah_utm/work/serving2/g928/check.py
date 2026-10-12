import json,sys
from collections import defaultdict
mo=json.load(open('months.json'))
first=mo['first_month']; fmi={}
for a,m,i in mo['rows']:
    if m==first[a]: fmi[a]=i
f=sys.argv[1]; ids=sys.argv[2].split(',')
tot=defaultdict(int); fd={}
for l in open(f):
    a,dt,i=l.split(); i=int(i); tot[a]+=i
    if a not in fd or dt<fd[a][0]: fd[a]=(dt,i)
out=open('firsts.txt','a')
for a in ids:
    ok = a in fd and tot[a]==fmi[a] and fd[a][0][:7]==first[a]
    print(a, fd.get(a), tot[a], fmi[a], 'OK' if ok else 'MISMATCH')
    if ok: out.write(f"{a} {fd[a][0]} {fd[a][1]} daysum={tot[a]}=month\n")
print('extra ids in file', set(tot)-set(ids))
