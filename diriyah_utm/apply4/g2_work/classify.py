import json, sys
from urllib.parse import urlsplit, parse_qsl
def norm(u):
    s=urlsplit(u); return (s.scheme,s.netloc,s.path,s.fragment,sorted(parse_qsl(s.query,keep_blank_values=True)))
d=json.load(open('in_google_2.json'))
live=json.load(open(sys.argv[1]))
out={}
for u in d:
    c=u['changes'][0]; cur=live.get(u['unit'])
    if cur is None: cls='MISSING'
    elif norm(cur)==norm(c['new']): cls='AlreadyFixed'
    elif cur==c['now']: cls='now'
    elif cur in c['alt_now']: cls='alt_now'
    else: cls='Skipped'
    out[u['unit']]=cls
    print(u['unit'], cls)
    if cls=='Skipped':
        print('   cur:',cur); print('   now:',c['now']); [print('   alt:',a) for a in c['alt_now']]; print('   new:',c['new'])
from collections import Counter; print(Counter(out.values()))
json.dump(out,open('g2_work/classes.json','w'),indent=1)
