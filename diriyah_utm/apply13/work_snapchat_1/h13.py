#!/usr/bin/env python3
"""apply13 Snapchat snap_composite_swap helper (in_snapchat_1.json). Run with python3 -I. No API calls.

  h13.py xt <label> <request_id>          save my snapchat_native_action call (input + parsed result) whose
                                          result text contains request_id -> raw/<label>.json (exact transcript bytes)
  h13.py xtfile <label> <path>            same, for a result the tool saved to a file
  h13.py ads <label>                      print ads in raw/<label>.json
  h13.py crs <label>                      print creatives in raw/<label>.json (+ odd-char report)
  h13.py users <ads_label> <creative_id>  ads that use creative_id
  h13.py compusers <crs_label> <id> ...   composites (in crs_label) whose creative_ids contain any id
  h13.py plan <u> <ad_label> <comp_label> <subs_label>
                                          check ad/composite/slots, classify each change, write plan_u<u>.json
  h13.py reuse <u> <crs_label> <users_label> <cand_id> ...
                                          check apply11 unattached candidates against the plan
  h13.py copies <u>                       build payload/u<u>_copies.json (WEB_VIEW copies, url = new)
  h13.py cmpdry <payload_file> <label>    compare dry-run preview body with payload file
  h13.py cmpcall <payload_file> <label>   compare payload actually sent (tool input) with payload file
  h13.py created <u> <label>              check created copies vs payload, record copy ids in plan
  h13.py comp <u>                         build payload/u<u>_comp.json: full composite as read, only creative_ids changed
  h13.py verify <u> <ad_label> <comp_label> <subs_label>
"""
import json, sys, os, copy, unicodedata
from urllib.parse import urlsplit, parse_qsl

BASE = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
INP = BASE + '/apply13/in_snapchat_1.json'
W = BASE + '/apply13/work_snapchat_1'
EXCL = BASE + '/work/excl_platform_refused_v2.json'
T = '/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/wf_8ebc107e-47d/agent-a3e0e35ac06d8fd3f.jsonl'
# never copied into a new creative: id, timestamps, review / semantic / processing / audit fields
NOCOPY = {'id', 'updated_at', 'created_at', 'packaging_status', 'review_status', 'review_status_details',
          'semantic_id', 'created_by_app_id', 'created_by_user', 'last_updated_by_app_id', 'last_updated_by_user'}


def units():
    return json.load(open(INP))


def same_url(a, b):
    if a is None or b is None:
        return False
    if a == b:
        return True
    pa, pb = urlsplit(a), urlsplit(b)
    if (pa.scheme, pa.netloc, pa.path, pa.fragment) != (pb.scheme, pb.netloc, pb.path, pb.fragment):
        return False
    return sorted(parse_qsl(pa.query, keep_blank_values=True)) == sorted(parse_qsl(pb.query, keep_blank_values=True))


def classify(cur, ch):
    if same_url(cur, ch['new']):
        return 'NEW'
    if cur == ch['now']:
        return 'NOW'
    if cur in (ch.get('alt_now') or []):
        return 'ALT'
    return 'OTHER'


def safe_dumps(o):
    s = json.dumps(o, ensure_ascii=False)
    out = []
    for c in s:
        n = ord(c)
        if n > 126 and unicodedata.category(c) not in ('Lo', 'Ll', 'Lu'):
            if n > 0xFFFF:
                v = n - 0x10000
                out.append('\\u%04x\\u%04x' % (0xD800 + (v >> 10), 0xDC00 + (v & 0x3FF)))
            else:
                out.append('\\u%04x' % n)
        else:
            out.append(c)
    return ''.join(out)


