"""Read-only: assemble the per-change results for apply9 in_google_2 from exact API responses
in this agent's transcript. Prints JSON (one result object per line). Writes no files."""
import json, sys
SL = (int(sys.argv[1]), int(sys.argv[2])) if len(sys.argv) > 2 else (0, 999)
sys.argv = [sys.argv[0], 'noop']
import importlib.util
spec = importlib.util.spec_from_file_location('chk', '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply9/work_google_2/v2/chk.py')

# chk.main() runs on import with mode 'noop' -> SystemExit('unknown mode'); catch it, keep the module
chk = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(chk)
except SystemExit:
    pass

PRE0 = '2f2bc1ff-2478-4439-b77a-b752b490c3ba'
PRE0b = 'd7ebb48e-cc4f-45c7-a869-429640db5c12'
GROUPS = [
    # (label, pre, dry, validate, live, readback, units)
    ('first unit, single operation', PRE0, '43c41ad1-ebd9-4026-b3f4-cc398c1eaaa4', None, '9f9b1934-7a16-4308-b038-a6c4172f539d',
     '869f49a9-ce77-4030-af98-59b27f4047ce', ['800840046891']),
    ('RSA batch A, 23 ops, partial_failure', '605c4513-48f0-400f-8b3e-0d1dd9f2b727', '05b981fb-6155-46d1-a72e-f3a15e135415', None,
     'a52033b6-4107-4b81-8342-6f0c7ae88567', '52110d3c-9208-421e-a55f-cd9019439c1b',
     '800840046894 797795488734 800840046954 797795488737 800840046957 797893430573 800840046843 797795488557 800840046897 797795488680 800840046900 797795488683 800840046903 797795488686 800840046906 797795488689 800840046909 797795488692 800840046912 797795488695 800840046915 797795488698 800840046918'.split()),
    ('RSA batch B, 23 ops, partial_failure', 'a57c8d53-b988-4baa-a514-a5f0412e4598', '249f119f-13f9-4154-ab5e-070f9e8b58c2', None,
     '226c4b52-f02c-4365-8d7a-16237b99b367', 'f1ce9fe0-4dfc-4d9f-b649-1b6f6aa80ece',
     '797795488701 800840046921 797795488704 800840046924 797795488707 800840046927 797795488710 800840046930 797795488713 800840046933 797795488716 800840046936 797795488719 800840046939 797795488722 800840046942 797795488725 800840046945 797795488752 800840047092 797905822541 800840047095 798315346001'.split()),
    ('Demand Gen batch, 10 ops, partial_failure', '67589212-0443-4cd8-89df-8f9cb2e6385a', '13018ca2-0d8c-4826-8449-5eaa268d1478',
     '83a286c0-ff86-4ba8-88a2-d19a07abe473', '49d5a317-606f-41ef-8d0b-ca56028800a0', '03f704ad-9365-41c7-b1bd-bd1a4cfae13d',
     '798305465759 798305465882 798305465885 798305465888 800012536990 800012536993 800023610872 800023610875 800012536996 800012536999'.split()),
]
EARLIER = {
    '800840046888': ('e5f2bcf0-5a12-44bb-9044-f965b180a4af', '11:38 UTC', 'its read-back 2f8bc080-0028-4838-815d-72a382920ca0 was byte-equal'),
    '797795488551': ('403bc4d3-46e4-4911-8e89-b9233c97f10c', '11:42 UTC', 'its own verification step was blocked by the session safety check, so this re-read is the first verification'),
    '797795488554': ('5b121ce1-e433-4004-9174-312115f902f9', '11:44 UTC', 'its read-back a24e46d2-8ee3-4952-b0ae-f8f9d80d635c was byte-equal'),
}


def live_ok(req, aid):
    inp, j = chk.by_req(req)
    res = j['data']['data']['data']
    names = [r.get('resourceName') for r in res.get('results', [])]
    pf = res.get('partialFailureError')
    return ('customers/8324286739/ads/%s' % aid) in names and not pf


