# prep.py <unit_idx> <pre_seq>[,<pre_seq>...] : classify every change of the unit from the raw pre-read(s),
# save pre objects and the PUT payload (full creative objects as read, only web_view_properties.url changed).
import sys, json, copy
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply7/snap2_work')
from common import *

idx = int(sys.argv[1])
seqs = [int(x) for x in sys.argv[2].split(',')]
u = units()[idx]
B = by_seq()
pre = {}
for s in seqs:
    o = B[s]
    assert o['result'] and o['result'].get('success') is True, 'read failed: %s' % o['raw'][:500]
    pre.update(creatives_of(o))
print('unit', idx, u['unit'], 'read ids:', sorted(pre))
parent = pre.get(u['unit'])
if parent is None:
    raise SystemExit('parent creative not in reads')
print('parent type', parent['type'], 'review', parent.get('review_status'), 'ad_account', parent['ad_account_id'])
assert parent['ad_account_id'] == u['account_id']
plan = []
payload = []
for ci, c in enumerate(u['changes']):
    sub, pos = slot_target(u, c)
    if pos is not None:
        cids = (parent.get('composite_properties') or {}).get('creative_ids') or []
        if pos >= len(cids) or cids[pos] != sub:
            print('  change', ci, 'SLOT MISMATCH: parent creative_ids =', cids)
            plan.append((ci, sub, None, 'Skipped', 'slot mismatch: parent creative_ids=%r' % cids))
            continue
    obj = pre.get(sub)
    if obj is None:
        print('  change', ci, 'sub creative not read', sub)
        plan.append((ci, sub, None, 'MISSING', 'not read'))
        continue
    assert obj['ad_account_id'] == u['account_id']
    if obj.get('type') != 'WEB_VIEW':
        print('  change', ci, sub, 'type is', obj.get('type'), '(not WEB_VIEW)')
    cur = (obj.get('web_view_properties') or {}).get('url')
    res, why = classify(cur, c)
    ex = excluded(u, c)
    if ex:
        res, why = 'EXCLUDED', 'platform-refused list: %r' % ex
    print('  change', ci, sub[:8], 'pos', pos, '->', res, '|', why)
    print('     cur:', cur)
    sp = {k: special_chars(v) for k, v in flat(obj).items() if special_chars(v)}
    if sp:
        print('     special chars:', sp)
    ns = nonstr_scalars(obj)
    if ns:
        print('     numeric fields:', ns)
    save('pre_u%d_%s.json' % (idx, sub[:8]), obj)
    plan.append((ci, sub, cur, res, why))
    if res == 'WRITE':
        n = copy.deepcopy(obj)
        n['web_view_properties']['url'] = c['new']
        payload.append(n)
if parent.get('type') == 'COMPOSITE':
    save('pre_u%d_parent_%s.json' % (idx, u['unit'][:8]), parent)
save('plan_u%d.json' % idx, plan)
if payload:
    body = {'creatives': payload}
    save('payload_u%d.json' % idx, body)
    print('PAYLOAD (%d creatives):' % len(payload))
    print(esc_json(body))
else:
    print('NO WRITE NEEDED')
