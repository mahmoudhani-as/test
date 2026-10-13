#!/usr/bin/env python3
"""apply8 Snapchat batch 2 helper (apply8/in_snapchat_2.json).

Raw tool inputs/results are read from this agent's own transcript, so every comparison is byte-exact.

  h.py calls [from_seq]                     list snapchat calls: seq, action, dry_run, ids, request status/ids
  h.py pre  <u> <seq> [seq ...]             classify unit u from the reads (later seqs win); verify composite slot
                                            indices; write u<u>_payload.json ({"creatives":[...]}, only url replaced)
                                            and print it ASCII-escaped for the write call
  h.py dry  <u> <dry_seq>                   dry-run input == payload file? preview body == payload?
  h.py live <u> <dry_seq> <live_seq>        live input == dry input except dry_run? statuses / request ids
  h.py post <u> <live_seq> <seq> [seq ...]  read-back: url == new byte for byte? any other field changed?
  h.py led  <u> key=value ...               store tool-call seq numbers / notes for unit u in ledger.json
  h.py results                              print the final results array (stdout only) from ledger + transcript
"""
import json, re, sys, os, unicodedata
from urllib.parse import urlsplit, parse_qsl

BASE = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/'
IN = BASE + 'apply8/in_snapchat_2.json'
W = BASE + 'apply8/work_snapchat_2/'
LEDGER = W + 'ledger.json'
EXCL = BASE + 'work/excl_platform_refused_v2.json'
T = ('/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/'
     'wf_12f54105-e78/agent-a7884ace029778a1b.jsonl')
UPDATE_ACTION = 'snapchat_adaccounts_ad_account_id_creatives_update'
READ_ACTIONS = ('snapchat_creatives_creative_id_get', 'snapchat_adaccounts_ad_account_id_get_creatives_by_ids_get',
                'snapchat_creative_get', 'snapchat_creative_get_by_ids')
VOLATILE = {'updated_at', 'semantic_id', 'review_status', 'review_status_details', 'packaging_status'}
AUDIT = {'created_by_app_id', 'created_by_user', 'last_updated_by_app_id', 'last_updated_by_user'}
SLOT_RE = re.compile(r'^creative\.composite_properties\.creative_ids\[(\d+)\] \(([0-9a-f-]{36})\)\.web_view_properties\.url$')


def units():
    return json.load(open(IN, encoding='utf-8'))


def same_url(a, b):
    if a == b:
        return True
    sa, sb = urlsplit(a), urlsplit(b)
    return ((sa.scheme, sa.netloc, sa.path, sa.fragment) == (sb.scheme, sb.netloc, sb.path, sb.fragment)
            and sorted(parse_qsl(sa.query, keep_blank_values=True)) == sorted(parse_qsl(sb.query, keep_blank_values=True)))


def slot_target(u, c):
    """-> (creative id holding the url, index in the parent composite or None)"""
    s = c['slot']
    if s == 'creative.web_view_properties.url':
        return u['unit'], None
    m = SLOT_RE.match(s)
    if not m:
        raise SystemExit('unexpected slot shape: ' + s)
    return m.group(2), int(m.group(1))


def classify(cur, c):
    if cur is None:
        return 'Skipped', 'no url'
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
    sub, _ = slot_target(u, c)
    ids = set(u['ad_ids']) | {u['unit'], u.get('creative_id'), sub}
    return [e for e in ex if e.get('platform') == 'snapchat'
            and (e.get('ad_id') in ids or e.get('unit') in ids) and e.get('slot') in (c['slot'], None)]


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
    """All snapchat_native_action calls of this agent, in result order: {seq, id, input, result, raw, is_error}."""
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


def creatives_of(o):
    d = inner(o) or {}
    return {x['creative']['id']: x['creative'] for x in d.get('creatives', []) if isinstance(x, dict) and 'creative' in x}


def req_of(o):
    d = inner(o) or {}
    return d.get('request_id'), d.get('request_status')


def payload_of(o):
    p = o['input'].get('payload')
    if isinstance(p, str):
        p = json.loads(p)
    return p


def account_of(o):
    i = o['input']
    return i.get('ad_account_id') or i.get('account_id') or (i.get('path_params') or {}).get('ad_account_id')


