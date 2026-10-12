import json,sys
def load(p):
    raw=json.load(open(p))
    txt=raw[0]['text'] if isinstance(raw,list) else raw
    d=json.loads(txt) if isinstance(txt,str) else txt
    budget=(d.get('meta') or {}).get('mcp_output_budget')
    inner=d['data']
    return d, inner, budget
