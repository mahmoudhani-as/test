"""Copy a persisted MCP tool-result file into raw/<name>.json after validating it.
Usage: python3 -I grab.py <tool-result file> <name> [--partial]
--partial: accept an output whose ONLY truncation is a trailing "[N more items truncated]"
entry at the end of the results array (the rows before it are complete); that entry is dropped.
Prints result count, truncation markers, first/last resource names."""
import json, sys, os, re
src, name = sys.argv[1], sys.argv[2]
partial_ok = '--partial' in sys.argv
W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = json.load(open(src))
t = d[0]['text'] if isinstance(d, list) else json.dumps(d)
markers = re.findall(r'\[\d+ more items truncated\]|MCP_OUTPUT_TRUNCATED', t)
j = json.loads(t)
assert j.get('success') is True, str(j)[:500]
inner = j['data']
assert inner.get('endpoint') == 'customers/8324286739/googleAds:search', inner.get('endpoint')
dd = inner['data']
assert dd.get('success') is True, str(dd)[:500]
res = dd['data'].get('results', [])
tail = None
if res and isinstance(res[-1], str) and re.fullmatch(r'\[\d+ more items truncated\]', res[-1]):
    tail = res[-1]
    res = res[:-1]
bad = [x for x in res if not isinstance(x, dict)]
inner_markers = re.findall(r'\[\d+ more items truncated\]|MCP_OUTPUT_TRUNCATED', json.dumps(res))
print('results', len(res), 'tail marker', tail, 'non-dict entries', bad, 'markers in rows', inner_markers,
      'all markers', markers, 'len', len(t))
print('fieldMask', dd['data'].get('fieldMask'))
print('nextPageToken', dd['data'].get('nextPageToken'))
def last_rn(x):
    m = re.findall(r'"resourceName": "([^"]+)"', json.dumps(x))
    return m[-1] if m else None
if res:
    print('first', last_rn(res[0]))
    print('last ', last_rn(res[-1]))
ok = not bad and not inner_markers and (tail is None or partial_ok) and \
    len(markers) == (1 if tail else 0) and 'MCP_OUTPUT_TRUNCATED' not in t
if not ok:
    print('NOT SAVED: truncated output (use --partial only when the sole marker is the trailing results entry)')
    sys.exit(2)
dst = os.path.join(W, 'raw', name + '.json')
json.dump({'src': src, 'results': res, 'partial_tail': tail, 'fieldMask': dd['data'].get('fieldMask'),
           'nextPageToken': dd['data'].get('nextPageToken')}, open(dst, 'w'), ensure_ascii=False)
print('saved', dst, '(PARTIAL page: continue after the last complete row)' if tail else '')
