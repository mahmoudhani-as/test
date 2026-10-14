"""Like grab.py, but also accepts an output that the MCP output budget cut at the END of the results array
(trailing "[N more items truncated]" marker): only the complete leading rows are kept (they are a prefix of the
ORDER BY result, so keyset paging continues from the last kept key). Refuses anything else (marker in the middle,
non-success flag, nextPageToken).
Usage: python3 -I grab2.py <tool-result file> <name> <key path> "<query/bounds note>" """
import json, sys, os, re

src, name, keypath, note = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACC = '8324286739'

d = json.load(open(src))
t = d[0]['text'] if isinstance(d, list) else json.dumps(d)
j = json.loads(t)
assert j.get('success') is True, str(j)[:800]
inner = j['data']
assert inner.get('success') is True, str(inner)[:800]
assert inner.get('endpoint') == f'customers/{ACC}/googleAds:search', inner.get('endpoint')
dd = inner['data']
assert dd.get('success') is True, str(dd)[:800]
body = dd['data']
res = body.get('results', [])
nd = [i for i, x in enumerate(res) if not isinstance(x, dict)]
cut = False
if nd:
    assert nd == [len(res) - 1], f'non-dict rows not only at the end: {nd}'
    assert re.fullmatch(r'\[\d+ more items truncated\]', res[-1]), res[-1]
    budget = (j.get('meta') or {}).get('mcp_output_budget') or {}
    assert budget.get('truncated') is True, budget
    cut = True
    res = res[:-1]
assert all(isinstance(x, dict) for x in res)
# any other truncation marker in the text (e.g. inside a nested list) -> refuse
other = len(re.findall(r'more items truncated', t)) - (1 if cut else 0)
assert other == 0, f'{other} other truncation markers'


def get(x, path):
    for p in path.split('.'):
        if not isinstance(x, dict):
            return None
        x = x.get(p)
    return x


keys = [get(x, keypath) for x in res]
print('results kept', len(res), '| cut by output budget', cut, '| text len', len(t))
print('nextPageToken', body.get('nextPageToken'))
print('first key', keys[0] if keys else None, '| last key', keys[-1] if keys else None,
      '| none keys', sum(1 for k in keys if k is None))
if body.get('nextPageToken'):
    print('NOT SAVED: paged output')
    sys.exit(2)
dst = os.path.join(W, 'raw', name + '.json')
if os.path.exists(dst):
    print('NOT SAVED: raw file exists already', dst)
    sys.exit(3)
note2 = note + (f' (output budget kept the first {len(res)} rows; next page starts at the last kept key)' if cut else '')
json.dump({'src': src, 'note': note2, 'cut': cut, 'fieldMask': body.get('fieldMask'), 'results': res},
          open(dst, 'w'), ensure_ascii=False)
with open(os.path.join(W, 'pages.txt'), 'a') as f:
    f.write(f"{name}|{note2}|returned {len(res)}|first {keys[0] if keys else None}|last {keys[-1] if keys else None}\n")
print('saved', dst)
