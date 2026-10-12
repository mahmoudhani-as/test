# rec.py <unit_idx> <pre_seq> [dry_seq live_seq post_seq] [--commit]
# Verifies byte-exact from the transcript and (with --commit) appends one result line per change of the unit:
#  - changes not needing a write (AlreadyFixed / Skipped) are recorded from the pre-read;
#  - written changes: live call == dry call except dry_run=false, request/sub-request SUCCESS, post-read url == new
#    and no other non-volatile field changed -> Fixed, else Failed.
import json, sys
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/snap7_work')
from common import *

args = [a for a in sys.argv[1:] if not a.startswith('--')]
commit = '--commit' in sys.argv
idx, pre_seq = int(args[0]), int(args[1])
wseq = [int(x) for x in args[2:5]] if len(args) >= 5 else None
u = units()[idx]
B = by_seq()
preo = B[pre_seq]
pre = creatives_of(preo)
pre_req = preo['result']['data']['data'].get('request_id')
lines = []
if wseq:
    dry_seq, live_seq, post_seq = wseq
    d, l, q = B[dry_seq], B[live_seq], B[post_seq]
    gp = []
    di, li = dict(d['input']), dict(l['input'])
    if di.pop('dry_run', None) is not True: gp.append('dry seq not dry_run=true')
    if li.pop('dry_run', None) is not False: gp.append('live seq not dry_run=false')
    if di != li: gp.append('live call != dry call (apart from dry_run)')
    if li.get('action') != UPDATE_ACTION: gp.append('live action %r' % li.get('action'))
    if account_of(l) != u['account_id']: gp.append('live account %r' % account_of(l))
    sent = {x['id']: x for x in payload_of(l)['creatives']}
    try:
        ld = l['result']['data']['data']
        live_req, live_status = ld.get('request_id'), ld.get('request_status')
        subst = {x['creative']['id']: x.get('sub_request_status') for x in ld.get('creatives', []) if isinstance(x, dict) and 'creative' in x}
        subfail = {x.get('creative', {}).get('id', '?'): x for x in ld.get('creatives', []) if isinstance(x, dict) and x.get('sub_request_status') != 'SUCCESS'}
    except Exception as e:
        live_req, live_status, subst, subfail = None, 'UNREADABLE %r' % e, {}, {}
        print(l['raw'][:3000])
    if live_status != 'SUCCESS': gp.append('live request_status %s' % live_status)
    post = creatives_of(q)
    post_req = q['result']['data']['data'].get('request_id')
    if q['input'].get('action') not in ('snapchat_adaccounts_ad_account_id_get_creatives_by_ids_get', 'snapchat_creatives_creative_id_get'):
        gp.append('post seq is not a read')
    print('live req', live_req, live_status, '| sub statuses', subst, '| post req', post_req, '| general problems', gp)
    parent_note = ''
    if pre.get(u['unit'], {}).get('type') == 'COMPOSITE':
        pa, pb = pre[u['unit']], post.get(u['unit'])
        if pb is None:
            parent_note = '; parent composite not in read-back'
        else:
            fa, fb = flat(pa), flat(pb)
            pd = [(k, fa.get(k, '<absent>'), fb.get(k, '<absent>')) for k in sorted(set(fa) | set(fb)) if fa.get(k, '<absent>') != fb.get(k, '<absent>')]
            pnv = [x for x in pd if x[0] not in VOLATILE]
            parent_note = '; side effect: parent composite %s (not written) review_status %s -> %s, semantic_id/updated_at regenerated, %s' % (
                u['unit'], pa.get('review_status'), pb.get('review_status'),
                'no other parent field changed' if not pnv else 'OTHER PARENT FIELDS CHANGED: %r' % pnv)
        print('parent:', parent_note)
