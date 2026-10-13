import json, sys
# usage: cmp_create.py before.json preview_body.json new_url
b = json.load(open(sys.argv[1]))['creative']
p = json.load(open(sys.argv[2]))
p = p['creatives'][0] if 'creatives' in p else p
new = sys.argv[3]
EXCL = {'id','updated_at','created_at','packaging_status','review_status','review_status_details','semantic_id'}
orig = {k: v for k, v in b.items() if k not in EXCL}
diffs = []
for k in sorted(set(orig) | set(p)):
    if k == 'web_view_properties':
        o = dict(orig.get(k, {})); n = dict(p.get(k, {}))
        ou = o.pop('url', None); nu = n.pop('url', None)
        if o != n: diffs.append(('web_view_properties(other)', o, n))
        if nu != new: diffs.append(('url != new', nu, new))
        if ou == nu: diffs.append(('url unchanged', ou, nu))
    elif orig.get(k, '<missing>') != p.get(k, '<missing>'):
        diffs.append((k, orig.get(k, '<missing>'), p.get(k, '<missing>')))
print('DIFFS:', json.dumps(diffs, ensure_ascii=False) if diffs else 'none (only url changed, url == new)')
