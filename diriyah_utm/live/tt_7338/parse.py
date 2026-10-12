import json,sys
def load(path):
    raw=open(path).read()
    try:
        d=json.loads(raw)
    except Exception:
        d=None
    if isinstance(d,list) and d and isinstance(d[0],dict) and 'text' in d[0]:
        t=json.loads(d[0]['text'])
    else:
        t=d
    inner=t['data']['data']['data']
    return t, inner
if __name__=='__main__':
    for p in sys.argv[1:]:
        t,inner=load(p)
        lst=inner['list']
        trunc=t.get('meta',{}).get('mcp_output_budget')
        print(p, t['data']['data']['code'], inner['page_info'], len(lst), sum(isinstance(x,str) for x in lst), 'TRUNC' if trunc else '')
