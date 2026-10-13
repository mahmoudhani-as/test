#!/usr/bin/env python3
"""apply11 Snapchat snap_split batch 4 helper (apply11/in_snapchat_snap_split_4.json).

Tool inputs/results are read from this agent's own transcript, so every comparison is byte-exact.

  h4.py calls [from_seq]                       list snapchat calls: seq, action, dry_run, request ids/status
  h4.py pre <u> <cr_seq> <ad_seq...>           classify unit u from the reads; write u<u>_cr_payload.json
                                               (copy of the creative, settable fields only, url = new)
  h4.py dry <u> cr|ad <dry_seq>                dry-run input == payload file? preview body == payload?
  h4.py live <u> cr|ad <dry_seq> <live_seq>    live input == dry input except dry_run? status / ids
  h4.py postcr <u> <seq>                       new creative read-back: url == new? other copied fields same?
  h4.py adpre <u> <new_cid> <ad_seq...>        write u<u>_ad_payload_<ad>.json (full ad as read, creative_id = new)
  h4.py adpost <u> <new_cid> <ad_seq...>       ad read-back: creative_id == new, status/name/... unchanged
  h4.py led <u> key=value ...                  store notes / seqs in ledger.json
  h4.py results                                print the results array from ledger.json
"""
import json, re, sys, os, unicodedata
from urllib.parse import urlsplit, parse_qsl

BASE = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/'
IN = BASE + 'apply11/in_snapchat_snap_split_4.json'
W = BASE + 'apply11/work_snapchat_snap_split_4/'
LEDGER = W + 'ledger.json'
EXCL = BASE + 'work/excl_platform_refused_v2.json'
T = ('/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/'
     'wf_3774299d-bd5/agent-a2328e16f935d7be1.jsonl')
CR_READ = ('snapchat_creatives_creative_id_get', 'snapchat_adaccounts_ad_account_id_get_creatives_by_ids_get',
           'snapchat_creative_get', 'snapchat_creative_get_by_ids')
AD_READ = ('snapchat_ads_ad_id_get', 'snapchat_ad_get', 'snapchat_ad_get_by_ids',
           'snapchat_adaccounts_ad_account_id_get_ads_by_ids_get')
CR_CREATE = ('snapchat_creative_create', 'snapchat_adaccounts_ad_account_id_creatives_create')
AD_PUT = ('snapchat_ad_replace', 'snapchat_adsquads_ad_squad_id_ads_update')
# fields of the read creative that are not copied into the new one (id, timestamps, review, semantic, server status, audit)
NOT_COPIED = {'id', 'updated_at', 'created_at', 'review_status', 'review_status_details', 'semantic_id',
              'packaging_status', 'created_by_app_id', 'created_by_user', 'last_updated_by_app_id',
              'last_updated_by_user'}
VOLATILE_AD = {'updated_at', 'review_status', 'review_status_details', 'delivery_status',
               'created_by_app_id', 'created_by_user', 'last_updated_by_app_id', 'last_updated_by_user'}


def units():
    return json.load(open(IN, encoding='utf-8'))


def same_url(a, b):
    if a == b:
        return True
    sa, sb = urlsplit(a), urlsplit(b)
    return ((sa.scheme, sa.netloc, sa.path, sa.fragment) == (sb.scheme, sb.netloc, sb.path, sb.fragment)
            and sorted(parse_qsl(sa.query, keep_blank_values=True)) == sorted(parse_qsl(sb.query, keep_blank_values=True)))


def classify(cur, c):
    if cur == c['new']:
        return 'AlreadyFixed', 'cur == new byte for byte'
    if same_url(cur, c['new']):
        return 'AlreadyFixed', 'cur == new (same params, different order)'
    if cur == c['now']:
        return 'WRITE', 'now'
    if cur in c['alt_now']:
        return 'WRITE', 'alt_now[%d]' % c['alt_now'].index(cur)
    return 'Skipped', 'changed since plan'


def excluded(u, c):
    ex = json.load(open(EXCL, encoding='utf-8'))
    ids = set(u['ad_ids']) | {u['unit'], u.get('creative_id')}
    return [e for e in ex if e.get('platform') == 'snapchat'
            and (e.get('ad_id') in ids or e.get('unit') in ids)]


