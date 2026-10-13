"""Read-only checker for apply9 in_google_2 (prints only; writes no files).

Reads exact tool-result text from this agent's transcript by meta.requestId.

usage:
  python3 -I chk.py pre    <gaql_req_id> [...]            classify every input unit found in the read(s)
  python3 -I chk.py preview <mutate_req_id> <ad_id> [...]   check a dry-run (or live) mutate request vs input
  python3 -I chk.py verify <gaql_req_id> [...] -- <ad_id> [...]   byte-compare read-back with "new"
"""
import json, sys
from urllib.parse import urlsplit, parse_qsl

D = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
IN = D + '/apply9/in_google_2.json'
EXCL = D + '/work/excl_platform_refused_v2.json'
T = ('/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/'
     'wf_295a17c2-06d/agent-ae5bbc038fa15565d.jsonl')


def transcript():
    calls, results = {}, {}
    for line in open(T):
        try:
            e = json.loads(line)
        except Exception:
            continue
        content = (e.get('message') or {}).get('content')
        if not isinstance(content, list):
            continue
        for c in content:
            if not isinstance(c, dict):
                continue
            if c.get('type') == 'tool_use':
                calls[c['id']] = (c.get('name'), c.get('input'))
            elif c.get('type') == 'tool_result':
                rc = c.get('content')
                if isinstance(rc, list):
                    txt = ''.join(x.get('text', '') for x in rc if isinstance(x, dict) and x.get('type') == 'text')
                else:
                    txt = rc if isinstance(rc, str) else json.dumps(rc)
                results[c['tool_use_id']] = txt
    return calls, results


CALLS, RESULTS = transcript()


def by_req(req_id):
    for tid, txt in RESULTS.items():
        if req_id not in txt:
            continue
        try:
            j = json.loads(txt)
        except Exception:
            continue
        if (j.get('meta') or {}).get('requestId') == req_id:
            return CALLS.get(tid, (None, None))[1], j
    raise SystemExit('request id not found in transcript: ' + req_id)


def gaql_rows(req_id):
    inp, j = by_req(req_id)
    d = j['data']
    assert d.get('action') == 'google_ads_v23_google_ads_search', d.get('action')
    res = d['data']['data'].get('results', [])
    bad = [r for r in res if not isinstance(r, dict)]
    if bad or (j.get('meta') or {}).get('mcp_output_budget'):
        print('WARNING', req_id, 'non-dict rows or output budget:', bad[:3], (j.get('meta') or {}).get('mcp_output_budget'))
    if d['data']['data'].get('nextPageToken'):
        print('WARNING', req_id, 'has nextPageToken')
    return [r for r in res if isinstance(r, dict)]


def row_info(r):
    aga = r['adGroupAd']; ad = aga['ad']
    fu = ad.get('finalUrls', [])
    suf = ad.get('finalUrlSuffix')
    land = fu[0] if fu else None
    if suf and land is not None:
        land = land + ('&' if '?' in land else '?') + suf
    return {
        'id': ad['id'], 'type': ad.get('type'), 'final_urls': fu, 'suffix': suf,
        'tut': ad.get('trackingUrlTemplate'), 'status': aga.get('status'),
        'approval': (aga.get('policySummary') or {}).get('approvalStatus'),
        'ad_group': r['adGroup']['id'], 'ad_group_name': r['adGroup'].get('name'),
        'campaign': r['campaign']['id'], 'campaign_status': r['campaign'].get('status'),
        'parent_suffix': [r['adGroup'].get('finalUrlSuffix'), r['campaign'].get('finalUrlSuffix'), r['customer'].get('finalUrlSuffix')],
        'parent_tut': [r['adGroup'].get('trackingUrlTemplate'), r['campaign'].get('trackingUrlTemplate'), r['customer'].get('trackingUrlTemplate')],
        'landing': land,
    }


def norm(u):
    s = urlsplit(u)
    return (s.scheme, s.netloc, s.path, s.fragment, tuple(sorted(parse_qsl(s.query, keep_blank_values=True))))


def classify(cur, ch):
    if cur is not None and norm(cur) == norm(ch['new']):
        return 'AlreadyFixed'
    if cur == ch['now'] or cur in (ch.get('alt_now') or []):
        return 'Write'
    return 'Skipped'


UNITS = json.load(open(IN))
U = {u['unit']: u for u in UNITS}
EX = {(e['ad_id'], e['slot']) for e in json.load(open(EXCL)) if e['platform'] == 'google'}


def rows_for(req_ids):
    rows = {}
    for rid in req_ids:
        for r in gaql_rows(rid):
            i = row_info(r)
            i['req'] = rid
            if i['id'] in rows:
                print('WARNING duplicate row', i['id'])
            rows[i['id']] = i
    return rows


