#!/usr/bin/env python3
"""Build the final results (stdout only) from the transcript + ledger, compact details.

  final.py print <from> <to>   print entries [from, to) one per line
  final.py check               read a JSON array from stdin, compare with the built results field by field
"""
import json, sys
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply8/work_snapchat_2')
import h

U8_DETAIL = ("blocked by session safety check: Bash 'python3 h.py calls 38 && python3 h.py dry 8 38' (local byte-exact check of the "
             "snapchat_adaccounts_ad_account_id_creatives_update dry_run preview that must pass before the live PUT) "
             "Permission for this action was denied by the Claude Code auto mode classifier. Reason: [Modify Shared Resources]. "
             "Not retried, not re-routed; the live PUT was NOT sent (only the dry_run=true preview, gateway req "
             "17250875-d9c8-425d-8464-4f1655b6e28b, no change). Pre-read GET req 06507cb2-222e-4f6a-b1c9-cce14c2d0b1b: URL == now; "
             "final re-read req 39af4bc6-3d6b-45cc-9d95-58160ef7ec76: creative untouched (URL still == now, updated_at "
             "2026-03-17T09:59:21.189Z, review_status APPROVED).")


def build():
    B = h.by_seq()
    L = h.ledger()
    out = []
    for ui, u in enumerate(h.units()):
        e = L[str(ui)]
        pre, psrc = h.reads(B, e['pre'])
        parent = pre[u['unit']]
        comp = parent.get('type') == 'COMPOSITE'
        for ci, c in enumerate(u['changes']):
            sub, pos = h.slot_target(u, c)
            o = pre[sub]
            before = o['web_view_properties']['url']
            if ui == 8:
                assert 'live' not in e and before == c['now']
                out.append(h._rec(u, c, before, before, 'Failed', U8_DETAIL))
                continue
            live = B[e['live']]
            lreq, lst = h.req_of(live)
            lsub = {x['creative']['id']: x.get('sub_request_status') for x in h.inner(live)['creatives'] if 'creative' in x}
            sent = {x['id']: x for x in h.payload_of(live)['creatives']}
            post, qsrc = h.reads(B, e['post'])
            fin, fsrc = h.reads(B, e['final'])
            b, f = post[sub], fin[sub]
            after = b['web_view_properties']['url']
            cls, why = h.classify(before, c)
            fa, fb = h.flat(o), h.flat(b)
            other = [k for k in sorted(set(fa) | set(fb)) if fa.get(k, '<a>') != fb.get(k, '<a>')
                     and k not in h.VOLATILE and k not in h.AUDIT and k != 'web_view_properties.url']
            # payload sent == pre-read except url (byte-exact)
            exp = json.loads(json.dumps(o)); exp['web_view_properties']['url'] = c['new']
            assert sent[sub] == exp, 'payload mismatch'
            ok = (cls == 'WRITE' and lst == 'SUCCESS' and lsub.get(sub) == 'SUCCESS' and after == c['new'] and not other)
            assert ok, (ui, ci, cls, lst, lsub.get(sub), after == c['new'], other)
            n = len(sent)
            if comp:
                d = ('COMPOSITE %s: sub-creative %s (creative_ids[%d], index verified live); pre-read POST get_creatives_by_ids req %s: '
                     'live URL == %s (review_status %s, updated_at %s); one PUT /v1/adaccounts/%s/creatives for %s, each the full object as read '
                     'with only web_view_properties.url changed (dry_run preview == read except url, checked byte-exact); live request_status %s, '
                     'sub_request_status %s, req %s; read-back POST get_creatives_by_ids req %s: URL == new byte for byte, no other field changed '
                     '(updated_at/semantic_id regenerated); review_status %s -> %s after the write; final re-read req %s: URL == new, review_status %s; '
                     'side effect: parent composite %s (not written) review_status APPROVED -> PENDING_REVIEW (final re-read: %s), its creative_ids and other fields unchanged.') % (
                    u['unit'], sub, pos, psrc[sub][1], why, o.get('review_status'), o.get('updated_at'), u['account_id'],
                    'this sub-creative' if n == 1 else 'the %d sub-creatives of this unit' % n, lst, lsub.get(sub), lreq, qsrc[sub][1],
                    o.get('review_status'), b.get('review_status'), fsrc[sub][1], f.get('review_status'),
                    u['unit'], fin[u['unit']].get('review_status'))
            else:
                d = ('WEB_VIEW creative; pre-read GET req %s: live URL == %s (review_status %s, updated_at %s); PUT /v1/adaccounts/%s/creatives '
                     'with the full creative object as read, only web_view_properties.url changed (dry_run preview == read except url, checked '
                     'byte-exact); live request_status %s, sub_request_status %s, req %s; read-back GET req %s: URL == new byte for byte, no other '
                     'field changed (updated_at/semantic_id regenerated); review_status %s -> %s after the write; final re-read req %s: URL == new, '
                     'review_status %s.') % (
                    psrc[sub][1], why, o.get('review_status'), o.get('updated_at'), u['account_id'], lst, lsub.get(sub), lreq,
                    qsrc[sub][1], o.get('review_status'), b.get('review_status'), fsrc[sub][1], f.get('review_status'))
            assert f['web_view_properties']['url'] == c['new']
            out.append(h._rec(u, c, before, after, 'Fixed', d))
    assert len(out) == 28 and len({(r['unit'], r['slot']) for r in out}) == 28
    return out


if __name__ == '__main__':
    R = build()
    if sys.argv[1] == 'print':
        a, b = int(sys.argv[2]), int(sys.argv[3])
        for i in range(a, min(b, len(R))):
            print(json.dumps(R[i], ensure_ascii=False, separators=(',', ':')))
    elif sys.argv[1] == 'check':
        got = json.loads(sys.stdin.read())
        bad = 0
        if len(got) != len(R):
            print('COUNT', len(got), '!=', len(R)); bad += 1
        for i, (g, r) in enumerate(zip(got, R)):
            for k in r:
                if g.get(k) != r[k]:
                    bad += 1
                    print('DIFF entry %d field %s:\n  got  %r\n  want %r' % (i, k, g.get(k), r[k]))
            for k in g:
                if k not in r:
                    bad += 1; print('EXTRA entry %d field %s' % (i, k))
        print('CHECK', 'OK' if not bad else 'FAILED (%d diffs)' % bad)
