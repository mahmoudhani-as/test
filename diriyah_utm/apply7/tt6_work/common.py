import json, unicodedata, os
from urllib.parse import urlsplit, parse_qsl
ROOT='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/'
W=ROOT+'apply7/'
T=W+'tt6_work/'
TR='/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/wf_e62cae8e-5aa/agent-aa09c901fa46a56c7.jsonl'
INP=json.load(open(W+'in_tiktok_6.json'))
INPD={u['unit']:u for u in INP}
OUT=W+'out_tiktok_6.jsonl'
EXCL=json.load(open(ROOT+'work/excl_platform_refused_v2.json'))

def excluded(ad, slot):
    return any(e['platform']=='tiktok' and str(e.get('ad_id'))==str(ad) and e['slot']==slot for e in EXCL)

def parts(u):
    s=urlsplit(u)
    return (s.scheme,s.netloc,s.path,s.fragment), sorted(parse_qsl(s.query, keep_blank_values=True))

def equiv(a,b):
    return parts(a)==parts(b)

def eff_url(url, utm_params):
    """full landing URL incl. separately stored utm_params (keys missing from the URL are appended)"""
    url=url or ''
    q=dict(parse_qsl(urlsplit(url).query, keep_blank_values=True))
    extra=[]; conflict=[]
    for x in (utm_params or []):
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

def tool_results(marker=None):
    """all tool_result texts in my transcript (optionally containing marker), in order"""
    res=[]
    for line in open(TR, encoding='utf-8'):
        try: e=json.loads(line)
        except Exception: continue
        content=(e.get('message') or {}).get('content')
        if not isinstance(content, list): continue
        for c in content:
            if not isinstance(c, dict) or c.get('type')!='tool_result': continue
            cc=c.get('content')
            texts=[x.get('text','') for x in cc if isinstance(x,dict) and x.get('type')=='text'] if isinstance(cc,list) else [cc if isinstance(cc,str) else '']
            for t in texts:
                if marker is None or marker in t: res.append((c.get('tool_use_id'),t))
    return res

def tool_uses(name_suffix='tiktok_native_action'):
    uses=[]
    for line in open(TR, encoding='utf-8'):
        try: e=json.loads(line)
        except Exception: continue
        content=(e.get('message') or {}).get('content')
        if not isinstance(content, list): continue
        for c in content:
            if isinstance(c,dict) and c.get('type')=='tool_use' and c.get('name','').endswith(name_suffix):
                uses.append((c['id'], c.get('input') or {}))
    return uses

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