def reads(B, seqs):
    """creatives from read calls, later seqs overwrite earlier ones; -> (objs, {id: (seq, req)})"""
    objs, src = {}, {}
    for s in seqs:
        o = B[s]
        if o['input'].get('action') not in READ_ACTIONS:
            raise SystemExit('seq %d is not a read: %s' % (s, o['input'].get('action')))
        rid, st = req_of(o)
        if st != 'SUCCESS':
            raise SystemExit('seq %d read request_status %r raw=%s' % (s, st, o['raw'][:1500]))
        for cid, cr in creatives_of(o).items():
            objs[cid] = cr
            src[cid] = (s, rid)
    return objs, src


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
    except FileNotFoundError:
        return {}


# ---------------------------------------------------------------- commands

def cmd_calls(frm=1):
    for o in calls():
        if o['seq'] < frm:
            continue
        i = o['input']
        ids = []
        if 'path_params' in i:
            ids.append((i['path_params'] or {}).get('creative_id'))
        p = i.get('payload')
        if isinstance(p, dict):
            ids += p.get('ids', [])
            ids += [x.get('id') for x in p.get('creatives', []) if isinstance(x, dict)]
        rid, st = req_of(o) if o['result'] else (None, None)
        gw = (o['result'] or {}).get('meta', {}).get('requestId') if isinstance(o['result'], dict) else None
        print('#%d %s dry_run=%s acct=%s ids=%s | status=%s req=%s gw=%s err=%s' % (
            o['seq'], i.get('action'), i.get('dry_run'), account_of(o), [x[:8] for x in ids if x], st, rid, gw, o['is_error']))
        if o['result'] is None or (isinstance(o['result'], dict) and o['result'].get('success') is False):
            print('    RAW', o['raw'][:1500].replace('\n', ' '))


def cmd_pre(ui, seqs):
    u = units()[ui]
    B = by_seq()
    objs, src = reads(B, seqs)
    parent = objs.get(u['unit'])
    print('unit %d %s ads=%s names=%s status_11oct=%s' % (ui, u['unit'], u['ad_ids'], u['ad_names'], u.get('status_11oct')))
    if parent is None:
        raise SystemExit('parent creative not in the reads')
    assert parent['ad_account_id'] == u['account_id'], 'account mismatch'
    print('  parent type=%s review=%s updated_at=%s name=%r' % (parent.get('type'), parent.get('review_status'),
                                                             parent.get('updated_at'), parent.get('name')))
    payload = []
    for ci, c in enumerate(u['changes']):
        sub, pos = slot_target(u, c)
        if pos is not None:
            ids = (parent.get('composite_properties') or {}).get('creative_ids') or []
            where = ids.index(sub) if sub in ids else None
            print('  [%d] composite slot index %d -> live index %s (%s)' % (ci, pos, where, 'OK' if where == pos else 'MOVED/ABSENT'))
            if where is None:
                print('     !! sub-creative no longer in the composite: Skip (changed since plan)')
                continue
        o = objs.get(sub)
        if o is None:
            print('  [%d] %s NOT READ' % (ci, sub))
            continue
        assert o['ad_account_id'] == u['account_id'], 'account mismatch (sub)'
        cur = (o.get('web_view_properties') or {}).get('url')
        cls, why = classify(cur, c)
        ex = excluded(u, c)
        if ex:
            cls, why = 'EXCLUDED', 'platform-refused list'
        print('  [%d] %s type=%s review=%s updated=%s read seq=%s req=%s -> %s (%s)' % (
            ci, sub, o.get('type'), o.get('review_status'), o.get('updated_at'), src[sub][0], src[sub][1], cls, why))
        if cls != 'WRITE' or cur != c['new']:
            print('     cur ', cur)
            print('     new ', c['new'])
        for k, v in flat(o).items():
            sc = special_chars(v)
            if sc:
                print('     STR %s %r %s' % (k, v, sc))
        extra = set(o) & AUDIT
        if extra:
            print('     NOTE audit fields in read: %s' % sorted(extra))
        if cls == 'WRITE':
            if o.get('type') != 'WEB_VIEW':
                print('     !! not a WEB_VIEW creative: no payload built')
                continue
            p = json.loads(json.dumps(o))
            p['web_view_properties']['url'] = c['new']
            payload.append(p)
    pf = W + 'u%02d_payload.json' % ui
    if payload:
        json.dump({'creatives': payload}, open(pf, 'w', encoding='utf-8'), ensure_ascii=False)
        print('PAYLOAD', pf, 'n=%d' % len(payload))
        print(json.dumps({'creatives': payload}, ensure_ascii=True))
    else:
        if os.path.exists(pf):
            os.remove(pf)
        print('NO WRITE NEEDED')


