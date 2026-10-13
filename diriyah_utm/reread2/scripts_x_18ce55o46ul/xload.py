import json, sys
def load(path):
    raw = open(path, encoding='utf-8').read()
    d = json.loads(raw)
    if isinstance(d, list) and d and isinstance(d[0], dict) and 'type' in d[0] and 'text' in d[0]:
        txt = ''.join(x['text'] for x in d if x.get('type') == 'text')
        d = json.loads(txt)
    return d
def inner(path):
    d = load(path)
    x = d
    # navigate to the object holding 'data' list
    while isinstance(x, dict) and 'data' in x and not isinstance(x['data'], list):
        x = x['data']
    return d, x
if __name__ == '__main__':
    for p in sys.argv[1:]:
        d, x = inner(p)
        items = x.get('data')
        print(p, len(items) if isinstance(items, list) else type(items), 'next_cursor=', x.get('next_cursor'), 'total=', x.get('total_count'))
        bad = [i for i in (items or []) if not isinstance(i, dict)]
        print(' non-dict items:', bad[:3])
        print(' meta:', json.dumps(d.get('meta'))[:300])