def flat(d, p=''):
    r = {}
    for k, v in d.items():
        kp = p + k
        if isinstance(v, dict) and v:
            r.update(flat(v, kp + '.'))
        else:
            r[kp] = v
    return r


def _load_text(txt):
    try:
        return json.loads(txt)
    except Exception:
        pass
    m = re.search(r'saved to:?\s*(/\S+)', txt or '')
    if m and os.path.exists(m.group(1)):
        raw = open(m.group(1), encoding='utf-8').read()
        try:
            o = json.loads(raw)
        except Exception:
            return None
        if isinstance(o, list) and o and isinstance(o[0], dict) and 'text' in o[0]:
            try:
                return json.loads(''.join(x.get('text', '') for x in o))
            except Exception:
                return None
        return o
    return None


def calls():
    inputs, out, seen = {}, [], set()
    for line in open(T, encoding='utf-8'):
        try:
            m = json.loads(line)
        except Exception:
            continue
        content = (m.get('message') or {}).get('content')
        if not isinstance(content, list):
            continue
        for it in content:
            if not isinstance(it, dict):
                continue
            if it.get('type') == 'tool_use' and 'snapchat_native_action' in (it.get('name') or ''):
                inputs.setdefault(it['id'], it.get('input') or {})
            elif it.get('type') == 'tool_result' and it.get('tool_use_id') in inputs and it['tool_use_id'] not in seen:
                seen.add(it['tool_use_id'])
                cc = it.get('content')
                txt = ''.join(x.get('text', '') for x in cc if isinstance(x, dict)) if isinstance(cc, list) else (cc or '')
                out.append({'seq': len(out) + 1, 'id': it['tool_use_id'], 'input': inputs[it['tool_use_id']],
                            'result': _load_text(txt), 'raw': txt, 'is_error': it.get('is_error')})
    return out


def by_seq():
    return {o['seq']: o for o in calls()}


def inner(o):
    r = o['result']
    if not isinstance(r, dict):
        return None
    d = r.get('data')
    if isinstance(d, dict) and isinstance(d.get('data'), dict):
        return d['data']
    return None


def objs_of(o, kind):
    d = inner(o) or {}
    return [x for x in d.get(kind + 's', []) if isinstance(x, dict)]


def req_of(o):
    d = inner(o) or {}
    return d.get('request_id'), d.get('request_status')


def payload_of(o):
    p = o['input'].get('payload')
    if isinstance(p, str):
        p = json.loads(p)
    return p


def special_chars(s):
    if not isinstance(s, str):
        return []
    r = ['U+%04X %s' % (ord(ch), unicodedata.name(ch, '?')) for ch in s if ord(ch) > 0x7e]
    if '  ' in s:
        r.append('double-space')
    if s != s.strip():
        r.append('leading/trailing space')
    return r


def ledger():
    try:
        return json.load(open(LEDGER, encoding='utf-8'))
    except Exception:
        return {}