def cmd_dry(ui, dseq):
    u = units()[ui]
    B = by_seq()
    d = B[dseq]
    pf = W + 'u%02d_payload.json' % ui
    want = json.load(open(pf, encoding='utf-8'))
    probs = []
    i = d['input']
    if i.get('action') != UPDATE_ACTION:
        probs.append('action %r' % i.get('action'))
    if i.get('dry_run') is not True:
        probs.append('dry_run is %r' % i.get('dry_run'))
    if account_of(d) != u['account_id']:
        probs.append('account %r' % account_of(d))
    extra_keys = set(i) - {'action', 'ad_account_id', 'dry_run', 'payload'}
    if extra_keys:
        probs.append('extra input keys %s' % sorted(extra_keys))
    sent = payload_of(d)
    if sent != want:
        probs.append('SENT PAYLOAD != payload file')
        for a, b in zip(sent.get('creatives', []), want['creatives']):
            fa, fb = flat(a), flat(b)
            for k in sorted(set(fa) | set(fb)):
                if fa.get(k, '<absent>') != fb.get(k, '<absent>'):
                    print('   DIFF', a.get('id'), k, repr(fa.get(k, '<absent>')), '!=', repr(fb.get(k, '<absent>')))
    r = d['result']
    try:
        req = r['data']['data']['request']
        body = req['body']
        print('preview', req.get('method'), req.get('url'), 'bodyFormat', req.get('bodyFormat'), 'query', req.get('query'))
        if body != want:
            probs.append('PREVIEW BODY != payload file')
            for a, b in zip(body.get('creatives', []), want['creatives']):
                fa, fb = flat(a), flat(b)
                for k in sorted(set(fa) | set(fb)):
                    if fa.get(k, '<absent>') != fb.get(k, '<absent>'):
                        print('   PDIFF', a.get('id'), k, repr(fa.get(k, '<absent>')), '!=', repr(fb.get(k, '<absent>')))
        for x in body.get('creatives', []):
            print('  body creative', x.get('id'), 'url==new-in-payload:', x['web_view_properties']['url'] in [c['new'] for c in u['changes']])
    except Exception as e:
        probs.append('no preview body (%r)' % e)
        print(d['raw'][:3000])
    print('DRY CHECK', 'OK' if not probs else 'PROBLEMS: %s' % probs)


def cmd_live(ui, dseq, lseq):
    u = units()[ui]
    B = by_seq()
    d, l = B[dseq], B[lseq]
    di, li = dict(d['input']), dict(l['input'])
    gp = []
    if di.pop('dry_run', None) is not True:
        gp.append('dry seq not dry_run=true')
    if li.pop('dry_run', None) is not False:
        gp.append('live seq not dry_run=false')
    if di != li:
        gp.append('LIVE CALL != DRY CALL (apart from dry_run)')
    if li.get('action') != UPDATE_ACTION:
        gp.append('live action %r' % li.get('action'))
    if account_of(l) != u['account_id']:
        gp.append('live account %r' % account_of(l))
    print('live input check:', 'OK' if not gp else gp)
    if l['is_error'] or not isinstance(l['result'], dict):
        print('LIVE RESULT ERROR / not JSON:', l['raw'][:3000])
        return
    print('gateway success=%s requestId=%s' % (l['result'].get('success'), (l['result'].get('meta') or {}).get('requestId')))
    dd = inner(l) or {}
    print('request_status=%s request_id=%s' % (dd.get('request_status'), dd.get('request_id')))
    for x in dd.get('creatives', []):
        cr = x.get('creative') or {}
        url = (cr.get('web_view_properties') or {}).get('url')
        news = [c['new'] for c in u['changes']]
        print('  sub_request_status=%s id=%s review=%s updated=%s url_in_new=%s %s' % (
            x.get('sub_request_status'), cr.get('id'), cr.get('review_status'), cr.get('updated_at'), url in news,
            '' if x.get('sub_request_status') == 'SUCCESS' else json.dumps(x)[:800]))
    if dd.get('request_status') != 'SUCCESS':
        print(l['raw'][:3000])


