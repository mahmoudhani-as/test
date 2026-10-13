import json, sys, base64
path = sys.argv[1]
s = open(path).read()
try:
    d = json.loads(s)
except Exception:
    raw = json.loads(s)
    d = json.loads(raw[0]['text'])
if isinstance(d, list):
    d = json.loads(d[0]['text'])
inner = d['data']['data']
assert inner['request_status'] == 'SUCCESS', inner['request_status']
items = inner['creatives']
bad = [x for x in items if not isinstance(x, dict)]
crs = [x['creative'] for x in items if isinstance(x, dict)]
print('items', len(crs), 'non-dict', bad)
print('paging', inner.get('paging'))
print('budget', json.dumps(d.get('meta', {}).get('mcp_output_budget')))
print('first', crs[0]['id'], 'last', crs[-1]['id'])
last = crs[-1]['id']
print('next cursor', base64.urlsafe_b64encode(('CreativesV2/' + last).encode()).decode().rstrip('='))
