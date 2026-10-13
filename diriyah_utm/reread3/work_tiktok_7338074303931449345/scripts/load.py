import json
def load(path):
    j = json.load(open(path, encoding='utf-8'))
    if isinstance(j, list) and j and isinstance(j[0], dict) and 'text' in j[0]:
        j = json.loads(''.join(b.get('text', '') for b in j))
    return j
def info(path):
    j = load(path)
    d = j['data']['data']
    lst = d['data']['list']
    t = json.dumps(j, indent=2, ensure_ascii=False)
    return {'code': d.get('code'), 'message': d.get('message'), 'request_id': d.get('request_id'), 'n': len(lst),
            'n_str': sum(1 for x in lst if not isinstance(x, dict)), 'page_info': d['data'].get('page_info'),
            'budget': j.get('meta', {}).get('mcp_output_budget'), 'chars': len(t), 'bytes': len(t.encode())}