def cmd_post(ui, lseq, pseqs, pre_seqs=None):
    u = units()[ui]
    B = by_seq()
    led = ledger().get(str(ui), {})
    pre_seqs = pre_seqs or led.get('pre')
    pre, _ = reads(B, pre_seqs)
    post, psrc = reads(B, pseqs)
    sent = {x['id'] for x in payload_of(B[lseq])['creatives']}
    for ci, c in enumerate(u['changes']):
        sub, pos = slot_target(u, c)
        if sub not in sent:
            print('  [%d] %s not in the live payload' % (ci, sub))
            continue
        a, b = pre[sub], post.get(sub)
        if b is None:
            print('  [%d] %s NOT IN READ-BACK' % (ci, sub))
            continue
        after = b['web_view_properties']['url']
        fa, fb = flat(a), flat(b)
        diffs = [k for k in sorted(set(fa) | set(fb)) if fa.get(k, '<absent>') != fb.get(k, '<absent>')]
        other = [k for k in diffs if k not in VOLATILE and k not in AUDIT and k != 'web_view_properties.url']
        print('  [%d] %s after==new:%s | review %s -> %s | volatile changed %s | audit %s | OTHER %s' % (
            ci, sub, after == c['new'], a.get('review_status'), b.get('review_status'),
            [k for k in diffs if k in VOLATILE], [k for k in diffs if k in AUDIT], other))
        for k in other:
            print('     OTHER', k, repr(fa.get(k, '<absent>')), '->', repr(fb.get(k, '<absent>')))
        if after != c['new']:
            print('     after', after)
            print('     new  ', c['new'])
    if u['unit'] in post and u['unit'] not in sent:
        a, b = pre[u['unit']], post[u['unit']]
        fa, fb = flat(a), flat(b)
        diffs = [k for k in sorted(set(fa) | set(fb)) if fa.get(k, '<absent>') != fb.get(k, '<absent>')]
        print('  parent %s (not written) review %s -> %s, changed %s' % (u['unit'], a.get('review_status'),
                                                                         b.get('review_status'), diffs))