def ts_of(req):
    # UTC time of the tool result that carries this request id
    for line in open(chk.T):
        if req in line:
            try:
                e = json.loads(line)
            except Exception:
                continue
            if e.get('type') == 'user':
                return (e.get('timestamp') or '')[11:16] + ' UTC'
    return '?'


pre_all = chk.rows_for([PRE0, PRE0b])
out = []
done = set()
for label, pre, dry, val, live, rb, units in GROUPS:
    prer = chk.rows_for([pre])
    rbr = chk.rows_for([rb])
    t = ts_of(live)
    for aid in units:
        u = chk.U[aid]; ch = u['changes'][0]
        b = prer[aid]; a = rbr[aid]
        assert chk.classify(b['landing'], ch) == 'Write' and b['landing'] == ch['now']
        ok = a['final_urls'] == [ch['new']] and not a['suffix'] and a['landing'] == ch['new']
        assert live_ok(live, aid)
        side = []
        if b['status'] != a['status']: side.append('AD STATUS CHANGED %s->%s' % (b['status'], a['status']))
        if b['campaign_status'] != a['campaign_status']: side.append('CAMPAIGN STATUS CHANGED')
        det = ('%s: pre-read %s cur==now; dry run %s preview exact (final_urls only, mask final_urls); %s'
               'live MutateAds %s at %s (%s), op returned its resourceName, no error; read-back %s byte-equal new, '
               'no final_url_suffix/tracking template on ad, ad group, campaign or account; ad %s and campaign %s unchanged; '
               'approval %s -> %s (Google re-review after URL edit). %s'
               % (b['type'], pre, dry, ('API validate_only %s passed; ' % val) if val else '', live, t,
                  label, rb, a['status'], a['campaign_status'], b['approval'], a['approval'], '; '.join(side))).strip()
        out.append({'platform': 'google', 'account_id': u['account_id'], 'unit_type': u['unit_type'], 'unit': aid,
                    'ad_ids': u['ad_ids'], 'ad_names': [n for n in (u.get('ad_names') or []) if n is not None],
                    'slot': ch['slot'], 'before': b['landing'], 'after_expected': ch['new'],
                    'after_live': a['landing'] if a['final_urls'] else None, 'result': 'Fixed' if ok else 'Failed',
                    'new_entity_ids': '', 'detail': det})
        done.add(aid)
for aid, (req, t, note) in EARLIER.items():
    u = chk.U[aid]; ch = u['changes'][0]
    r = pre_all[aid]
    assert r['landing'] == ch['new'] and r['final_urls'] == [ch['new']] and not r['suffix']
    det = ('Re-read %s: live final_urls already == new byte for byte, no suffix/tracking template at any level; no write in this run. '
           'Written by the stopped earlier apply9 attempt for this batch (run wf_6331729e-fc0): live MutateAds %s at %s; %s. '
           'Ad %s, campaign %s, approval %s.' % (PRE0, req, t, note, r['status'], r['campaign_status'], r['approval']))
    out.append({'platform': 'google', 'account_id': u['account_id'], 'unit_type': u['unit_type'], 'unit': aid,
                'ad_ids': u['ad_ids'], 'ad_names': [n for n in (u.get('ad_names') or []) if n is not None],
                'slot': ch['slot'], 'before': r['landing'], 'after_expected': ch['new'],
                'after_live': r['landing'], 'result': 'AlreadyFixed', 'new_entity_ids': '', 'detail': det})
    done.add(aid)
order = {u['unit']: i for i, u in enumerate(chk.UNITS)}
out.sort(key=lambda o: order[o['unit']])
missing = [u['unit'] for u in chk.UNITS if u['unit'] not in done]
from collections import Counter
print('COUNTS', dict(Counter(o['result'] for o in out)), 'entries', len(out), 'missing', missing, file=sys.stderr)
print('ad_names in input:', Counter(json.dumps(u.get('ad_names')) for u in chk.UNITS), file=sys.stderr)
for o in out[SL[0]:SL[1]]:
    print(json.dumps(o, ensure_ascii=False))
