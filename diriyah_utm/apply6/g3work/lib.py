import json
from urllib.parse import urlsplit, parse_qsl
D='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
W=D+'/apply6/g3work'
def load_results(path):
    raw=json.load(open(path))
    txt=raw[0]['text'] if isinstance(raw,list) else raw
    j=json.loads(txt)
    data=j['data']['data']['data']
    res=[r for r in data.get('results',[]) if isinstance(r,dict)]
    trunc=[r for r in data.get('results',[]) if not isinstance(r,dict)]
    return res,trunc,j
def rows_by_ad(paths):
    out={}
    for p in paths:
        res,trunc,j=load_results(p)
        for r in res:
            out[r['adGroupAd']['ad']['id']]=r
    return out
def landing(r):
    ad=r['adGroupAd']['ad']
    fu=ad.get('finalUrls',[])
    u=fu[0] if fu else None
    suf=ad.get('finalUrlSuffix')
    if suf:
        u=u+('&' if '?' in u else '?')+suf
    return u
def norm(u):
    if u is None: return None
    s=urlsplit(u)
    return (s.scheme,s.netloc,s.path,s.fragment,tuple(sorted(parse_qsl(s.query,keep_blank_values=True))))
def same(a,b):
    return a is not None and b is not None and norm(a)==norm(b)
