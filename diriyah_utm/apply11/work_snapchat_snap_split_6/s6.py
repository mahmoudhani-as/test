#!/usr/bin/env python3
"""Helper for apply11 Snapchat snap_split batch 6 (in_snapchat_snap_split_6.json). Run with python3 -I.

  s6.py xt <label> <request_id>              save my snapchat_native_action tool call (input + result) whose result
                                             contains request_id to raw/<label>.json (exact bytes from my transcript)
  s6.py ads <label>                          print every ad object in raw/<label>.json
  s6.py crs <label>                          print every creative object in raw/<label>.json (+ odd-char report)
  s6.py plan <u> <ads_label> <cr_label> [<cr_label2> ...]
                                             classify unit u's changes against the live reads; build the create
                                             payload payload/u<u>_subs.json (COMPOSITE: copies of the listed
                                             sub-creatives) or payload/u<u>_web.json (WEB_VIEW copy), url = new
  s6.py cmpdry <payload_file> <label>        compare dry-run preview body in raw/<label>.json with the payload file
  s6.py cmpcall <payload_file> <label>       compare the payload I actually sent (tool input) with the payload file
  s6.py created <payload_file> <label>       list created creatives (live create response) and compare with payload
  s6.py comp <u> <created_label>             build payload/u<u>_comp.json: new COMPOSITE from the live composite,
                                             listed sub ids replaced by the copies created in <created_label>
  s6.py adpay <u> <ads_label> <ad_id> <new_creative_id>
                                             build payload/u<u>_ad_<ad8>.json = {"ads":[ad as read, creative_id=new]}
  s6.py verify <u> <ads_after_label> <crs_after_label> [...]
                                             verify ads + new creatives vs plan; prints per-change verdicts
"""
import json, sys, os, copy, unicodedata
from urllib.parse import urlsplit, parse_qsl

BASE = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
INP = BASE + '/apply11/in_snapchat_snap_split_6.json'
W = BASE + '/apply11/work_snapchat_snap_split_6'
EXCL = BASE + '/work/excl_platform_refused_v2.json'
T = '/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/wf_875fbfdc-036/agent-ae0590f2ef2e190ec.jsonl'
NOCOPY = ['id', 'updated_at', 'created_at', 'packaging_status', 'review_status', 'review_status_details', 'semantic_id']
AD_VOLATILE = {'updated_at', 'review_status', 'review_status_reasons', 'delivery_status', 'creative_id'}


def units():
    return json.load(open(INP))


def same_url(a, b):
    if a == b:
        return True
    pa, pb = urlsplit(a), urlsplit(b)
    if (pa.scheme, pa.netloc, pa.path, pa.fragment) != (pb.scheme, pb.netloc, pb.path, pb.fragment):
        return False
    return sorted(parse_qsl(pa.query, keep_blank_values=True)) == sorted(parse_qsl(pb.query, keep_blank_values=True))


def classify(cur, ch):
    if cur is not None and same_url(cur, ch['new']):
        return 'NEW'
    if cur == ch['now']:
        return 'NOW'
    if cur in ch.get('alt_now', []):
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


def cmd_xt(label, rid):
    uses, hits = {}, []
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
                txt = result_text(p.get('content'))
                if rid in txt:
                    hits.append((p['tool_use_id'], uses[p['tool_use_id']], txt))
    if len(hits) != 1:
        raise SystemExit('expected exactly 1 tool result with %s, found %d' % (rid, len(hits)))
    tid, inp, txt = hits[0]
    res = json.loads(txt)
    os.makedirs(W + '/raw', exist_ok=True)
    json.dump({'tool_use_id': tid, 'input': inp, 'result': res}, open(W + '/raw/%s.json' % label, 'w'), ensure_ascii=False, indent=1)
    print('saved raw/%s.json tool_use_id=%s action=%s dry_run=%s' % (label, tid, inp.get('action'), inp.get('dry_run')))


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


def find_cr(labels, cid):
    for lb in labels:
        f = [c for c in creatives(lb) if c.get('id') == cid]
        if f:
            return f[0]
    raise SystemExit('creative %s not found in %s' % (cid, labels))


def cmd_ads(label):
    for a in ads(label):
        print(json.dumps({k: a.get(k) for k in ('id', 'name', 'ad_squad_id', 'creative_id', 'status', 'type', 'review_status', 'updated_at')}, ensure_ascii=False))
        print('   keys:', sorted(a.keys()))
        for line in str_report(a):
            print('   STR', line)


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


