import json, sys
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply9/work_google_2')
from lib import *

# usage: python3 -I check_preview.py <dry_run_req_id> <unit_id> [<unit_id> ...]
# Checks that the dry-run preview body has exactly one op per listed unit, each touching only
# final_urls (update_mask "final_urls"), with final_urls == [new] byte for byte; and that the
# call input params are identical to the previewed body.
rid = sys.argv[1]
want = sys.argv[2:]
inp, j = result_by_request_id(rid)
d = j['data']
assert d.get('dry_run') is True, 'not a dry run'
body = d['body']
ops = body['operations']
U = {u['unit']: u for u in units()}
ex = excluded()
ok = True
seen = []
for op in ops:
    upd = op.get('update') or {}
    keys = set(upd.keys())
    mask = op.get('update_mask')
    rn = upd.get('resource_name', '')
    aid = rn.rsplit('/', 1)[-1]
    seen.append(aid)
    u = U.get(aid)
    probs = []
    if set(op.keys()) != {'update', 'update_mask'}: probs.append('op keys %s' % sorted(op.keys()))
    if keys != {'resource_name', 'final_urls'}: probs.append('update keys %s' % sorted(keys))
    if mask != 'final_urls': probs.append('mask %r' % mask)
    if u is None:
        probs.append('unit not in input')
    else:
        if rn != 'customers/%s/ads/%s' % (u['account_id'], aid): probs.append('resource_name %s' % rn)
        new = u['changes'][0]['new']
        if upd.get('final_urls') != [new]: probs.append('final_urls differ: %r' % (upd.get('final_urls'),))
        if (aid, u['changes'][0]['slot']) in ex: probs.append('EXCLUDED')
    if probs:
        ok = False
        print('PROBLEM', aid, probs)
if sorted(seen) != sorted(want) or len(seen) != len(set(seen)):
    ok = False
    print('PROBLEM op set', sorted(set(seen) ^ set(want)), 'dups' if len(seen) != len(set(seen)) else '')
extra = set(body.keys()) - {'operations', 'partial_failure', 'validate_only'}
if extra:
    ok = False
    print('PROBLEM body keys', extra)
print('body flags:', {k: body.get(k) for k in ('partial_failure', 'validate_only')})
print('input params identical to body:', inp.get('params') == body or json.dumps(inp.get('params'), sort_keys=True) == json.dumps(body, sort_keys=True))
print('ops:', len(ops), 'OK' if ok else 'NOT OK')