def save_ledger(L):
    json.dump(L, open(LEDGER, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def read_creative(B, s):
    o = B[s]
    if o['input'].get('action') not in CR_READ:
        raise SystemExit('seq %d is not a creative read: %s' % (s, o['input'].get('action')))
    rid, st = req_of(o)
    if st != 'SUCCESS':
        raise SystemExit('seq %d read status %r raw=%s' % (s, st, o['raw'][:1500]))
    return {x['creative']['id']: x['creative'] for x in objs_of(o, 'creative') if 'creative' in x}, rid


def read_ads(B, s):
    o = B[s]
    if o['input'].get('action') not in AD_READ:
        raise SystemExit('seq %d is not an ad read: %s' % (s, o['input'].get('action')))
    rid, st = req_of(o)
    if st != 'SUCCESS':
        raise SystemExit('seq %d read status %r raw=%s' % (s, st, o['raw'][:1500]))
    return {x['ad']['id']: x['ad'] for x in objs_of(o, 'ad') if 'ad' in x}, rid


def cmd_calls(a):
    frm = int(a[0]) if a else 1
    for o in calls():
        if o['seq'] < frm:
            continue
        i = o['input']
        d = inner(o) or {}
        ids = []
        for kind in ('creative', 'ad'):
            for x in objs_of(o, kind):
                ob = x.get(kind) or {}
                ids.append('%s:%s/%s' % (kind, ob.get('id'), x.get('sub_request_status')))
        print(o['seq'], i.get('action'), 'dry_run=%s' % i.get('dry_run'), (i.get('path_params') or {}),
              'req=%s/%s' % (d.get('request_id'), d.get('request_status')), ids,
              'ERR' if o['is_error'] else '', ('' if o['result'] else 'UNPARSED:' + o['raw'][:300]))


def cmd_pre(a):
    u = int(a[0]); cr_seq = int(a[1]); ad_seqs = [int(x) for x in a[2:]]
    U = units()[u]; c = U['changes'][0]
    assert len(U['changes']) == 1, 'unit has %d changes' % len(U['changes'])
    assert c['slot'] == 'creative.web_view_properties.url', c['slot']
    B = by_seq()
    crs, crid = read_creative(B, cr_seq)
    ads = {}
    for s in ad_seqs:
        x, rid = read_ads(B, s)
        for k, v in x.items():
            ads[k] = (v, rid, s)
    print('unit', u, U['unit'], 'creative', U['creative_id'], 'ads', U['ad_ids'])
    ex = excluded(U, c)
    if ex:
        print('EXCLUDED:', ex)
    # every ad must still use the unit's creative
    cur_cids = set()
    for aid in U['ad_ids']:
        if aid not in ads:
            raise SystemExit('ad %s not read' % aid)
        ad = ads[aid][0]
        print(' ad', aid, 'creative_id', ad['creative_id'], 'status', ad['status'], 'squad', ad['ad_squad_id'],
              'type', ad.get('type'), 'review', ad.get('review_status'), 'read req', ads[aid][1])
        cur_cids.add(ad['creative_id'])
    if cur_cids != {U['creative_id']}:
        print('NOTE: ads point to', cur_cids, '(unit creative %s)' % U['creative_id'])
    cid = list(cur_cids)[0] if len(cur_cids) == 1 else None
    if cid not in crs:
        raise SystemExit('creative %s (current of the ads) not in read seq %d' % (cid, cr_seq))
    cr = crs[cid]
    print(' creative type', cr['type'], 'review', cr.get('review_status'), 'read req', crid)
    if cr['type'] != 'WEB_VIEW':
        raise SystemExit('creative type %s is not WEB_VIEW' % cr['type'])
    cur = cr['web_view_properties']['url']
    res, why = classify(cur, c)
    print(' cur  ', cur)
    print(' now  ', c['now'])
    print(' new  ', c['new'])
    print(' CLASSIFY', res, why)
    for k, v in flat(cr).items():
        sc = special_chars(v)
        if sc:
            print(' special chars in', k, sc)
    L = ledger(); e = L.setdefault(str(u), {})
    e.update({'pre_cr_seq': cr_seq, 'pre_cr_req': crid, 'pre_ad_seqs': ad_seqs, 'before': cur,
              'classify': res, 'classify_why': why, 'orig_cid': cid,
              'orig_ads': {aid: ads[aid][0] for aid in U['ad_ids']}, 'orig_creative': cr})
    save_ledger(L)
    if res != 'WRITE':
        print('NO WRITE')
        return
    new_cr = {k: v for k, v in cr.items() if k not in NOT_COPIED}
    new_cr['web_view_properties'] = dict(cr['web_view_properties'])
    new_cr['web_view_properties']['url'] = c['new']
    payload = {'creatives': [new_cr]}
    fn = W + 'u%d_cr_payload.json' % u
    json.dump(payload, open(fn, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(' dropped (not copied):', sorted(k for k in cr if k in NOT_COPIED))
    print(' copied:', sorted(new_cr))
    print('PAYLOAD', fn)
    print(json.dumps(payload, ensure_ascii=True))


def body_of_dry(o):
    d = inner(o) or {}
    return (d.get('request') or {}).get('body'), (d.get('request') or {}).get('method'), (d.get('request') or {}).get('url')


def cmd_dry(a):
    u = int(a[0]); kind = a[1]; s = int(a[2])
    B = by_seq(); o = B[s]
    acts = CR_CREATE if kind == 'cr' else AD_PUT
    if o['input'].get('action') not in acts:
        raise SystemExit('seq %d action %s not in %s' % (s, o['input'].get('action'), acts))
    if o['input'].get('dry_run') is not True:
        raise SystemExit('seq %d is not a dry run' % s)
    fns = [W + 'u%d_cr_payload.json' % u] if kind == 'cr' else sorted(
        W + f for f in os.listdir(W) if f.startswith('u%d_ad_payload_' % u))
    if kind == 'ad':
        ad_in = payload_of(o)['ads'][0]['id']
        fns = [W + 'u%d_ad_payload_%s.json' % (u, ad_in)]
    want = json.load(open(fns[0], encoding='utf-8'))
    got = payload_of(o)
    print('input payload == file %s: %s' % (os.path.basename(fns[0]), got == want))
    body, meth, url = body_of_dry(o)
    print('preview', meth, url)
    print('preview body == payload:', body == want)
    if body != want:
        fw, fb = flat(want['creatives' if kind == 'cr' else 'ads'][0]), flat((body or {}).get('creatives' if kind == 'cr' else 'ads', [{}])[0])
        for k in sorted(set(fw) | set(fb)):
            if fw.get(k) != fb.get(k):
                print('  DIFF', k, repr(fw.get(k))[:200], '->', repr(fb.get(k))[:200])
    print('top-level input keys:', {k: v for k, v in o['input'].items() if k != 'payload'})
    print('result success:', (o['result'] or {}).get('success'), 'warnings:', (inner(o) or {}).get('warnings'))


def cmd_live(a):
    u = int(a[0]); kind = a[1]; ds = int(a[2]); ls = int(a[3])
    B = by_seq(); d, l = B[ds], B[ls]
    di = dict(d['input']); li = dict(l['input'])
    if li.get('dry_run') is not False:
        raise SystemExit('seq %d is not live' % ls)
    di.pop('dry_run', None); li.pop('dry_run', None)
    print('live input == dry input (except dry_run):', di == li)
    rid, st = req_of(l)
    print('request', rid, st, 'is_error', l['is_error'])
    kindn = 'creative' if kind == 'cr' else 'ad'
    for x in objs_of(l, kindn):
        ob = x.get(kindn) or {}
        print(' sub', x.get('sub_request_status'), x.get('sub_request_error_reason'), 'id', ob.get('id'),
              'review', ob.get('review_status'), 'status', ob.get('status'), 'creative_id', ob.get('creative_id'))
        if kind == 'cr':
            print('  url', (ob.get('web_view_properties') or {}).get('url'))
    if st != 'SUCCESS':
        print('RAW', l['raw'][:3000])


def cmd_postcr(a):
    u = int(a[0]); s = int(a[1])
    U = units()[u]; c = U['changes'][0]
    B = by_seq()
    L = ledger(); e = L[str(u)]
    crs, rid = read_creative(B, s)
    ncid = e.get('new_cid')
    if ncid not in crs:
        raise SystemExit('new creative %s not in seq %d' % (ncid, s))
    nc = crs[ncid]; oc = e['orig_creative']
    url = nc['web_view_properties']['url']
    print('new creative', ncid, 'read req', rid)
    print(' url ', url)
    print(' new ', c['new'])
    print(' url == new byte for byte:', url == c['new'])
    fo, fn = flat(oc), flat(nc)
    diffs = []
    for k in sorted(set(fo) | set(fn)):
        if k.split('.')[0] in NOT_COPIED:
            continue
        if k == 'web_view_properties.url':
            continue
        if fo.get(k) != fn.get(k):
            diffs.append((k, fo.get(k), fn.get(k)))
    for k, x, y in diffs:
        print('  DIFF', k, repr(x)[:200], '->', repr(y)[:200])
    print(' other copied fields identical:', not diffs)
    print(' review_status', nc.get('review_status'), nc.get('review_status_details'), 'packaging', nc.get('packaging_status'))
    e.update({'postcr_seq': s, 'postcr_req': rid, 'new_url': url, 'new_review': nc.get('review_status'),
              'new_cr_diffs': [[k, x, y] for k, x, y in diffs]})
    save_ledger(L)


def cmd_adpre(a):
    u = int(a[0]); ncid = a[1]; ad_seqs = [int(x) for x in a[2:]]
    U = units()[u]
    B = by_seq()
    ads = {}
    for s in ad_seqs:
        x, rid = read_ads(B, s)
        for k, v in x.items():
            ads[k] = (v, rid, s)
    L = ledger(); e = L[str(u)]
    for aid in U['ad_ids']:
        ad = ads[aid][0]
        orig = e['orig_ads'][aid]
        if ad['creative_id'] != e['orig_cid']:
            print('NOTE ad', aid, 'creative now', ad['creative_id'], '(was', e['orig_cid'], ')')
        fo, fn = flat(orig), flat(ad)
        for k in sorted(set(fo) | set(fn)):
            if fo.get(k) != fn.get(k):
                print('  ad changed since pre-read', aid, k, fo.get(k), '->', fn.get(k))
        p = dict(ad)
        p['creative_id'] = ncid
        payload = {'ads': [p]}
        fn_ = W + 'u%d_ad_payload_%s.json' % (u, aid)
        json.dump(payload, open(fn_, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('PAYLOAD', fn_, 'squad', ad['ad_squad_id'], 'read req', ads[aid][1])
        print(json.dumps(payload, ensure_ascii=True))
        e.setdefault('adpre', {})[aid] = {'seq': ads[aid][2], 'req': ads[aid][1], 'ad': ad}
    save_ledger(L)


def cmd_adpost(a):
    u = int(a[0]); ncid = a[1]; ad_seqs = [int(x) for x in a[2:]]
    U = units()[u]
    B = by_seq()
    ads = {}
    for s in ad_seqs:
        x, rid = read_ads(B, s)
        for k, v in x.items():
            ads[k] = (v, rid, s)
    L = ledger(); e = L[str(u)]
    ok = True
    for aid in U['ad_ids']:
        ad = ads[aid][0]
        before = e['adpre'][aid]['ad']
        print('ad', aid, 'creative_id', ad['creative_id'], '== new:', ad['creative_id'] == ncid,
              'status', before.get('status'), '->', ad.get('status'), 'review', before.get('review_status'), '->',
              ad.get('review_status'), 'delivery', ad.get('delivery_status'), 'read req', ads[aid][1])
        fo, fn = flat(before), flat(ad)
        for k in sorted(set(fo) | set(fn)):
            if k in ('creative_id',) or k.split('.')[0] in VOLATILE_AD:
                continue
            if fo.get(k) != fn.get(k):
                print('  OTHER FIELD CHANGED', k, fo.get(k), '->', fn.get(k))
                ok = False
        if ad['creative_id'] != ncid:
            ok = False
        e.setdefault('adpost', {})[aid] = {'seq': ads[aid][2], 'req': ads[aid][1], 'creative_id': ad['creative_id'],
                                            'status': ad.get('status'), 'review_status': ad.get('review_status'),
                                            'review_status_details': ad.get('review_status_details'),
                                            'delivery_status': ad.get('delivery_status')}
    print('ALL OK:', ok)
    save_ledger(L)


def cmd_led(a):
    u = a[0]
    L = ledger(); e = L.setdefault(str(u), {})
    for kv in a[1:]:
        k, v = kv.split('=', 1)
        try:
            v = json.loads(v)
        except Exception:
            pass
        e[k] = v
    save_ledger(L)
    print(json.dumps({k: v for k, v in e.items() if k not in ('orig_ads', 'orig_creative', 'adpre')}, ensure_ascii=False)[:3000])


def cmd_results(a):
    L = ledger(); out = []
    for i, U in enumerate(units()):
        e = L.get(str(i), {})
        for c in U['changes']:
            r = {'platform': 'snapchat', 'account_id': U['account_id'], 'unit_type': U['unit_type'], 'unit': U['unit'],
                 'ad_ids': U['ad_ids'], 'ad_names': U['ad_names'], 'slot': c['slot'],
                 'before': e.get('before', ''), 'after_expected': c['new'],
                 'after_live': e.get('after_live', e.get('before', '')),
                 'result': e.get('result', 'NotAttempted'), 'new_entity_ids': e.get('new_entity_ids', ''),
                 'detail': e.get('detail', '')}
            out.append(r)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    cmd = sys.argv[1]; args = sys.argv[2:]
    globals()['cmd_' + cmd](args)
