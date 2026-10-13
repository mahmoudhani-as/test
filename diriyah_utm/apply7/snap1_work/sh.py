#!/usr/bin/env python3
"""Helper for apply7 Snapchat batch 1 (in_snapchat_1.json).

  sh.py show   <u>                       -> print unit u (index) with its changes
  sh.py state  <u> <objs.json>           -> objs.json = one creative dict or a list of them, exactly as read.
                                            Classifies every change of unit u whose (sub-)creative is in the file,
                                            writes <objs>.payload.json = {"creatives":[...]} for NOW/ALT ones and prints it
                                            (non-letter non-ASCII chars as \\uXXXX escapes).
  sh.py diff   <before.json> <after.json> -> per creative: every differing field (url / volatile / OTHER)
  sh.py record <u> <c> <before.json> <after.json> <result> <detail> [new_entity_ids]
"""
import json, sys, os, copy, unicodedata
from urllib.parse import urlsplit, parse_qsl

BASE = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
INP = BASE + '/apply7/in_snapchat_1.json'
OUT = BASE + '/apply7/out_snapchat_1.jsonl'
EXCL = BASE + '/work/excl_platform_refused_v2.json'
VOLATILE = {'updated_at', 'review_status', 'review_status_details', 'semantic_id', 'packaging_status'}


def units():
    return json.load(open(INP))


def sub_id(u, ch):
    s = ch['slot']
    if '(' in s:
        return s.split('(')[1].split(')')[0]
    return u['unit']


def same_url(a, b):
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
    if cur in ch.get('alt_now', []):
        return 'ALT'
    return 'OTHER'


def safe_dumps(o):
    s = json.dumps(o, ensure_ascii=False)
    out = []
    for c in s:
        o_ = ord(c)
        if o_ > 126 and unicodedata.category(c) not in ('Lo', 'Ll', 'Lu'):
            if o_ > 0xFFFF:
                v = o_ - 0x10000
                out.append('\\u%04x\\u%04x' % (0xD800 + (v >> 10), 0xDC00 + (v & 0x3FF)))
            else:
                out.append('\\u%04x' % o_)
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
        dbl = '  ' in obj
        edge = obj != obj.strip()
        if odd or dbl or edge or any(ord(c) > 126 for c in obj):
            res.append('%s len=%d odd=%s double_space=%s edge_space=%s' % (path, len(obj), odd, dbl, edge))
    return res


def load_objs(f):
    o = json.load(open(f))
    if isinstance(o, dict) and 'creatives' in o:
        o = o['creatives']
    if isinstance(o, dict):
        o = [o]
    res = []
    for x in o:
        if 'creative' in x and 'id' not in x:
            x = x['creative']
        res.append(x)
    return {x['id']: x for x in res}


def excluded(u, ch):
    for e in json.load(open(EXCL)):
        if e.get('platform') == 'snapchat' and (e.get('ad_id') in u['ad_ids'] or e.get('ad_id') in (u['unit'], sub_id(u, ch))) and e.get('slot') == ch['slot']:
            return True
    return False


def cmd_show(ui):
    u = units()[ui]
    print(u['unit'], u['account_id'], u['ad_ids'], u['ad_names'], u.get('status_11oct'))
    for ci, ch in enumerate(u['changes']):
        print(' [%d] sub=%s' % (ci, sub_id(u, ch)))
        print('     now', ch['now'])
        for a in ch.get('alt_now', []):
            print('     alt', a)
        print('     new', ch['new'])


def cmd_state(ui, f):
    u = units()[ui]
    objs = load_objs(f)
    payload = []
    for ci, ch in enumerate(u['changes']):
        sid = sub_id(u, ch)
        if sid not in objs:
            continue
        o = objs[sid]
        assert o['ad_account_id'] == u['account_id'], ('account mismatch', sid)
        cur = o['web_view_properties']['url']
        st = classify(cur, ch)
        if excluded(u, ch):
            st = 'EXCLUDED'
        print('[%d] %s type=%s review=%s updated=%s state=%s' % (ci, sid, o.get('type'), o.get('review_status'), o.get('updated_at'), st))
        if st == 'OTHER':
            print('     cur', cur)
        for line in str_report(o):
            print('     STR', line)
        if st in ('NOW', 'ALT'):
            p = copy.deepcopy(o)
            p['web_view_properties']['url'] = ch['new']
            payload.append(p)
    if payload:
        pf = f.replace('.json', '') + '.payload.json'
        json.dump({'creatives': payload}, open(pf, 'w'), ensure_ascii=False)
        print('payload_file', pf, 'n=%d' % len(payload))
        print(safe_dumps({'creatives': payload}))


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


