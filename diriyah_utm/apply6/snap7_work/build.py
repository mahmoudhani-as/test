# build.py <unit_idx> <pre_seq> : classify each change of the unit from the pre-read (by seq) and print the PUT payload
# (full creative objects as read, only web_view_properties.url = new) as escaped JSON. Writes nothing to the results file.
import json, sys, copy
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/snap7_work')
from common import *

idx, pre_seq = int(sys.argv[1]), int(sys.argv[2])
u = units()[idx]
o = by_seq()[pre_seq]
assert o['input'].get('action') in ('snapchat_adaccounts_ad_account_id_get_creatives_by_ids_get', 'snapchat_creatives_creative_id_get'), 'pre_seq is not a read'
crs = creatives_of(o)
assert o['result']['data']['data']['request_status'] == 'SUCCESS'
parent = crs.get(u['unit'])
print('unit', idx, u['unit'], u['ad_names'], '| parent type', parent and parent.get('type'), 'review', parent and parent.get('review_status'),
      'updated_at', parent and parent.get('updated_at'))
assert parent is not None, 'parent creative not in pre-read'
assert parent['ad_account_id'] == u['account_id'], 'account mismatch'
done = recorded()
write = []
for ci, c in enumerate(u['changes']):
    sub, pos = slot_target(u, c)
    if pos is not None:
        assert parent['type'] == 'COMPOSITE', 'parent is not COMPOSITE'
        cids = parent['composite_properties']['creative_ids']
        assert pos < len(cids) and cids[pos] == sub, 'slot position mismatch: %r' % cids
    obj = crs.get(sub)
    assert obj is not None, 'sub-creative %s not in pre-read' % sub
    assert obj['ad_account_id'] == u['account_id'], 'sub account mismatch'
    assert obj['type'] == 'WEB_VIEW', 'creative %s is %s, not WEB_VIEW' % (sub, obj['type'])
    cur = obj['web_view_properties']['url']
    cls, why = classify(cur, c)
    ex = excluded(u, c)
    rec = (u['unit'], c['slot']) in done
    print(' change', ci, sub, 'pos', pos, '| type', obj['type'], 'review', obj.get('review_status'), 'updated_at', obj.get('updated_at'),
          '| CLASS', cls, '(' + why + ')', '| EXCLUDED' if ex else '', '| ALREADY RECORDED' if rec else '')
    if cls != 'WRITE':
        print('   cur', cur)
    for k in ('name', 'headline', 'brand_name'):
        sc = special_chars(obj.get(k))
        if sc:
            print('   note', k, repr(obj.get(k)), sc)
    if cls == 'WRITE' and not ex and not rec:
        n = copy.deepcopy(obj)
        n['web_view_properties']['url'] = c['new']
        write.append(n)
if write:
    print('PAYLOAD (%d creatives):' % len(write))
    print(esc_json({'creatives': write}))
else:
    print('NO WRITE NEEDED')