for ci, c in enumerate(u['changes']):
    sub, pos = slot_target(u, c)
    o = pre[sub]
    before = o['web_view_properties']['url']
    cls, why = classify(before, c)
    if wseq and sub in sent:
        assert cls == 'WRITE'
        problems = list(gp)
        if flat(sent[sub]) != {**flat(o), 'web_view_properties.url': c['new']}:
            problems.append('payload object != pre-read except url')
        if subst.get(sub) != 'SUCCESS':
            problems.append('sub_request_status %r %s' % (subst.get(sub), json.dumps(subfail.get(sub), ensure_ascii=False)[:500] if sub in subfail else ''))
        a = post.get(sub)
        if a is None:
            problems.append('not in post-read')
            after = '<not read back>'
            vol, nonvol = [], []
        else:
            after = a['web_view_properties']['url']
            fp, fq = flat(o), flat(a)
            diffs = [(k, fp.get(k, '<absent>'), fq.get(k, '<absent>')) for k in sorted(set(fp) | set(fq)) if fp.get(k, '<absent>') != fq.get(k, '<absent>')]
            nonvol = [x for x in diffs if x[0] not in VOLATILE and x[0] != 'web_view_properties.url']
            vol = [x for x in diffs if x[0] in VOLATILE]
            if nonvol:
                problems.append('other fields changed on re-read: %s' % nonvol)
        ok = after == c['new'] and not problems
        result = 'Fixed' if ok else 'Failed'
        sc = [k for k in ('name', 'headline', 'brand_name') if special_chars(o.get(k))]
        detail = ("%s; pre-read (req %s) url == plan %s; PUT /v1/adaccounts/{id}/creatives (%s) with the full creative object as read, "
                  "only web_view_properties.url changed%s; dry_run preview checked first (sent body byte-identical to the read except url, "
                  "verified from raw tool results%s); live request_status %s, sub_request %s, req %s; read-back (req %s) url %s; "
                  "review_status %s -> %s (%s)%s; %s") % (
            'COMPOSITE sub-creative %s (creative_ids[%d] of %s)' % (sub, pos, u['unit']) if pos is not None else 'WEB_VIEW creative',
            pre_req, why, UPDATE_ACTION,
            ' (%d sub-creatives of this composite in one PUT)' % len(sent) if len(sent) > 1 else '',
            '; non-ASCII/special chars in ' + '/'.join(sc) + ' sent as \\u escapes' if sc else '',
            live_status, subst.get(sub), live_req, post_req,
            'matches new byte for byte' if after == c['new'] else 'DOES NOT match new',
            o.get('review_status'), a.get('review_status') if a else '?',
            'PUT triggers re-review; already re-approved at read-back' if a and a.get('review_status') == 'APPROVED' else 're-review triggered by the PUT',
            '; server changed: ' + ', '.join('%s %r->%r' % x for x in vol if x[0] != 'review_status') if vol else '',
            'all other fields unchanged on re-read' if a is not None and not nonvol else 'PROBLEMS: ' + ' | '.join(problems))
        detail += parent_note
        if problems and 'PROBLEMS' not in detail:
            detail += ' | PROBLEMS: ' + ' | '.join(problems)
        lines.append((c, before, after, result, detail))
    else:
        if cls == 'AlreadyFixed':
            lines.append((c, before, before, 'AlreadyFixed', 'pre-read (req %s, updated_at %s, review_status %s): live url already equals new (%s); no write' % (
                pre_req, o.get('updated_at'), o.get('review_status'), why)))
        elif cls == 'Skipped':
            lines.append((c, before, before, 'Skipped', 'changed since plan: %s' % before))
        elif cls == 'WRITE' and excluded(u, c):
            lines.append((c, before, before, 'Skipped', 'slot is in excl_platform_refused_v2.json (platform-refused); not written'))
        else:
            print('change', ci, 'class', cls, why, '-> not handled here (needs a write or manual record)')
            continue
for c, before, after, result, detail in lines:
    print(result, c['slot'][:90], '| after==new', after == c['new'])
    print('   ', detail[:1200])
if commit:
    for c, before, after, result, detail in lines:
        append(u, c, before, after, result, detail)
    print('COMMITTED', len(lines))