def str_report(obj, path=''):
    res = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            res += str_report(v, path + '.' + k if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            res += str_report(v, '%s[%d]' % (path, i))
    elif isinstance(obj, str):
        odd = [(i, 'U+%04X' % ord(c), unicodedata.name(c, '?')) for i, c in enumerate(obj)
               if (ord(c) > 126 and unicodedata.category(c) not in ('Lo', 'Ll', 'Lu')) or c in '\t\r\n']
        if odd or '  ' in obj or obj != obj.strip():
            res.append('%s len=%d odd=%s double_space=%s edge_space=%s' % (path, len(obj), odd, '  ' in obj, obj != obj.strip()))
    return res


def result_text(content):
    if isinstance(content, str):
        return content
    parts = []
    for p in content or []:
        if isinstance(p, dict) and p.get('type') == 'text':
            parts.append(p.get('text', ''))
    return ''.join(parts)


def tool_calls():
    uses, out = {}, []
    for line in open(T):
        try:
            o = json.loads(line)
        except Exception:
            continue
        c = (o.get('message') or {}).get('content')
        if not isinstance(c, list):
            continue
        for p in c:
            if not isinstance(p, dict):
                continue
            if p.get('type') == 'tool_use' and 'snapchat_native_action' in (p.get('name') or ''):
                uses[p['id']] = p.get('input')
            elif p.get('type') == 'tool_result' and p.get('tool_use_id') in uses:
                out.append((p['tool_use_id'], uses[p['tool_use_id']], result_text(p.get('content'))))
    return out


def save_raw(label, tid, inp, res):
    json.dump({'tool_use_id': tid, 'input': inp, 'result': res}, open(W + '/raw/%s.json' % label, 'w'), ensure_ascii=False, indent=1)
    print('saved raw/%s.json tool_use_id=%s action=%s dry_run=%s' % (label, tid, inp.get('action'), inp.get('dry_run')))


def cmd_xt(label, rid):
    hits = [h for h in tool_calls() if rid in h[2]]
    if len(hits) != 1:
        raise SystemExit('expected exactly 1 tool result with %s, found %d' % (rid, len(hits)))
    tid, inp, txt = hits[0]
    save_raw(label, tid, inp, json.loads(txt))


def cmd_xtfile(label, path):
    txt = open(path).read()
    try:
        res = json.loads(txt)
    except Exception:
        # some saved files hold a list of text parts
        res = json.loads(result_text(json.loads(txt)))
    # find the tool call whose result text names this path
    hits = [h for h in tool_calls() if path in h[2]]
    tid, inp = (hits[-1][0], hits[-1][1]) if hits else (None, {})
    save_raw(label, tid, inp, res)


def load_raw(label):
    return json.load(open(W + '/raw/%s.json' % label))


def walk_key(obj, key):
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key and isinstance(v, dict):
                out.append(v)
            else:
                out += walk_key(v, key)
    elif isinstance(obj, list):
        for v in obj:
            out += walk_key(v, key)
    return out


def find_key(obj, key):
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            r = find_key(v, key)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = find_key(v, key)
            if r is not None:
                return r
    return None


def sub_statuses(obj):
    out = []
    if isinstance(obj, dict):
        if 'sub_request_status' in obj:
            out.append(obj)
        for v in obj.values():
            out += sub_statuses(v)
    elif isinstance(obj, list):
        for v in obj:
            out += sub_statuses(v)
    return out


def creatives(label):
    return walk_key(load_raw(label)['result'], 'creative')


def ads(label):
    return walk_key(load_raw(label)['result'], 'ad')


def get_one(objs, oid, what):
    f = [o for o in objs if o.get('id') == oid]
    if len(f) != 1:
        raise SystemExit('expected 1 %s %s, found %d' % (what, oid, len(f)))
    return f[0]


def cmd_ads(label):
    al = ads(label)
    print('request_id=%s count=%d' % (find_key(load_raw(label)['result'], 'request_id'), len(al)))
    for a in al:
        print(json.dumps({k: a.get(k) for k in ('id', 'name', 'ad_squad_id', 'creative_id', 'status', 'type', 'review_status', 'updated_at')}, ensure_ascii=False))


def cmd_crs(label):
    for c in creatives(label):
        info = {k: c.get(k) for k in ('id', 'type', 'name', 'review_status', 'packaging_status', 'updated_at')}
        if 'web_view_properties' in c:
            info['url'] = c['web_view_properties'].get('url')
        if 'composite_properties' in c:
            info['subs'] = c['composite_properties'].get('creative_ids')
        print(json.dumps(info, ensure_ascii=False))
        print('   keys:', sorted(c.keys()))
        for line in str_report(c):
            print('   STR', line)


def cmd_users(ads_label, cid):
    al = ads(ads_label)
    u = [a for a in al if a.get('creative_id') == cid]
    print('ads read: %d ; ads using %s: %s' % (len(al), cid, [(a['id'], a.get('name'), a.get('status')) for a in u]))


def cmd_compusers(crs_label, ids):
    cl = creatives(crs_label)
    comps = [c for c in cl if c.get('type') == 'COMPOSITE' or 'composite_properties' in c]
    print('creatives read: %d ; composites: %d' % (len(cl), len(comps)))
    for i in ids:
        us = [c['id'] for c in comps if i in ((c.get('composite_properties') or {}).get('creative_ids') or [])]
        print('  %s used by composites %s' % (i, us))


def parse_slot(slot):
    pre = 'creative.composite_properties.creative_ids['
    assert slot.startswith(pre), slot
    i = int(slot[len(pre):slot.index(']')])
    sid = slot[slot.index('(') + 1:slot.index(')')]
    assert slot.endswith(').web_view_properties.url'), slot
    return i, sid


def copy_of(c, url):
    p = {k: copy.deepcopy(v) for k, v in c.items() if k not in NOCOPY}
    p['web_view_properties']['url'] = url
    return p


def plan_path(ui):
    return W + '/plan_u%d.json' % ui


def cmd_plan(ui, ad_label, comp_label, subs_label):
    u = units()[ui]
    excl = json.load(open(EXCL))
    print('unit u%d ad=%s creative=%s recipe=%s' % (ui, u['unit'], u['creative_id'], u['recipe']))
    a = get_one(ads(ad_label), u['ad_ids'][0], 'ad')
    print('  ad status=%s type=%s creative_id=%s review=%s updated=%s squad=%s' % (
        a['status'], a['type'], a['creative_id'], a.get('review_status'), a.get('updated_at'), a.get('ad_squad_id')))
    ok_ad = a['creative_id'] == u['creative_id']
    print('  ad.creative_id == unit creative_id: %s' % ok_ad)
    top = get_one(creatives(comp_label), u['creative_id'], 'creative')
    assert top['type'] == 'COMPOSITE', top['type']
    ids = top['composite_properties']['creative_ids']
    print('  composite review=%s updated=%s ids=%s' % (top.get('review_status'), top.get('updated_at'), ids))
    for line in str_report(top):
        print('   STR top', line)
    subs = creatives(subs_label)
    plan = {'u': ui, 'unit': u['unit'], 'ad': {k: a.get(k) for k in ('id', 'creative_id', 'status', 'review_status', 'updated_at', 'ad_squad_id', 'name', 'type')},
            'composite': top, 'old_ids': list(ids), 'changes': []}
    for ch in u['changes']:
        i, sid = parse_slot(ch['slot'])
        ex = [e for e in excl if e.get('platform') == 'snapchat' and e.get('slot') == ch['slot']]
        live_sid = ids[i] if i < len(ids) else None
        src = get_one(subs, live_sid, 'creative') if live_sid else None
        cur = src['web_view_properties']['url'] if src else None
        st = classify(cur, ch)
        if live_sid != sid:
            st = 'NEW' if st == 'NEW' else 'MOVED'
        if ex:
            st = 'EXCLUDED'
        plan['changes'].append({'slot': ch['slot'], 'index': i, 'plan_sub': sid, 'live_sub': live_sid, 'cur': cur, 'state': st,
                                'new': ch['new'], 'src': src})
        print('  [%d] plan_sub=%s live_sub=%s state=%s type=%s review=%s updated=%s' % (
            i, sid, live_sid, st, src and src.get('type'), src and src.get('review_status'), src and src.get('updated_at')))
        print('      cur', cur)
        for line in str_report(src or {}):
            print('      STR', line)
    json.dump(plan, open(plan_path(ui), 'w'), ensure_ascii=False, indent=1)
    print('plan written; states:', [c['state'] for c in plan['changes']], 'ok_ad=%s' % ok_ad)


def cmd_reuse(ui, crs_label, users_label, cands):
    plan = json.load(open(plan_path(ui)))
    cl = creatives(crs_label)
    comps = [c for c in creatives(users_label) if 'composite_properties' in c]
    for cid in cands:
        c = get_one(cl, cid, 'creative')
        url = (c.get('web_view_properties') or {}).get('url')
        used = [x['id'] for x in comps if cid in x['composite_properties'].get('creative_ids', [])]
        print('cand %s type=%s review=%s url=%s' % (cid, c.get('type'), c.get('review_status'), url))
        print('   used by composites: %s' % used)
        for ch in plan['changes']:
            src = ch['src']
            a = {k: v for k, v in src.items() if k not in NOCOPY}
            b = {k: v for k, v in c.items() if k not in NOCOPY}
            a = json.loads(json.dumps(a)); b = json.loads(json.dumps(b))
            a['web_view_properties'].pop('url', None); b.get('web_view_properties', {}).pop('url', None)
            if a == b:
                print('   matches original at index %d (%s) except url; url == new byte for byte: %s' % (ch['index'], src['id'], url == ch['new']))


def cmd_copies(ui):
    plan = json.load(open(plan_path(ui)))
    pay = []
    for ch in plan['changes']:
        if ch['state'] in ('NOW', 'ALT'):
            pay.append(copy_of(ch['src'], ch['new']))
    fn = 'payload/u%d_copies.json' % ui
    json.dump({'creatives': pay}, open(W + '/' + fn, 'w'), ensure_ascii=False)
    print('payload_file', fn, 'count', len(pay))
    print(safe_dumps({'creatives': pay}))


def flat(obj, path=''):
    out = {}
    if isinstance(obj, dict):
        if not obj:
            out[path] = {}
        for k, v in obj.items():
            out.update(flat(v, path + '.' + k if path else k))
    elif isinstance(obj, list):
        if not obj:
            out[path] = []
        for i, v in enumerate(obj):
            out.update(flat(v, '%s[%d]' % (path, i)))
    else:
        out[path] = obj
    return out


def cmp_objs(a, b):
    fa, fb = flat(a), flat(b)
    return [(k, fa.get(k, '<missing>'), fb.get(k, '<missing>')) for k in sorted(set(fa) | set(fb))
            if fa.get(k, '<missing>') != fb.get(k, '<missing>') or type(fa.get(k)) != type(fb.get(k))]


def find_body(obj):
    if isinstance(obj, dict):
        if 'body' in obj and isinstance(obj['body'], dict):
            return obj['body']
        for v in obj.values():
            b = find_body(v)
            if b is not None:
                return b
    elif isinstance(obj, list):
        for v in obj:
            b = find_body(v)
            if b is not None:
                return b
    return None


def cmd_cmpdry(pf, label):
    pay = json.load(open(W + '/' + pf))
    r = load_raw(label)
    body = find_body(r['result'])
    print('dry_run=%s method=%s url=%s' % (r['input'].get('dry_run'), find_key(r['result'], 'method'), find_key(r['result'], 'url')))
    if body is None:
        print('no body in preview:', json.dumps(r['result'], ensure_ascii=True)[:3000])
        return
    d = cmp_objs(pay, body)
    print('preview body == payload: %s ; differences: %d' % (body == pay, len(d)))
    for k, x, y in d:
        print('  DIFF', k, repr(x)[:200], '->', repr(y)[:200])


def cmd_cmpcall(pf, label):
    pay = json.load(open(W + '/' + pf))
    r = load_raw(label)
    sent = r['input'].get('payload')
    if isinstance(sent, str):
        sent = json.loads(sent)
    d = cmp_objs(pay, sent)
    print('sent payload == built payload: %s ; differences: %d ; action=%s dry_run=%s ad_account_id=%s' % (
        sent == pay, len(d), r['input'].get('action'), r['input'].get('dry_run'), r['input'].get('ad_account_id')))
    for k, x, y in d:
        print('  DIFF', k, repr(x)[:200], '->', repr(y)[:200])


def cmd_created(ui, label):
    plan = json.load(open(plan_path(ui)))
    pay = json.load(open(W + '/payload/u%d_copies.json' % ui))['creatives']
    r = load_raw(label)
    print('request_status=%s request_id=%s' % (find_key(r['result'], 'request_status'), find_key(r['result'], 'request_id')))
    subs = sub_statuses(r['result'])
    print('sub_requests:', [(s.get('sub_request_status'), s.get('sub_request_error_reason')) for s in subs])
    crs = walk_key(r['result'], 'creative')
    writes = [ch for ch in plan['changes'] if ch['state'] in ('NOW', 'ALT')]
    print('created %d (payload %d, writes %d)' % (len(crs), len(pay), len(writes)))
    assert len(crs) == len(pay) == len(writes)
    for ch, exp, c in zip(writes, pay, crs):
        d = cmp_objs(exp, {k: v for k, v in c.items() if k not in NOCOPY})
        print('  [%d] src=%s copy=%s review=%s packaging=%s url_ok=%s diffs=%d' % (
            ch['index'], ch['src']['id'], c.get('id'), c.get('review_status'), c.get('packaging_status'),
            c['web_view_properties']['url'] == ch['new'], len(d)))
        for k, x, y in d:
            print('     DIFF', k, repr(x)[:200], '->', repr(y)[:200])
        ch['copy_id'] = c['id']
        ch['copy_create_review'] = c.get('review_status')
    plan['create_request_id'] = find_key(r['result'], 'request_id')
    json.dump(plan, open(plan_path(ui), 'w'), ensure_ascii=False, indent=1)


def cmd_comp(ui):
    plan = json.load(open(plan_path(ui)))
    top = plan['composite']
    ids = list(top['composite_properties']['creative_ids'])
    for ch in plan['changes']:
        if ch['state'] in ('NOW', 'ALT'):
            assert ids[ch['index']] == ch['src']['id']
            ids[ch['index']] = ch['copy_id']
    p = copy.deepcopy(top)
    p['composite_properties']['creative_ids'] = ids
    d = cmp_objs(top, p)
    print('payload vs read differences (expect only composite_properties.creative_ids[i]):')
    for k, x, y in d:
        print('  DIFF', k, x, '->', y)
    plan['new_ids'] = ids
    json.dump(plan, open(plan_path(ui), 'w'), ensure_ascii=False, indent=1)
    fn = 'payload/u%d_comp.json' % ui
    json.dump({'creatives': [p]}, open(W + '/' + fn, 'w'), ensure_ascii=False)
    print('payload_file', fn)
    print(safe_dumps({'creatives': [p]}))


def cmd_verify(ui, ad_label, comp_label, subs_label):
    plan = json.load(open(plan_path(ui)))
    u = units()[ui]
    a = get_one(ads(ad_label), u['ad_ids'][0], 'ad')
    b = plan['ad']
    print('ad creative_id=%s (same: %s) status=%s (same: %s) review=%s (before %s) updated=%s (before %s)' % (
        a['creative_id'], a['creative_id'] == b['creative_id'], a['status'], a['status'] == b['status'],
        a.get('review_status'), b.get('review_status'), a.get('updated_at'), b.get('updated_at')))
    top = get_one(creatives(comp_label), u['creative_id'], 'creative')
    ids = top['composite_properties']['creative_ids']
    print('composite review=%s updated=%s ids==expected: %s' % (top.get('review_status'), top.get('updated_at'), ids == plan.get('new_ids')))
    d = cmp_objs({k: v for k, v in plan['composite'].items() if k not in ('updated_at', 'review_status', 'review_status_details', 'semantic_id', 'packaging_status')},
                 {k: v for k, v in top.items() if k not in ('updated_at', 'review_status', 'review_status_details', 'semantic_id', 'packaging_status',
                                                             'created_by_app_id', 'created_by_user', 'last_updated_by_app_id', 'last_updated_by_user')})
    print('composite diffs vs before (excl. volatile):')
    for k, x, y in d:
        print('  DIFF', k, x, '->', y)
    subs = creatives(subs_label)
    for ch in plan['changes']:
        sid = ids[ch['index']]
        s = get_one(subs, sid, 'creative')
        url = s['web_view_properties']['url']
        print('  [%d] now_at_index=%s review=%s url==new: %s' % (ch['index'], sid, s.get('review_status'), url == ch['new']))
        print('      url', url)


if __name__ == '__main__':
    c = sys.argv[1]
    a = sys.argv[2:]
    if c == 'xt':
        cmd_xt(a[0], a[1])
    elif c == 'xtfile':
        cmd_xtfile(a[0], a[1])
    elif c == 'ads':
        cmd_ads(a[0])
    elif c == 'crs':
        cmd_crs(a[0])
    elif c == 'users':
        cmd_users(a[0], a[1])
    elif c == 'compusers':
        cmd_compusers(a[0], a[1:])
    elif c == 'plan':
        cmd_plan(int(a[0]), a[1], a[2], a[3])
    elif c == 'reuse':
        cmd_reuse(int(a[0]), a[1], a[2], a[3:])
    elif c == 'copies':
        cmd_copies(int(a[0]))
    elif c == 'cmpdry':
        cmd_cmpdry(a[0], a[1])
    elif c == 'cmpcall':
        cmd_cmpcall(a[0], a[1])
    elif c == 'created':
        cmd_created(int(a[0]), a[1])
    elif c == 'comp':
        cmd_comp(int(a[0]))
    elif c == 'verify':
        cmd_verify(int(a[0]), a[1], a[2], a[3])
    else:
        raise SystemExit(__doc__)
