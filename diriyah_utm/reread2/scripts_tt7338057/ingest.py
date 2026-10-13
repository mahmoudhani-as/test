# usage: python3 -I ingest.py <saved_tool_result_path> <dest_path>
# Copies a persisted Whathead TikTok tool result (JSON array of text parts, or plain text) into dest_path as the gateway JSON, and reports list size / truncation.
import json, sys
src, dst = sys.argv[1], sys.argv[2]
raw = open(src, encoding='utf-8').read()
try:
    outer = json.loads(raw)
except Exception:
    outer = None
if isinstance(outer, list):
    text = ''.join(p.get('text', '') for p in outer if isinstance(p, dict) and p.get('type') == 'text')
else:
    text = raw
d = json.loads(text)
with open(dst, 'w', encoding='utf-8') as f:
    f.write(text)
assert d.get('success') is True, 'gateway not success'
inner = d['data']['data']
assert inner.get('code') == 0, (inner.get('code'), inner.get('message'))
dd = inner.get('data') or {}
lst = dd.get('list') or []
markers = [x for x in lst if not isinstance(x, dict)]
budget = (d.get('meta') or {}).get('mcp_output_budget')
items = [x for x in lst if isinstance(x, dict)]
ids = [x.get('ad_id') or x.get('smart_plus_ad_id') for x in items]
print('request_id', inner.get('request_id'), 'items', len(items), 'markers', markers[:2], 'page_info', dd.get('page_info'), 'budget', budget)
print('first', ids[:1], 'last', ids[-1:])