def cmd_led(ui, kvs):
    L = ledger()
    e = L.setdefault(str(ui), {})
    for kv in kvs:
        k, v = kv.split('=', 1)
        if k in ('pre', 'post', 'final'):
            e[k] = [int(x) for x in v.split(',') if x]
        elif k in ('dry', 'live', 'dry2', 'live2'):
            e[k] = int(v)
        else:
            e[k] = v
    json.dump(L, open(LEDGER, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ledger', ui, e)


def cmd_results():
    B = by_seq()
    L = ledger()
    res = []
    for ui, u in enumerate(units()):
        e = L.get(str(ui), {})
        if not e.get('pre'):
            for c in u['changes']:
                res.append(_rec(u, c, '', '', e.get('result_all', 'NotAttempted'), e.get('note', 'not attempted')))
            continue
        pre, psrc = reads(B, e['pre'])
        parent = pre[u['unit']]
        is_comp = parent.get('type') == 'COMPOSITE'
        live = B[e['live']] if 'live' in e else None
        post, qsrc = reads(B, e['post']) if e.get('post') else ({}, {})
        final, fsrc = reads(B, e['final']) if e.get('final') else ({}, {})
        sent = {x['id'] for x in payload_of(live)['creatives']} if live else set()
        lreq, lst = req_of(live) if live else (None, None)
        lsub = {}
        if live:
            for x in (inner(live) or {}).get('creatives', []):
                if isinstance(x, dict) and 'creative' in x:
                    lsub[x['creative']['id']] = x.get('sub_request_status')
        for ci, c in enumerate(u['changes']):
            sub, pos = slot_target(u, c)
            o = pre.get(sub)
            before = o['web_view_properties']['url'] if o else ''
            cls, why = classify(before, c)
            where = 'COMPOSITE %s, sub-creative %s (creative_ids[%d], index verified live); ' % (u['unit'], sub, pos) if is_comp else 'WEB_VIEW creative %s; ' % sub
            pre_note = 'pre-read %s (Snapchat req %s): review_status %s, updated_at %s; ' % (
                'GET' if B[psrc[sub][0]]['input']['action'].endswith('creative_id_get') else 'POST get_creatives_by_ids',
                psrc[sub][1], o.get('review_status'), o.get('updated_at')) if o else ''
            if cls == 'AlreadyFixed':
                res.append(_rec(u, c, before, before, 'AlreadyFixed', where + pre_note + why + '; no write made.' + e.get('note_%d' % ci, '')))
                continue
            if cls == 'Skipped':
                res.append(_rec(u, c, before, before, 'Skipped', 'changed since plan: %s (%s%s). No write made.' % (before, where, pre_note.rstrip('; '))))
                continue
            # WRITE
            if sub not in sent:
                r = e.get('result_%d' % ci) or e.get('result_all') or 'NotAttempted'
                res.append(_rec(u, c, before, before, r, where + pre_note + 'live URL == %s; ' % why + e.get('note', 'not written')))
                continue
            b = post.get(sub)
            after = b['web_view_properties']['url'] if b else ''
            fa, fb = flat(o), flat(b) if b else {}
            diffs = [k for k in sorted(set(fa) | set(fb)) if fa.get(k, '<absent>') != fb.get(k, '<absent>')]
            other = [k for k in diffs if k not in VOLATILE and k not in AUDIT and k != 'web_view_properties.url']
            ok = b is not None and after == c['new'] and lst == 'SUCCESS' and lsub.get(sub) == 'SUCCESS'
            n = len(sent)
            d = (where + pre_note + 'live URL == %s; ' % why +
                 'PUT /v1/adaccounts/%s/creatives with the full creative object as read, only web_view_properties.url changed%s '
                 '(dry_run preview checked byte-exact against the read: body identical except url); '
                 'live request_status %s req %s, sub_request_status %s; ' % (
                     u['account_id'], ' (one PUT for the %d sub-creatives of this unit)' % n if n > 1 else '',
                     lst, lreq, lsub.get(sub)))
            if b is not None:
                d += 'read-back %s (Snapchat req %s) URL %s; %s; review_status after write: %s (was %s)' % (
                    'GET' if B[qsrc[sub][0]]['input']['action'].endswith('creative_id_get') else 'POST get_creatives_by_ids',
                    qsrc[sub][1], 'equals new byte for byte' if after == c['new'] else 'DIFFERS from new',
                    'no other field changed (updated_at/semantic_id regenerated)' if not other else 'OTHER FIELDS CHANGED: %s' % other,
                    b.get('review_status'), o.get('review_status'))
            else:
                d += 'NOT READ BACK'
            f = final.get(sub)
            if f is not None:
                d += '; final re-read (Snapchat req %s): URL %s, review_status %s, updated_at %s' % (
                    fsrc[sub][1], 'equals new' if f['web_view_properties']['url'] == c['new'] else 'DIFFERS: ' + f['web_view_properties']['url'],
                    f.get('review_status'), f.get('updated_at'))
            if is_comp and e.get('parent_note'):
                d += '; ' + e['parent_note']
            if e.get('note_%d' % ci):
                d += '; ' + e['note_%d' % ci]
            res.append(_rec(u, c, before, after, 'Fixed' if ok else 'Failed', d))
    print(json.dumps(res, ensure_ascii=False, indent=1))
    from collections import Counter
    print(Counter(r['result'] for r in res), len(res), file=sys.stderr)


def _rec(u, c, before, after, result, detail, new_ids=''):
    return {"platform": "snapchat", "account_id": u['account_id'], "unit_type": u['unit_type'], "unit": u['unit'],
            "ad_ids": u['ad_ids'], "ad_names": u['ad_names'], "slot": c['slot'], "before": before,
            "after_expected": c['new'], "after_live": after, "result": result, "new_entity_ids": new_ids, "detail": detail}


if __name__ == '__main__':
    cmd, a = sys.argv[1], sys.argv[2:]
    if cmd == 'calls':
        cmd_calls(int(a[0]) if a else 1)
    elif cmd == 'pre':
        cmd_pre(int(a[0]), [int(x) for x in a[1:]])
    elif cmd == 'dry':
        cmd_dry(int(a[0]), int(a[1]))
    elif cmd == 'live':
        cmd_live(int(a[0]), int(a[1]), int(a[2]))
    elif cmd == 'post':
        cmd_post(int(a[0]), int(a[1]), [int(x) for x in a[2:]])
    elif cmd == 'led':
        cmd_led(int(a[0]), a[1:])
    elif cmd == 'results':
        cmd_results()
    else:
        raise SystemExit('unknown command')