def main():
    mode = sys.argv[1]
    if mode == 'pre':
        rows = rows_for(sys.argv[2:])
        from collections import Counter
        cnt = Counter()
        writes = []
        for u in UNITS:
            aid = u['unit']; ch = u['changes'][0]
            r = rows.get(aid)
            if r is None:
                continue
            cls = classify(r['landing'], ch)
            flags = []
            if len(r['final_urls']) != 1: flags.append('final_urls_len=%d' % len(r['final_urls']))
            if r['suffix']: flags.append('AD_SUFFIX=%s' % r['suffix'])
            if r['tut']: flags.append('AD_TUT=%s' % r['tut'])
            if any(r['parent_suffix']): flags.append('PARENT_SUFFIX=%s' % r['parent_suffix'])
            if any(r['parent_tut']): flags.append('PARENT_TUT=%s' % r['parent_tut'])
            if (aid, ch['slot']) in EX: flags.append('EXCLUDED')
            how = 'exact_now' if r['landing'] == ch['now'] else ('exact_new' if r['landing'] == ch['new'] else ('in_alt' if r['landing'] in (ch.get('alt_now') or []) else '-'))
            cnt[cls] += 1
            print('%-12s %-13s %-9s %-22s %-7s %-7s %-12s %s %s' % (aid, cls, how, r['type'], r['status'], r['campaign_status'], r['approval'], r['req'][:8], flags if flags else ''))
            if cls == 'Skipped':
                print('    CUR:', r['landing'])
            if cls == 'Write' and not flags:
                writes.append(aid)
        missing = [u['unit'] for u in UNITS if u['unit'] in rows]
        print('found %d of %d units in read(s); classes %s' % (len(missing), len(UNITS), dict(cnt)))
        print('WRITE_UNITS', ','.join(writes))
    elif mode == 'preview':
        rid = sys.argv[2]; want = sys.argv[3:]
        inp, j = by_req(rid)
        d = j['data']
        body = d.get('body')
        print('dry_run flag in response:', d.get('dry_run'), '| input dry_run:', inp.get('dry_run'), '| action:', inp.get('action'), '| account:', inp.get('account_id'))
        sent = inp.get('params')
        ops_src = {'params(sent)': sent.get('operations') if sent else None}
        if body is not None:
            ops_src['body(preview)'] = body.get('operations')
            print('body keys:', sorted(body.keys()), '| params == body:', json.dumps(sent, sort_keys=True) == json.dumps(body, sort_keys=True))
        ok = True
        for label, ops in ops_src.items():
            seen = []
            for op in ops or []:
                upd = op.get('update') or {}
                rn = upd.get('resource_name', '')
                aid = rn.rsplit('/', 1)[-1]
                seen.append(aid)
                u = U.get(aid)
                probs = []
                if set(op.keys()) != {'update', 'update_mask'}: probs.append('op keys %s' % sorted(op.keys()))
                if set(upd.keys()) != {'resource_name', 'final_urls'}: probs.append('update keys %s' % sorted(upd.keys()))
                if op.get('update_mask') != 'final_urls': probs.append('mask %r' % op.get('update_mask'))
                if u is None:
                    probs.append('NOT IN INPUT')
                else:
                    if rn != 'customers/%s/ads/%s' % (u['account_id'], aid): probs.append('resource_name %s' % rn)
                    if inp.get('account_id') != u['account_id']: probs.append('account %s' % inp.get('account_id'))
                    if upd.get('final_urls') != [u['changes'][0]['new']]: probs.append('final_urls differ: %r' % (upd.get('final_urls'),))
                    if (aid, u['changes'][0]['slot']) in EX: probs.append('EXCLUDED')
                if probs:
                    ok = False
                    print('PROBLEM', label, aid, probs)
            if sorted(seen) != sorted(want) or len(seen) != len(set(seen)):
                ok = False
                print('PROBLEM', label, 'op set differs from expected:', sorted(set(seen) ^ set(want)), 'dups' if len(seen) != len(set(seen)) else '')
            print(label, 'ops:', len(seen))
        res = (d.get('data') or {}).get('data') if isinstance(d.get('data'), dict) else None
        if res is not None:
            print('live response results:', json.dumps(res, ensure_ascii=False)[:2000])
        print('requestId', (j.get('meta') or {}).get('requestId'), 'warnings', d.get('warnings'))
        print('PREVIEW_OK' if ok else 'PREVIEW_NOT_OK')
    elif mode == 'verify':
        args = sys.argv[2:]
        sep = args.index('--')
        rows = rows_for(args[:sep])
        want = args[sep + 1:]
        good = 0
        for aid in want:
            ch = U[aid]['changes'][0]
            r = rows.get(aid)
            if r is None:
                print(aid, 'NOT IN READ-BACK')
                continue
            byte_eq = r['final_urls'] == [ch['new']] and not r['suffix'] and r['landing'] == ch['new']
            clean = not any(r['parent_suffix']) and not any(r['parent_tut']) and not r['tut']
            good += byte_eq
            print(aid, 'BYTE_EQUAL_NEW' if byte_eq else 'MISMATCH', 'parents_clean' if clean else 'PARENT/TRACKING SET',
                  r['status'], r['campaign_status'], r['approval'], r['req'])
            if not byte_eq:
                print('   live:', json.dumps(r['final_urls'], ensure_ascii=False), 'suffix:', r['suffix'])
                print('   new :', ch['new'])
        print('verified %d of %d' % (good, len(want)))
    elif mode == 'ops':
        ops = []
        for aid in sys.argv[2:]:
            u = U[aid]; ch = u['changes'][0]
            assert u['unit_type'] == 'ad' and ch['slot'] == 'ad.final_urls[0]' and (aid, ch['slot']) not in EX
            ops.append({'update': {'resource_name': 'customers/%s/ads/%s' % (u['account_id'], aid), 'final_urls': [ch['new']]},
                        'update_mask': 'final_urls'})
        print(json.dumps({'operations': ops}, ensure_ascii=False))
    else:
        raise SystemExit('unknown mode')


main()
