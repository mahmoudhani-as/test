"""Validate a persisted Whathead GAQL tool-result file and copy its rows to raw/<name>.json.
Usage: python3 -I grab.py <tool-result file> <name> <key path, e.g. adGroupAd.ad.id> "<query/bounds note>"
Refuses (exit 2) when the output carries any truncation marker or a non-success flag.
Prints the row count and the first / last value of the key path (for keyset paging),
and appends one line to pages.txt."""
import json, sys, os, re

src, name, keypath, note = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACC = '8324286739'

d = json.load(open(src))
t = d[0]['text'] if isinstance(d, list) else json.dumps(d)
markers = re.findall(r'more items truncated|MCP_OUTPUT_TRUNCATED|truncated', t)
j = json.loads(t)
assert j.get('success') is True, str(j)[:800]
inner = j['data']
assert inner.get('success') is True, str(inner)[:800]
assert inner.get('endpoint') == f'customers/{ACC}/googleAds:search', inner.get('endpoint')
dd = inner['data']
assert dd.get('success') is True, str(dd)[:800]
body = dd['data']
res = body.get('results', [])
bad = [x for x in res if not isinstance(x, dict)]


def get(x, path):
    for p in path.split('.'):
        if not isinstance(x, dict):
            return None
        x = x.get(p)
    return x


keys = [get(x, keypath) for x in res if isinstance(x, dict)]
print('results', len(res), '| non-dict', len(bad), '| markers', markers, '| text len', len(t))
print('fieldMask', body.get('fieldMask'))
print('nextPageToken', body.get('nextPageToken'))
print('first key', keys[0] if keys else None, '| last key', keys[-1] if keys else None,
      '| none keys', sum(1 for k in keys if k is None))
if bad or markers or body.get('nextPageToken'):
    print('NOT SAVED: truncated / paged output')
    sys.exit(2)
dst = os.path.join(W, 'raw', name + '.json')
if os.path.exists(dst):
    print('NOT SAVED: raw file exists already', dst)
    sys.exit(3)
json.dump({'src': src, 'note': note, 'fieldMask': body.get('fieldMask'), 'results': res},
          open(dst, 'w'), ensure_ascii=False)
with open(os.path.join(W, 'pages.txt'), 'a') as f:
    f.write(f"{name}|{note}|returned {len(res)}|first {keys[0] if keys else None}|last {keys[-1] if keys else None}\n")
print('saved', dst)
