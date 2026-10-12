# drycheck.py <unit_idx> <pre_seq> <dry_seq> : byte-exact check, from the transcript, that the dry-run call sent
# exactly the pre-read objects with only web_view_properties.url changed (to new), and that the preview body == payload.
import json, sys
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/snap7_work')
from common import *

idx, pre_seq, dry_seq = (int(x) for x in sys.argv[1:4])
u = units()[idx]
B = by_seq()
pre = creatives_of(B[pre_seq])
d = B[dry_seq]
inp = d['input']
problems = []
if inp.get('action') != UPDATE_ACTION:
    problems.append('action %r' % inp.get('action'))
if inp.get('dry_run') is not True:
    problems.append('dry_run is %r' % inp.get('dry_run'))
if account_of(d) != u['account_id']:
    problems.append('account %r' % account_of(d))
extra = set(inp) - {'action', 'ad_account_id', 'account_id', 'payload', 'dry_run'}
if extra:
    problems.append('extra input keys %s' % sorted(extra))
p = payload_of(d)
if set(p) != {'creatives'}:
    problems.append('payload keys %s' % sorted(p))
exp = {}
for ci, c in enumerate(u['changes']):
    sub, pos = slot_target(u, c)
    obj = pre.get(sub)
    if obj is not None and classify(obj['web_view_properties']['url'], c)[0] == 'WRITE' and not excluded(u, c):
        exp[sub] = c['new']
sent_ids = [x.get('id') for x in p['creatives']]
if sorted(sent_ids) != sorted(exp) or len(set(sent_ids)) != len(sent_ids):
    problems.append('sent ids %s != expected %s' % (sent_ids, sorted(exp)))
for s in p['creatives']:
    o = pre.get(s.get('id'))
    if o is None:
        problems.append('sent id %s not in pre-read' % s.get('id'))
        continue
    fp, fs = flat(o), flat(s)
    diff = [k for k in sorted(set(fp) | set(fs)) if fp.get(k, '<absent>') != fs.get(k, '<absent>')]
    if diff != ['web_view_properties.url']:
        problems.append('%s diff vs pre-read: %s' % (s['id'][:8], [(k, fp.get(k, '<absent>'), fs.get(k, '<absent>')) for k in diff]))
    if fs.get('web_view_properties.url') != exp.get(s['id']):
        problems.append('%s url != new' % s['id'][:8])
r = d['result'] or {}
try:
    dd = r['data']
    print('dry result keys:', sorted(dd) if isinstance(dd, dict) else type(dd))
    req = dd.get('request') or (dd.get('data') or {}).get('request')
    if req is None:
        print('preview (raw, first 1500 chars):', d['raw'][:1500])
        problems.append('no request preview found')
    else:
        body = req.get('body')
        if isinstance(body, str):
            body = json.loads(body)
        print('preview method', req.get('method'), 'url/path', req.get('url') or req.get('path'))
        if req.get('method') != 'PUT':
            problems.append('preview method %r' % req.get('method'))
        if body != p:
            problems.append('preview body != payload sent')
except Exception as e:
    problems.append('dry result unreadable %r' % e)
    print(d['raw'][:2000])
print('unit', idx, u['unit'][:8], 'sent', len(p['creatives']), 'creatives |', 'OK' if not problems else 'NOT OK: ' + ' ; '.join(problems))
