import sys, json, copy
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply8/work_meta_3')
from lib8 import *


def build(ad_id, creative):
    """creative = exact parsed live creative object. Returns payload (copy of every sendable field, URL slot(s) set to new)."""
    unknown = [k for k in creative if k not in SEND_KEYS and k not in DERIVED]
    assert not unknown, ('unhandled fields', unknown)
    assert not has_trunc(creative), 'truncated read'
    u = unit(ad_id)
    for c, cur, v in classify(u, creative):
        print(v, c['slot'], '| cur==now:', cur == c['now'])
        assert v == 'Write', v
    p = {k: copy.deepcopy(creative[k]) for k in SEND_KEYS if k in creative}
    # deprecated key Meta rejects on create (earlier runs); everything else copied as read
    dof = p.get('degrees_of_freedom_spec', {}).get('creative_features_spec')
    if dof and 'standard_enhancements' in dof:
        print('dropping deprecated standard_enhancements:', dof['standard_enhancements'])
        dof.pop('standard_enhancements')
    for c in u['changes']:
        set_slot(p, c['slot'], c['new'])
    o = {k: creative[k] for k in SEND_KEYS if k in creative}
    print('diff vs live creative (sendable fields):')
    for l in diff(o, p):
        print('  ', l)
    print('invisible chars:', invisible(p))
    json.dump(p, open(W + 'payload_%s.json' % ad_id, 'w'), ensure_ascii=False, indent=1)
    return p


if __name__ == '__main__':
    ad_id, src = sys.argv[1], sys.argv[2]
    obj = json.load(open(src))
    cr = obj[ad_id]['creative'] if ad_id in obj else obj
    p = build(ad_id, cr)
    print('PAYLOAD_JSON', json.dumps(p, ensure_ascii=False))