def parse_slot(slot):
    # creative.composite_properties.creative_ids[0] (666b...).web_view_properties.url
    if slot == 'creative.web_view_properties.url':
        return None, None
    pre = 'creative.composite_properties.creative_ids['
    assert slot.startswith(pre), slot
    i = int(slot[len(pre):slot.index(']')])
    sid = slot[slot.index('(') + 1:slot.index(')')]
    assert slot.endswith(').web_view_properties.url'), slot
    return i, sid


def copy_of(c, url=None):
    p = {k: copy.deepcopy(v) for k, v in c.items() if k not in NOCOPY}
    if url is not None:
        p['web_view_properties']['url'] = url
    return p


def cmd_plan(ui, ads_label, cr_labels):
    u = units()[ui]
    excl = json.load(open(EXCL))
    print('unit u%d %s recipe=%s creative=%s ads=%s' % (ui, u['unit'], u['recipe'], u['creative_id'], u['ad_ids']))
    al = ads(ads_label)
    live_cids = set()
    for aid in u['ad_ids']:
        a = get_one(al, aid, 'ad')
        live_cids.add(a['creative_id'])
        print('  ad %s status=%s type=%s creative_id=%s (plan %s) review=%s updated=%s' % (
            aid, a['status'], a['type'], a['creative_id'], u['creative_id'], a.get('review_status'), a.get('updated_at')))
    if live_cids != {u['creative_id']}:
        print('  !! ads now use creative(s) %s, not the plan creative' % live_cids)
    live_cid = sorted(live_cids)[0]
    top = find_cr(cr_labels, live_cid)
    plan = {'u': ui, 'unit': u['unit'], 'live_creative_id': live_cid, 'type': top['type'], 'changes': []}
    print('  live creative %s type=%s review=%s updated=%s' % (live_cid, top['type'], top.get('review_status'), top.get('updated_at')))
    for line in str_report(top):
        print('   STR top', line)
    to_copy = []
    for ch in u['changes']:
        i, sid = parse_slot(ch['slot'])
        ex = [e for e in excl if e.get('platform') == 'snapchat' and e.get('slot') == ch['slot']
              and (e.get('ad_id') in u['ad_ids'] or e.get('ad_id') == u['unit'])]
        if i is None:
            assert top['type'] == 'WEB_VIEW', top['type']
            cur = top['web_view_properties']['url']
            src = top
        else:
            assert top['type'] == 'COMPOSITE', top['type']
            ids = top['composite_properties']['creative_ids']
            live_sid = ids[i] if i < len(ids) else None
            if live_sid != sid:
                print('  !! slot %d now holds %s (plan %s)' % (i, live_sid, sid))
            src = find_cr(cr_labels, live_sid)
            cur = src['web_view_properties']['url']
        st = classify(cur, ch)
        if ex:
            st = 'EXCLUDED'
        plan['changes'].append({'slot': ch['slot'], 'index': i, 'src_id': src['id'], 'cur': cur, 'state': st, 'new': ch['new']})
        print('  change idx=%s src=%s state=%s src_review=%s src_updated=%s' % (i, src['id'], st, src.get('review_status'), src.get('updated_at')))
        print('     cur', cur)
        for line in str_report(src):
            print('     STR', line)
        if st in ('NOW', 'ALT'):
            to_copy.append(copy_of(src, ch['new']))
    json.dump(plan, open(W + '/plan_u%d.json' % ui, 'w'), ensure_ascii=False, indent=1)
    if to_copy:
        fn = 'payload/u%d_%s.json' % (ui, 'subs' if top['type'] == 'COMPOSITE' else 'web')
        os.makedirs(W + '/payload', exist_ok=True)
        json.dump({'creatives': to_copy}, open(W + '/' + fn, 'w'), ensure_ascii=False)
        print('payload_file', fn)
        print(safe_dumps({'creatives': to_copy}))
    else:
        print('nothing to write')


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


def cmd_cmpdry(pf, label):
    pay = json.load(open(W + '/' + pf))
    r = load_raw(label)
    body = find_body(r['result'])
    print('dry_run=%s method=%s url=%s gateway_request_id=%s' % (
        r['input'].get('dry_run'), find_key(r['result'], 'method'), find_key(r['result'], 'url'), find_key(r['result'], 'gateway_request_id')))
    if body is None:
        print('no body found in the preview:')
        print(json.dumps(r['result'], ensure_ascii=True)[:4000])
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
    print('sent payload == built payload: %s ; differences: %d ; action=%s dry_run=%s ad_account_id=%s path_params=%s' % (
        sent == pay, len(d), r['input'].get('action'), r['input'].get('dry_run'), r['input'].get('ad_account_id'), r['input'].get('path_params')))
    for k, x, y in d:
        print('  DIFF', k, repr(x)[:200], '->', repr(y)[:200])


