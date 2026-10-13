import json, sys
def load(path):
    t = open(path, encoding='utf-8').read().strip()
    # file may be a JSON list of content blocks or the raw text
    try:
        j = json.loads(t)
    except Exception as e:
        print('JSON parse fail', e); raise
    if isinstance(j, list) and j and isinstance(j[0], dict) and 'text' in j[0]:
        j = json.loads(j[0]['text'])
    return j
def inner(j):
    d = j['data']['data']
    return d
if __name__ == '__main__':
    for p in sys.argv[1:]:
        j = load(p)
        d = inner(j)
        lst = d['data']['list']
        trunc = [x for x in lst if isinstance(x, str)]
        print(p.split('/')[-1], 'code', d.get('code'), 'req', d.get('request_id'), 'items', len(lst), 'page_info', d['data'].get('page_info'), 'trunc', trunc, 'budget', j.get('meta', {}).get('mcp_output_budget'))
