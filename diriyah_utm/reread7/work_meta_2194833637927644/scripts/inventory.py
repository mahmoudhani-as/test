"""Build data/inventory.json {ad_id: {id, effective_status}} from the given call indexes in data/calls.json (14-Oct status-partitioned lists).
Usage: inventory.py IN_FILE OUT_JSON idx1 idx2 ..."""
import json, sys
from collections import Counter
IN_FILE, OUT = sys.argv[1], sys.argv[2]
idxs = [int(x) for x in sys.argv[3:]]
calls = json.load(open('data/calls.json', encoding='utf-8'))
inv = {}
for i in idxs:
    c = calls[i]
    assert not c['truncated'], ('truncated', i)
    items = c['payload']['data']['data']['data']
    assert all(isinstance(x, dict) for x in items), ('non-dict item (truncation marker?)', i)
    for a in items:
        assert a['id'] not in inv, ('dup', a['id'])
        inv[a['id']] = a
json.dump(inv, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
rows = json.load(open(IN_FILE, encoding='utf-8'))
in_ids = {r['ad_id'] for r in rows}
print('inventory', len(inv), Counter(a['effective_status'] for a in inv.values()))
print('input ads', len(in_ids), 'input ads not in inventory', sorted(in_ids - set(inv)))
new = sorted(set(inv) - in_ids)
print('non-input ads', len(new), Counter(inv[a]['effective_status'] for a in new))
print('non-input DELETED', [a for a in new if inv[a]['effective_status'] == 'DELETED'])
print('input ads now DELETED', sorted(a for a in in_ids if a in inv and inv[a]['effective_status'] == 'DELETED'))
st11 = {r['ad_id']: r['status_11oct'] for r in rows}
ch = Counter((st11[a], inv[a]['effective_status']) for a in in_ids if a in inv and st11[a] != inv[a]['effective_status'])
print('input ads whose status changed since 11-Oct', sum(ch.values()), dict(ch))
