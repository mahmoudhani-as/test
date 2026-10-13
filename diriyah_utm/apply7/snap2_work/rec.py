# rec.py <unit_idx> <pre_seqs> <dry_seq|0> <live_seq|0> <post_seqs|0> : record one result line per change of the unit,
# everything taken from the raw tool results in this agent's transcript.
import json, sys
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply7/snap2_work')
from common import *

ALLOWED = {'.review_status', '.review_status_details', '.semantic_id', '.updated_at'}

idx = int(sys.argv[1])
pre_seqs = [int(x) for x in sys.argv[2].split(',')]
dry_seq, live_seq = int(sys.argv[3]), int(sys.argv[4])
post_seqs = [int(x) for x in sys.argv[5].split(',') if int(x)]
u = units()[idx]
B = by_seq()

def snap_req(o):
    try:
        return o['result']['data']['data'].get('request_id') or req_id(o)
    except Exception:
        return req_id(o)

pre, pre_req = {}, {}
for s in pre_seqs:
    for k, v in creatives_of(B[s]).items():
        pre[k] = v; pre_req[k] = snap_req(B[s])
post, post_req = {}, {}
for s in post_seqs:
    for k, v in creatives_of(B[s]).items():
        post[k] = v; post_req[k] = snap_req(B[s])
parent_pre = pre.get(u['unit'])
parent_post = post.get(u['unit'])

sent, sub_status, live_req, dry_req = {}, {}, None, None
if live_seq:
    L = B[live_seq]
    assert L['input'].get('action') == UPDATE_ACTION and L['input'].get('dry_run') is False
    sent = {x['id']: x for x in payload_of(L)['creatives']}
    lv = L['result']['data']['data'] if L['result'] and L['result'].get('success') else {}
    live_req = lv.get('request_id') or req_id(L)
    for x in lv.get('creatives', []):
        cid = (x.get('creative') or {}).get('id')
        sub_status[cid] = (x.get('sub_request_status'), x.get('sub_request_error_reason'))
    live_status = lv.get('request_status')
    saved = json.load(open(WD + '/payload_u%d.json' % idx, encoding='utf-8'))
    assert payload_of(L) == saved, 'live payload != dry-run-checked payload'
if dry_seq:
    D = B[dry_seq]
    assert D['input'].get('action') == UPDATE_ACTION and D['input'].get('dry_run') is True
    assert payload_of(D) == payload_of(B[live_seq]), 'dry-run payload != live payload'
    dry_req = req_id(D)

parent_note = ''
if parent_pre is not None and parent_pre.get('type') == 'COMPOSITE' and parent_post is not None:
    pd = diff(parent_pre, parent_post)
    unexp = [x for x in pd if x[0] not in ALLOWED]
    parent_note = '; parent COMPOSITE %s (not written itself) after the sub-creative PUT: %s%s; parent review_status %s' % (
        u['unit'], '; '.join("%s %r->%r" % x for x in pd) or 'no field changes',
        '' if not unexp else ' UNEXPECTED parent changes: %r' % unexp, parent_post.get('review_status'))

rows = []
for ci, c in enumerate(u['changes']):
    sub, pos = slot_target(u, c)
    obj = pre.get(sub)
    kind = 'COMPOSITE sub-creative %s (creative_ids[%d] of %s)' % (sub, pos, u['unit']) if pos is not None else '%s creative' % (obj or {}).get('type', '?')
    if obj is None:
        append(u, c, '', '', 'Failed', 'sub-creative %s could not be read; not written' % sub)
        continue
    cur = obj['web_view_properties']['url']
    res, why = classify(cur, c)
    if excluded(u, c):
        res, why = 'EXCLUDED', 'platform-refused list'
    if res != 'WRITE' or sub not in sent:
        if res == 'WRITE':
            raise SystemExit('change %d needs a write but was not in the live payload' % ci)
        result = 'AlreadyFixed' if res == 'AlreadyFixed' else ('Skipped')
        detail = ('%s; pre-read (Snapchat req %s) %s; no write made; live review_status %s, updated_at %s' % (kind, pre_req[sub], why if res != 'Skipped' else 'changed since plan: %s' % cur, obj.get('review_status'), obj.get('updated_at')))
        if res == 'EXCLUDED':
            detail = '%s; listed in excl_platform_refused_v2.json, not written' % kind
        append(u, c, cur, cur, result, detail)
        rows.append((ci, sub[:8], result))
        continue
    p = post.get(sub)
    after = (p or {}).get('web_view_properties', {}).get('url') if p else None
    st = sub_status.get(sub)
    ok = p is not None and after == c['new'] and st and st[0] == 'SUCCESS'
    d = [x for x in diff(obj, p)] if p else []
    other = [x for x in d if x[0] != '.web_view_properties.url']
    unexp = [x for x in other if x[0] not in ALLOWED]
    sc = '; '.join("%s %r->%r" % x for x in other)
    detail = ("%s; pre-read (Snapchat req %s) url == plan %s; PUT /v1/adaccounts/{id}/creatives "
              "(snapchat_adaccounts_ad_account_id_creatives_update) with the full creative object as read, only web_view_properties.url changed%s; "
              "dry_run preview checked first (gateway req %s: body byte-identical to the read except url, verified from raw tool results); "
              "live request_status %s, sub_request %s%s, Snapchat req %s; read-back (Snapchat req %s) url %s; "
              "review_status after write: %s (re-review triggered by the PUT); server changed: %s; %s%s") % (
        kind, pre_req[sub], why,
        (' (%d creatives in one PUT)' % len(sent)) if len(sent) > 1 else '',
        dry_req, live_status, st[0] if st else None, (' (%s)' % st[1]) if st and st[1] else '', live_req,
        post_req.get(sub), 'matches new byte for byte' if (after == c['new']) else 'DOES NOT match new',
        (p or {}).get('review_status'), sc or 'nothing else',
        'all other fields unchanged on re-read' if not unexp else 'UNEXPECTED other changes: %r' % unexp,
        parent_note)
    append(u, c, cur, after if after is not None else '', 'Fixed' if ok else 'Failed', detail)
    rows.append((ci, sub[:8], 'Fixed' if ok else 'Failed', (p or {}).get('review_status'), unexp))
for r in rows:
    print(r)
