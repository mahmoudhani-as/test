import json,glob,sys
sys.path.insert(0,'.')
from parse import load
ads={}; order=[]
def norm_utm(u):
    if not u: return None
    out=[]
    for p in u:
        if isinstance(p,dict): out.append([p.get('key'),p.get('value')])
        else: out.append(list(p))
    return out
for p in ['raw/manual_p1.json']+[f'raw/manual_s45_p{i}.json' for i in range(5,12)]+['raw/manual_s45_p2.txt','raw/manual_s45_p3.txt']:
    t,inner=load(p)
    for x in inner['list']:
        assert isinstance(x,dict)
        x=dict(x); x['utm_params']=norm_utm(x.get('utm_params'))
        if x['ad_id'] in ads and ads[x['ad_id']]!=x: print('DIFF',x['ad_id'])
        ads[x['ad_id']]=x
for p in ['man_s45_p4.jsonl','man_s45_p12.jsonl','man_s45_p13.jsonl']:
    for l in open(p):
        x=json.loads(l); x['utm_params']=norm_utm(x.get('utm_params'))
        if x['ad_id'] in ads and ads[x['ad_id']]!=x: print('DIFF',x['ad_id'])
        ads[x['ad_id']]=x
print(len(ads))
import collections
keys=collections.Counter(k for a in ads.values() for k in a)
print(keys)
json.dump(ads,open('manual_ads.json','w'),ensure_ascii=False)
