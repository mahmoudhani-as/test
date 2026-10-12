import json, unicodedata
from urllib.parse import urlsplit, parse_qsl
W='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/'
T=W+'tt9_work/'
INP=json.load(open(W+'in_tiktok_9.json'))
INPD={u['unit']:u for u in INP}
EXCL=json.load(open('/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/work/excl_platform_refused_v2.json'))
PIX={7347671240183693330:"7347671240183693330", 7610705877289091089:"7610705877289091089"}  # exact, pixel/list req 20261012222006D041C4FD11D0938CEAE8

def load_list(path):
    j=json.loads(open(path,encoding='utf-8').read())
    assert j['success'] and j['data']['data']['code']==0, j
    lst=j['data']['data']['data']['list']
    for a in lst:
        assert isinstance(a,dict), 'truncated item in '+path
        assert '__mcp_truncated_keys' not in a, 'truncated keys in '+path
    return {a['ad_id']:a for a in lst}, j['data']['data']['request_id']

def parts(u):
    s=urlsplit(u)
    return (s.scheme,s.netloc,s.path,s.fragment), sorted(parse_qsl(s.query, keep_blank_values=True))

def equiv(a,b):
    return parts(a)==parts(b)

def effective(a):
    """full landing URL incl. separately stored utm_params (keys missing from the URL are appended)"""
    url=a.get('landing_page_url') or ''
    q=dict(parse_qsl(urlsplit(url).query, keep_blank_values=True))
    extra=[]; conflict=[]
    for x in (a.get('utm_params') or []):
        k,v=x['key'],x['value']
        if k in q:
            if q[k]!=v: conflict.append((k,q[k],v))
        else: extra.append((k,v))
    eff=url
    if extra:
        eff=url+('&' if '?' in url else '?')+'&'.join(f'{k}={v}' for k,v in extra)
    return eff, extra, conflict

def utm_from(new):
    q=parse_qsl(urlsplit(new).query, keep_blank_values=True)
    assert all(k.startswith('utm_') and k!='utm_id' for k,v in q), q
    assert len(set(k for k,v in q))==len(q)
    return [{"key":k,"value":v} for k,v in q]

def pixel_exact(v):
    if v in (None,0,'0',''): return None
    for exact,s in PIX.items():
        if float(v)==float(exact): return s
    raise SystemExit('UNKNOWN PIXEL %r'%v)

def safe_dumps(o):
    s=json.dumps(o,ensure_ascii=False)
    r=[]
    for c in s:
        cat=unicodedata.category(c)
        if ord(c)>0xFFFF:
            v=ord(c)-0x10000; r.append('\\u%04x\\u%04x'%(0xD800+(v>>10),0xDC00+(v&0x3FF)))
        elif ord(c)>127 and (cat in ('Cf','Cc','Zs','Mn','Me','Co','Cs','So','Sk') or not cat.startswith('L')):
            r.append('\\u%04x'%ord(c))
        else:
            r.append(c)
    t=''.join(r)
    assert json.loads(t)==o
    return t

def text_notes(txt):
    txt=txt or ''
    return {"trailing_ws":txt!=txt.rstrip(),"leading_ws":txt!=txt.lstrip(),
            "nonprint":sorted({'U+%04X'%ord(c) for c in txt if unicodedata.category(c) in ('Cf','Cc','Zs','Mn') and c!=' '})}