def cmd_created(pf, label):
    pay = json.load(open(W + '/' + pf))
    r = load_raw(label)
    print('request_status=%s request_id=%s' % (find_key(r['result'], 'request_status'), find_key(r['result'], 'request_id')))
    subs = sub_statuses(r['result'])
    print('sub_requests:', [(s.get('sub_request_status'), s.get('sub_request_error_reason')) for s in subs])
    crs = walk_key(r['result'], 'creative')
    want = pay['creatives']
    print('created %d (payload %d)' % (len(crs), len(want)))
    ids = []
    for i, c in enumerate(crs):
        ids.append(c.get('id'))
        exp = want[i] if i < len(want) else {}
        d = [x for x in cmp_objs(exp, {k: v for k, v in c.items() if k not in NOCOPY})]
        print('  [%d] id=%s review=%s packaging=%s diffs_vs_payload=%d' % (i, c.get('id'), c.get('review_status'), c.get('packaging_status'), len(d)))
        for k, x, y in d:
            print('     DIFF', k, repr(x)[:200], '->', repr(y)[:200])
        if 'web_view_properties' in c:
            print('     url', c['web_view_properties'].get('url'))
    print('NEW_IDS', json.dumps(ids))


def cmd_comp(ui, created_label):
    plan = json.load(open(W + '/plan_u%d.json' % ui))
    u = units()[ui]
    # the live composite was read in the plan step; find it in the raw files
    top = None
    for fn in sorted(os.listdir(W + '/raw')):
        for c in walk_key(json.load(open(W + '/raw/' + fn))['result'], 'creative'):
            if c.get('id') == plan['live_creative_id'] and c.get('updated_at'):
                top = c
                break
        if top:
            break
    assert top and top['type'] == 'COMPOSITE'
    crs = walk_key(load_raw(created_label)['result'], 'creative')
    writes = [ch for ch in plan['changes'] if ch['state'] in ('NOW', 'ALT')]
    assert len(crs) == len(writes), (len(crs), len(writes))
    ids = list(top['composite_properties']['creative_ids'])
    mapping = {}
    for ch, c in zip(writes, crs):
        assert c['web_view_properties']['url'] == ch['new']
        assert ids[ch['index']] == ch['src_id']
        ids[ch['index']] = c['id']
        mapping[ch['src_id']] = c['id']
    p = copy_of(top)
    p['composite_properties']['creative_ids'] = ids
    json.dump({'creatives': [p]}, open(W + '/payload/u%d_comp.json' % ui, 'w'), ensure_ascii=False)
    plan['sub_map'] = mapping
    plan['new_comp_ids'] = ids
    plan['old_comp_ids'] = top['composite_properties']['creative_ids']
    json.dump(plan, open(W + '/plan_u%d.json' % ui, 'w'), ensure_ascii=False, indent=1)
    print('old ids', top['composite_properties']['creative_ids'])
    print('new ids', ids)
    print('payload_file payload/u%d_comp.json' % ui)
    print(safe_dumps({'creatives': [p]}))


def cmd_adpay(ui, ads_label, aid, ncid):
    a = get_one(ads(ads_label), aid, 'ad')
    p = copy.deepcopy(a)
    p['creative_id'] = ncid
    fn = 'payload/u%d_ad_%s.json' % (ui, aid[:8])
    json.dump({'ads': [p]}, open(W + '/' + fn, 'w'), ensure_ascii=False)
    print('ad_squad_id', a['ad_squad_id'])
    print('payload_file', fn)
    print(safe_dumps({'ads': [p]}))


