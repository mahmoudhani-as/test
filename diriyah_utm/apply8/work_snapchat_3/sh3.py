#!/usr/bin/env python3
"""Helper for apply8 Snapchat batch 3 (in_snapchat_3.json). Writes no results file.

  sh3.py state <before.json>            classify each change against the read, check exclusions/strings,
                                        write <before>.payload.json ({"creatives":[...]}, only url changed) and print it
  sh3.py checkpayload <payload.json> <before.json>   every field equal to the read except web_view_properties.url == new
  sh3.py diff <before.json> <after.json>             per creative: every differing field (URL / VOLATILE / OTHER)
  sh3.py urls <after.json>                           print each slot's read-back url and whether it equals new byte for byte
"""
import json, sys, copy, unicodedata
from urllib.parse import urlsplit, parse_qsl

BASE = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
INP = BASE + '/apply8/in_snapchat_3.json'
EXCL = BASE + '/work/excl_platform_refused_v2.json'
SIB = BASE + '/apply7/snap1_work/u02_before.json'   # sibling ManazelAlHadawi_CR2_AR reads (verified clean strings)
VOLATILE = {'updated_at', 'review_status', 'review_status_details', 'semantic_id', 'packaging_status'}


def units():
    return json.load(open(INP))


def sub_id(u, ch):
    s = ch['slot']
    return s.split('(')[1].split(')')[0] if '(' in s else u['unit']


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
        n = ord(c)
        if n > 126 and unicodedata.category(c) not in ('Lo', 'Ll', 'Lu'):
            out.append('\\u%04x' % n)
        else:
            out.append(c)
    return ''.join(out)


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
    sid = sub_id(u, ch)
    for e in json.load(open(EXCL)):
        if e.get('platform') != 'snapchat':
            continue
        ids = {e.get('ad_id'), e.get('creative_id'), e.get('unit')}
        if ids & (set(u['ad_ids']) | {u['unit'], sid}):
            return True
    return False


def sib_strings():
    o = load_objs(SIB)
    x = next(iter(o.values()))
    return x['headline'], x['brand_name']


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


def cmd_state(f):
    (u,) = units()
    objs = load_objs(f)
    parent = json.load(open(f)).get('parent')
    if parent:
        order = parent['composite_properties']['creative_ids']
        for ci, ch in enumerate(u['changes']):
            idx = int(ch['slot'].split('creative_ids[')[1].split(']')[0])
            assert order[idx] == sub_id(u, ch), ('slot index mismatch', ci)
        print('parent', parent['id'], parent['type'], parent['review_status'], 'creative_ids order == slot indices: OK')
    sh, sb = sib_strings()
    payload = []
    for ci, ch in enumerate(u['changes']):
        sid = sub_id(u, ch)
        o = objs[sid]
        assert o['ad_account_id'] == u['account_id'], ('account mismatch', sid)
        assert o['type'] == 'WEB_VIEW', ('not WEB_VIEW', sid)
        cur = o['web_view_properties']['url']
        st = 'EXCLUDED' if excluded(u, ch) else classify(cur, ch)
        print('[%d] %s type=%s review=%s updated=%s state=%s' % (ci, sid, o['type'], o['review_status'], o['updated_at'], st))
        print('     cur', cur)
        h, b = o['headline'], o['brand_name']
        print('     headline len=%d == sibling:%s  brand_name len=%d == sibling:%s  non-letter non-ascii: %s' % (
            len(h), h == sh, len(b), b == sb,
            [('U+%04X' % ord(c)) for c in h + b + o['name'] if ord(c) > 126 and unicodedata.category(c) not in ('Lo', 'Ll', 'Lu')]))
        if st in ('NOW', 'ALT'):
            p = copy.deepcopy(o)
            p['web_view_properties']['url'] = ch['new']
            payload.append(p)
    if payload:
        pf = f.replace('.json', '') + '.payload.json'
        json.dump({'creatives': payload}, open(pf, 'w'), ensure_ascii=False)
        print('payload_file', pf, 'n=%d' % len(payload))
        print(safe_dumps({'creatives': payload}))


def cmd_checkpayload(pf, bf):
    (u,) = units()
    P, B = load_objs(pf), load_objs(bf)
    new_by_sid = {sub_id(u, ch): ch['new'] for ch in u['changes']}
    ok = True
    for cid, p in P.items():
        b = B[cid]
        fp, fb = flat(p), flat(b)
        diffs = [k for k in sorted(set(fp) | set(fb)) if fp.get(k, '<missing>') != fb.get(k, '<missing>')]
        url_ok = p['web_view_properties']['url'] == new_by_sid[cid]
        keys_same_order = list(p.keys()) == list(b.keys())
        print(cid, 'diff_fields=%s url==new:%s key_order_same:%s' % (diffs, url_ok, keys_same_order))
        ok &= diffs == ['web_view_properties.url'] and url_ok and keys_same_order
    print('PAYLOAD_OK' if ok else 'PAYLOAD_BAD')


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


def cmd_urls(af):
    (u,) = units()
    A = load_objs(af)
    for ci, ch in enumerate(u['changes']):
        sid = sub_id(u, ch)
        a = A[sid]
        got = a['web_view_properties']['url']
        print('[%d] %s review=%s url==new(byte):%s' % (ci, sid, a.get('review_status'), got == ch['new']))
        print('     ', got)


if __name__ == '__main__':
    cmd, args = sys.argv[1], sys.argv[2:]
    {'state': cmd_state, 'checkpayload': cmd_checkpayload, 'diff': cmd_diff, 'urls': cmd_urls}[cmd](*args)