def cmd_diff(bf, af):
    B, A = load_objs(bf), load_objs(af)
    for cid in B:
        if cid not in A:
            print(cid, 'MISSING in after')
            continue
        fb, fa = flat(B[cid]), flat(A[cid])
        other = []
        for k in sorted(set(fb) | set(fa)):
            vb, va = fb.get(k, '<missing>'), fa.get(k, '<missing>')
            if vb != va:
                tag = 'URL' if k == 'web_view_properties.url' else ('VOLATILE' if k in VOLATILE else 'OTHER')
                if tag == 'OTHER':
                    other.append(k)
                print('  %s %s %s: %r -> %r' % (cid[:8], tag, k, str(vb)[:200], str(va)[:200]))
        print('%s OTHER_FIELD_CHANGES=%d %s' % (cid, len(other), other))


def cmd_record(ui, ci, bf, af, result, detail, new_ids=''):
    u = units()[ui]
    ch = u['changes'][ci]
    sid = sub_id(u, ch)
    B, A = load_objs(bf), load_objs(af)
    before = B[sid]['web_view_properties']['url']
    after = A[sid]['web_view_properties']['url']
    if result == 'Fixed':
        assert after == ch['new'], 'read-back != new: cannot record Fixed'
        assert before == ch['now'] or before in ch.get('alt_now', []), 'before not now/alt'
    if result == 'AlreadyFixed':
        assert same_url(before, ch['new']), 'before != new: cannot record AlreadyFixed'
    if result == 'Skipped':
        assert classify(before, ch) == 'OTHER', 'before is now/alt/new: not a Skip'
    if os.path.exists(OUT):
        for line in open(OUT):
            line = line.strip()
            if line:
                r = json.loads(line)
                if r['unit'] == u['unit'] and r['slot'] == ch['slot']:
                    raise SystemExit('duplicate record for %s %s' % (u['unit'], ch['slot']))
    rec = {"platform": "snapchat", "account_id": u['account_id'], "unit_type": u['unit_type'], "unit": u['unit'],
           "ad_ids": u['ad_ids'], "ad_names": u['ad_names'], "slot": ch['slot'], "before": before,
           "after_expected": ch['new'], "after_live": after, "result": result, "new_entity_ids": new_ids,
           "detail": detail}
    with open(OUT, 'a') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    print('recorded u%d c%d %s %s after==new:%s' % (ui, ci, sid[:8], result, after == ch['new']))


def cmd_mk(spec_f, out_f):
    """spec = {"order": [keys], "common": {...}, "items": [{per-creative keys}]} -> list of objects in key order."""
    spec = json.load(open(spec_f))
    order, common, items = spec['order'], spec['common'], spec['items']
    res = []
    for it in items:
        both = set(it) & set(common)
        assert not both, ('key in both item and common', both)
        missing = [k for k in order if k not in it and k not in common]
        assert not missing, ('missing keys', missing)
        extra = [k for k in list(it) + list(common) if k not in order]
        assert not extra, ('keys not in order', extra)
        res.append({k: copy.deepcopy(it[k] if k in it else common[k]) for k in order})
    json.dump(res, open(out_f, 'w'), ensure_ascii=False)
    print('wrote', out_f, len(res), 'objects')


if __name__ == '__main__':
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == 'mk':
        cmd_mk(args[0], args[1])
    elif cmd == 'show':
        cmd_show(int(args[0]))
    elif cmd == 'state':
        cmd_state(int(args[0]), args[1])
    elif cmd == 'diff':
        cmd_diff(args[0], args[1])
    elif cmd == 'record':
        cmd_record(int(args[0]), int(args[1]), args[2], args[3], args[4], args[5], *(args[6:7]))
    else:
        raise SystemExit('unknown command')