def cmd_verify(ui, ads_before, ads_after, cr_labels):
    u = units()[ui]
    plan = json.load(open(W + '/plan_u%d.json' % ui))
    ab, aa = ads(ads_before), ads(ads_after)
    ok = True
    newtop = None
    for aid in u['ad_ids']:
        b, a = get_one(ab, aid, 'ad'), get_one(aa, aid, 'ad')
        d = cmp_objs(b, a)
        other = [k for k, x, y in d if k.split('[')[0] not in AD_VOLATILE]
        print('ad %s creative %s -> %s status %s -> %s review %s -> %s other_changes=%s' % (
            aid, b['creative_id'], a['creative_id'], b['status'], a['status'], b.get('review_status'), a.get('review_status'), other))
        for k, x, y in d:
            print('   ', k, repr(x)[:120], '->', repr(y)[:120])
        if other or b['status'] != a['status']:
            ok = False
        if newtop is None:
            newtop = a['creative_id']
        elif newtop != a['creative_id']:
            ok = False
    top = find_cr(cr_labels, newtop)
    oldtop = None
    for fn in sorted(os.listdir(W + '/raw')):
        for c in walk_key(json.load(open(W + '/raw/' + fn))['result'], 'creative'):
            if c.get('id') == plan['live_creative_id'] and c.get('updated_at'):
                oldtop = c
                break
        if oldtop:
            break
    print('new top creative %s type=%s review=%s packaging=%s' % (newtop, top['type'], top.get('review_status'), top.get('packaging_status')))
    dtop = [x for x in cmp_objs(copy_of(oldtop), copy_of(top))]
    for k, x, y in dtop:
        print('   top DIFF', k, repr(x)[:120], '->', repr(y)[:120])
    results = []
    if top['type'] == 'COMPOSITE':
        ids = top['composite_properties']['creative_ids']
        exp_ids = plan.get('new_comp_ids')
        print('composite ids == planned new ids: %s ; unlisted unchanged: %s' % (
            ids == exp_ids, all(ids[j] == plan['old_comp_ids'][j] for j in range(len(ids)) if plan['old_comp_ids'][j] not in plan['sub_map'])))
        if ids != exp_ids:
            ok = False
        other_top = [k for k, x, y in dtop if not k.startswith('composite_properties.creative_ids')]
        if other_top:
            ok = False
            print('   !! top other diffs', other_top)
        for ch in plan['changes']:
            sid = ids[ch['index']]
            sc = find_cr(cr_labels, sid)
            src = find_cr(cr_labels + [l[:-5] for l in os.listdir(W + '/raw') if l.endswith('.json')], ch['src_id'])
            dd = [x for x in cmp_objs(copy_of(src), copy_of(sc)) if x[0] != 'web_view_properties.url']
            got = sc['web_view_properties']['url']
            res = 'Fixed' if (got == ch['new'] and not dd and ok) else 'CHECK'
            print('slot[%d] %s -> %s url==new: %s other_diffs=%s review=%s => %s' % (ch['index'], ch['src_id'], sid, got == ch['new'], dd, sc.get('review_status'), res))
            print('   after_live', got)
            results.append({'slot': ch['slot'], 'after_live': got, 'new_sub': sid, 'review': sc.get('review_status'), 'res': res})
    else:
        other_top = [k for k, x, y in dtop if k != 'web_view_properties.url']
        got = top['web_view_properties']['url']
        ch = plan['changes'][0]
        res = 'Fixed' if (got == ch['new'] and not other_top and ok) else 'CHECK'
        print('url==new: %s other_diffs=%s review=%s => %s' % (got == ch['new'], other_top, top.get('review_status'), res))
        print('   after_live', got)
        results.append({'slot': ch['slot'], 'after_live': got, 'review': top.get('review_status'), 'res': res})
    plan['verify'] = {'ok': ok, 'new_top': newtop, 'results': results}
    json.dump(plan, open(W + '/plan_u%d.json' % ui, 'w'), ensure_ascii=False, indent=1)
    print('UNIT_OK', ok)


if __name__ == '__main__':
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == 'xt':
        cmd_xt(args[0], args[1])
    elif cmd == 'ads':
        cmd_ads(args[0])
    elif cmd == 'crs':
        cmd_crs(args[0])
    elif cmd == 'plan':
        cmd_plan(int(args[0]), args[1], args[2:])
    elif cmd == 'cmpdry':
        cmd_cmpdry(args[0], args[1])
    elif cmd == 'cmpcall':
        cmd_cmpcall(args[0], args[1])
    elif cmd == 'created':
        cmd_created(args[0], args[1])
    elif cmd == 'comp':
        cmd_comp(int(args[0]), args[1])
    elif cmd == 'adpay':
        cmd_adpay(int(args[0]), args[1], args[2], args[3])
    elif cmd == 'verify':
        cmd_verify(int(args[0]), args[1], args[2], args[3:])
    else:
        raise SystemExit('unknown command')
