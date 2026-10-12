import json, sys
def load_results(path):
    raw = json.load(open(path))
    if isinstance(raw, list):
        txt = ''.join(x.get('text','') for x in raw if x.get('type')=='text')
        obj = json.loads(txt)
    else:
        obj = raw
    # navigate
    d = obj
    for k in ('data','data','data'):
        if isinstance(d, dict) and k in d:
            d = d[k]
    if isinstance(d, dict) and 'results' in d:
        return d['results'], obj
    raise SystemExit('no results: ' + json.dumps(obj)[:2000])
