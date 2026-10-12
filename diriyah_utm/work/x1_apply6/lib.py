import json, re
from urllib.parse import urlsplit, parse_qsl
W='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/work/x1_apply6'
IN='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/in_x_1.json'
OUT='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/out_x_1.jsonl'
def load_cards(path):
    raw=json.load(open(path))
    txt=raw[0]['text'] if isinstance(raw,list) else json.dumps(raw)
    d=json.loads(txt)
    inner=d['data']['data']
    data=inner['data']
    if isinstance(data,dict): data=[data]
    return {c['id']:c for c in data}
def slot_get(card, slot):
    m=re.fullmatch(r'card\.components\[(\d+)\]\.destination\.url', slot)
    if m: return card['components'][int(m.group(1))]['destination']['url']
    m=re.fullmatch(r'card\.slides\[(\d+)\]\[(\d+)\]\.destination\.url', slot)
    if m: return card['slides'][int(m.group(1))][int(m.group(2))]['destination']['url']
    raise ValueError(slot)
def same_url(a,b):
    A=urlsplit(a); B=urlsplit(b)
    return (A.scheme,A.netloc,A.path,A.fragment)==(B.scheme,B.netloc,B.path,B.fragment) and sorted(parse_qsl(A.query,keep_blank_values=True))==sorted(parse_qsl(B.query,keep_blank_values=True))
def classify(cur, ch):
    if cur==ch['new'] or same_url(cur, ch['new']): return 'AlreadyFixed'
    if cur==ch['now'] or cur in ch['alt_now']: return 'Write'
    return 'Skipped'
def build_payload(card, ch_list):
    # send name + components exactly as read, minus read-only media_metadata, with only the listed urls replaced
    comps=[]
    for c in card['components']:
        c2={k:v for k,v in c.items() if k!='media_metadata'}
        if 'destination' in c2: c2['destination']=dict(c2['destination'])
        comps.append(c2)
    body={'name':card['name'],'components':comps}
    for ch in ch_list:
        m=re.fullmatch(r'card\.components\[(\d+)\]\.destination\.url', ch['slot'])
        body['components'][int(m.group(1))]['destination']['url']=ch['new']
    return body
