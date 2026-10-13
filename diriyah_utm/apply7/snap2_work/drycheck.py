# drycheck.py <unit_idx> <pre_seq>[,..] <call_seq> [live] : byte-exact check, from the transcript, that the PUT call
# sent exactly the pre-read objects with only web_view_properties.url changed (to new) for the WRITE changes, and
# (dry run) that the preview body == payload, method PUT, path of this account.
import json, sys
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply7/snap2_work')
from common import *

idx = int(sys.argv[1]); pre_seqs = [int(x) for x in sys.argv[2].split(',')]; cseq = int(sys.argv[3])
live = len(sys.argv) > 4 and sys.argv[4] == 'live'
u = units()[idx]
B = by_seq()
pre = {}
for s in pre_seqs:
    pre.update(creatives_of(B[s]))
d = B[cseq]
inp = d['input']
problems = []
if inp.get('action') != UPDATE_ACTION:
    problems.append('action %r' % inp.get('action'))
if inp.get('dry_run') is not (False if live else True):
    problems.append('dry_run is %r' % inp.get('dry_run'))
if account_of(d) != u['account_id']:
    problems.append('account %r' % account_of(d))
extra = set(inp) - {'action', 'ad_account_id', 'payload', 'dry_run'}
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
    dd = diff(o, s)
    if [x[0] for x in dd] != ['.web_view_properties.url']:
        problems.append('%s diff vs pre-read: %s' % (s['id'][:8], dd))
    if s['web_view_properties']['url'] != exp.get(s['id']):
        problems.append('%s url != new' % s['id'][:8])
    if list(s.keys()) != list(o.keys()) or list(s['web_view_properties'].keys()) != list(o['web_view_properties'].keys()):
        print('note: key order differs from the read (harmless for JSON)')
r = d['result'] or {}
if not live:
    try:
        req = r['data']['data']['request']
        body = req.get('body')
        if isinstance(body, str):
            body = json.loads(body)
        print('preview method', req.get('method'), 'path', req.get('path'))
        if req.get('method') != 'PUT':
            problems.append('preview method %r' % req.get('method'))
        if req.get('path') != '/v1/adaccounts/%s/creatives' % u['account_id']:
            problems.append('preview path %r' % req.get('path'))
        if body != p:
            problems.append('preview body != payload sent')
        if r['data'].get('dryRun') is not True:
            problems.append('preview dryRun flag %r' % r['data'].get('dryRun'))
        if r['data']['data'].get('warnings'):
            print('preview warnings:', r['data']['data'].get('warnings'))
    except Exception as e:
        problems.append('dry result unreadable %r' % e)
        print(d['raw'][:2000])
    # also compare against the saved payload file
    try:
        sp = json.load(open(WD + '/payload_u%d.json' % idx, encoding='utf-8'))
        if sp != p:
            problems.append('sent payload != saved payload_u%d.json' % idx)
    except FileNotFoundError:
        problems.append('no saved payload file')
else:
    try:
        lv = r['data']['data']
        print('live request_status', lv.get('request_status'), 'request_id', lv.get('request_id'), 'dryRun', r['data'].get('dryRun'))
        for x in lv.get('creatives', []):
            cr = x.get('creative') or {}
            print('  sub', cr.get('id'), x.get('sub_request_status'), 'review', cr.get('review_status'), 'url==new', (cr.get('web_view_properties') or {}).get('url') == exp.get(cr.get('id')), x.get('sub_request_error_reason', ''))
    except Exception as e:
        print('live result unreadable', e, d['raw'][:2000])
    # live payload must equal the dry-run-checked payload
    try:
        sp = json.load(open(WD + '/payload_u%d.json' % idx, encoding='utf-8'))
        if sp != p:
            problems.append('live payload != saved/dry-run payload_u%d.json' % idx)
    except FileNotFoundError:
        problems.append('no saved payload file')
print('unit', idx, u['unit'][:8], 'seq', cseq, 'live' if live else 'dry', 'sent', len(p['creatives']), 'creatives |', 'OK' if not problems else 'NOT OK: ' + ' ; '.join(problems))
