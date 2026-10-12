import json,sys
d=json.load(open(sys.argv[1]));j=json.loads(d[0]['text'])
r=j['data']['data']['data'].get('results',[])
key=sys.argv[2]
print(len(r),[x for x in r if not isinstance(x,dict)],j['meta'].get('mcp_output_budget'))
real=[x for x in r if isinstance(x,dict)]
if real:
    print('first',real[0][key]['id'],'last',real[-1][key]['id'])
    import collections
    c=collections.Counter(x[key]['id'] for x in real); print('last-key count',c[real[-1][key]['id']])
