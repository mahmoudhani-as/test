import json,sys
p=sys.argv[1]
d=json.load(open(p))
t=d[0]['text'] if isinstance(d,list) else d
j=json.loads(t)
inner=j['data']['data']['data']
res=inner['results']
real=[r for r in res if isinstance(r,dict)]
trunc=[r for r in res if not isinstance(r,dict)]
print('items',len(real),'trunc',trunc,'total',inner.get('totalResultsCount'),'meta',j.get('meta',{}).get('mcp_output_budget'))
if real and 'adGroupAd' in real[0]:
    ids=[int(r['adGroupAd']['ad']['id']) for r in real]
    print('first',ids[0],'last',ids[-1],'sorted',ids==sorted(ids))
