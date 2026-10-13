# usage: python3 -I ingest.py <saved_tool_result_path> <work_dir> <dest_name> <collection: creatives|ads|adsquads|campaigns>
import json, sys, base64, re, shutil, os
src, wd, name, coll = sys.argv[1:5]
dst = os.path.join(wd, name)
shutil.copyfile(src, dst)
t = open(dst).read()
d = json.loads(t)
assert d.get('success') is True, 'gateway not success'
inner = d['data']['data']
assert inner.get('request_status') == 'SUCCESS', inner.get('request_status')
items = inner[coll]
bad = [x for x in items if not isinstance(x, dict)]
budget = (d.get('meta') or {}).get('mcp_output_budget')
print('items', len(items), 'non-dict(truncation markers)', bad[:2], 'budget', budget)
key = coll[:-1]
subs = [x.get('sub_request_status') for x in items if isinstance(x, dict)]
recs = [x[key] for x in items if isinstance(x, dict)]
print('first', recs[0]['id'] if recs else None, 'last', recs[-1]['id'] if recs else None)
nl = (inner.get('paging') or {}).get('next_link', '')
m = re.search(r'cursor=([^&]+)', nl)
if m:
    c = m.group(1)
    print('next_cursor', c, base64.b64decode(c + '=' * (-len(c) % 4)).decode())
else:
    print('no next_link')
