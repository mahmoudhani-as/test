import json, sys, os, uuid
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply9/work_google_3')
from lib import *
# usage: python3 -I step.py <tag> <verify_ids comma|-> <next_ids comma|-> <req_id> [<req_id> ...]
# verify: byte-for-byte read-back check vs "new"; next: fresh pre-read classification + batch payload (written to payload_<tag>.json)
tag, vids, nids = sys.argv[1], sys.argv[2], sys.argv[3]
rids = sys.argv[4:]
rows = {}
for rid in rids:
    rs, trunc, budget, inp = gaql_rows(rid)
    if trunc or (budget and budget.get('truncated')):
        print('WARNING truncated result', rid, trunc)
    for aid, lst in parse_rows(rs, rid).items():
        rows.setdefault(aid, []).extend(lst)
U = {u['unit']: u for u in units()}
ex = excluded()
os.makedirs(W + '/reads', exist_ok=True)
ver = {}
if vids != '-':
    for aid in vids.split(','):
        ch = U[aid]['changes'][0]
        lst = rows.get(aid)
        if not lst:
            print('VERIFY', aid, 'NOT IN READ'); ver[aid] = None; continue
        r = lst[0]
        byte_eq = r['final_urls'] == [ch['new']] and not r['final_url_suffix'] and r['landing'] == ch['new'] and all(x['final_urls'] == r['final_urls'] for x in lst)
        clean = not any(r['parent_suffix']) and not any(r['parent_tut']) and not r['tracking_url_template']
        ver[aid] = dict(r, byte_equal_new=byte_eq, parents_clean=clean, n_rows=len(lst))
        json.dump(dict(r, role='readback'), open(W + '/reads/%s_after.json' % aid, 'w'), indent=1, ensure_ascii=False)
        print('VERIFY', aid, 'BYTE_EQUAL_NEW' if byte_eq else 'MISMATCH', 'parents_clean' if clean else 'PARENT/TRACKING SET',
              r['status'], r['campaign_status'], r['approval'], r['req'])
        if not byte_eq:
            print('   live:', json.dumps(r['final_urls'], ensure_ascii=False), 'suffix:', r['final_url_suffix'])
            print('   new :', ch['new'])
    json.dump(ver, open(W + '/verify_%s.json' % tag, 'w'), indent=1, ensure_ascii=False)
    print('verified', sum(1 for v in ver.values() if v and v['byte_equal_new']), 'of', len(ver))
if nids != '-':
    ops = []; cls_out = {}
    for aid in nids.split(','):
        u = U[aid]; ch = u['changes'][0]
        lst = rows.get(aid)
        if not lst:
            print('NEXT', aid, 'NOT IN READ'); cls_out[aid] = {'cls': 'MISSING'}; continue
        r = lst[0]
        json.dump(dict(r, role='preread'), open(W + '/reads/%s_before.json' % aid, 'w'), indent=1, ensure_ascii=False)
        cls = classify(r['landing'], ch)
        flags = []
        if len(lst) > 1: flags.append('multi_rows=%d' % len(lst))
        if len(r['final_urls']) != 1: flags.append('final_urls_len=%d' % len(r['final_urls']))
        if any(r['parent_suffix']): flags.append('PARENT_SUFFIX=%s' % r['parent_suffix'])
        if any(r['parent_tut']) or r['tracking_url_template']: flags.append('TRACKING_TEMPLATE')
        if (aid, ch['slot']) in ex: flags.append('EXCLUDED')
        how = 'exact_now' if r['landing'] == ch['now'] else ('in_alt_now' if r['landing'] in ch.get('alt_now', []) else '')
        cls_out[aid] = {'cls': cls, 'how': how, 'flags': flags, 'cur': r['landing'], 'ad_suffix': r['final_url_suffix'], 'req': r['req'],
                        'status': r['status'], 'campaign_status': r['campaign_status'], 'approval': r['approval'], 'type': r['type']}
        print('NEXT', aid, cls, how, r['type'], r['status'], r['campaign_status'], r['approval'], 'suffix' if r['final_url_suffix'] else 'nosuffix', 'flags=%s' % flags)
        if cls == 'Write' and not flags:
            upd = {'resource_name': 'customers/%s/ads/%s' % (u['account_id'], aid), 'final_urls': [ch['new']]}
            mask = 'final_urls'
            if r['final_url_suffix']:
                upd['final_url_suffix'] = ''
                mask = 'final_urls,final_url_suffix'
            ops.append({'update': upd, 'update_mask': mask})
    json.dump(cls_out, open(W + '/class_%s.json' % tag, 'w'), indent=1, ensure_ascii=False)
    params = {'operations': ops}
    if len(ops) > 1:
        params['partial_failure'] = True
    json.dump(params, open(W + '/payload_%s.json' % tag, 'w'), ensure_ascii=False)
    from collections import Counter
    print('classes', Counter(v['cls'] for v in cls_out.values()), 'ops', len(ops))
    print('KEY', str(uuid.uuid4()))
