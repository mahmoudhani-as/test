"""Helper for in_snapchat_5.json: classify live URLs, build payloads, compare objects, record results.
All logic is local; it never calls any API."""
import json, sys, unicodedata
from urllib.parse import urlsplit, parse_qsl

BASE = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
IN = BASE + '/apply6/in_snapchat_5.json'
OUT = BASE + '/apply6/out_snapchat_5.jsonl'
EXCL = BASE + '/work/excl_platform_refused_v2.json'
WD = BASE + '/apply6/snap5_work'

units = json.load(open(IN))


def find(unit_id, change_idx):
    u = [x for x in units if x['unit'] == unit_id]
    assert len(u) == 1, 'unit not found / ambiguous: ' + unit_id
    u = u[0]
    return u, u['changes'][int(change_idx)]


def same_url(a, b):
    A = urlsplit(a); B = urlsplit(b)
    return ((A.scheme, A.netloc, A.path, A.fragment) == (B.scheme, B.netloc, B.path, B.fragment)
            and sorted(parse_qsl(A.query, keep_blank_values=True)) == sorted(parse_qsl(B.query, keep_blank_values=True)))


def excluded(u, ch):
    e = json.load(open(EXCL))
    for x in e:
        if x.get('platform') != 'snapchat':
            continue
        ids = {x.get('ad_id'), x.get('unit'), x.get('creative_id')}
        if ids & (set(u['ad_ids']) | {u['unit'], u['creative_id']}):
            return True
    return False


def classify(u, ch, cur):
    if cur == ch['new']:
        return 'NEW_EXACT'
    if same_url(cur, ch['new']):
        return 'NEW_SAMEPARAMS'
    if cur == ch['now']:
        return 'NOW'
    if cur in ch['alt_now']:
        return 'ALT'
    return 'OTHER'


def vis(s):
    return ''.join(c if (c.isprintable() and unicodedata.category(c) not in ('Cf',)) else '\\u%04x' % ord(c) for c in s)


def cmd_classify(unit_id, change_idx, objfile):
    u, ch = find(unit_id, change_idx)
    obj = json.load(open(objfile))
    cur = obj['web_view_properties']['url']
    print('state', classify(u, ch, cur), '| excluded', excluded(u, ch))
    print('cur', cur)
    for k in ('name', 'headline', 'brand_name'):
        if k in obj:
            s = obj[k]
            print(k, 'len', len(s), 'non-ascii-escaped:', s.encode('ascii', 'backslashreplace').decode())


def cmd_payload(unit_id, change_idx, objfile, outfile):
    u, ch = find(unit_id, change_idx)
    obj = json.load(open(objfile))
    obj['web_view_properties']['url'] = ch['new']
    p = {"creatives": [obj]}
    json.dump(p, open(outfile, 'w'), ensure_ascii=True)
    print(json.dumps(p, ensure_ascii=True))


def cmd_diff(afile, bfile, ignore_url='1'):
    """Compare two creative objects field by field (ignoring server-managed fields)."""
    a = json.load(open(afile)); b = json.load(open(bfile))
    if 'creatives' in a: a = a['creatives'][0]
    if 'creatives' in b: b = b['creatives'][0]
    ign = {'updated_at', 'review_status', 'review_status_details', 'semantic_id', 'packaging_status'}
    diffs = []
    for k in sorted(set(a) | set(b)):
        if k in ign:
            continue
        if k == 'web_view_properties':
            for kk in sorted(set(a.get(k, {})) | set(b.get(k, {}))):
                if kk == 'url' and ignore_url == '1':
                    continue
                if a[k].get(kk, '<absent>') != b[k].get(kk, '<absent>'):
                    diffs.append(('wvp.' + kk, a[k].get(kk, '<absent>'), b[k].get(kk, '<absent>')))
        elif a.get(k, '<absent>') != b.get(k, '<absent>'):
            diffs.append((k, a.get(k, '<absent>'), b.get(k, '<absent>')))
    print('field diffs (excl. server-managed%s):' % (' and url' if ignore_url == '1' else ''), diffs if diffs else 'NONE')
    print('url A:', a.get('web_view_properties', {}).get('url'))
    print('url B:', b.get('web_view_properties', {}).get('url'))
    for k in ('review_status', 'semantic_id', 'updated_at', 'packaging_status', 'review_status_details'):
        print(' ', k, repr(a.get(k, '<absent>')), '->', repr(b.get(k, '<absent>')))


def cmd_record(unit_id, change_idx, before, after_live, result, detail, newids=''):
    u, ch = find(unit_id, change_idx)
    if result == 'Fixed':
        assert after_live == ch['new'], 'readback mismatch -> cannot be Fixed'
    if result == 'AlreadyFixed':
        assert same_url(before, ch['new']), 'before != new -> cannot be AlreadyFixed'
    if result == 'Skipped':
        assert classify(u, ch, before) == 'OTHER'
    rec = {"platform": "snapchat", "account_id": u['account_id'], "unit_type": u['unit_type'], "unit": u['unit'],
           "ad_ids": u['ad_ids'], "ad_names": u['ad_names'], "slot": ch['slot'], "before": before,
           "after_expected": ch['new'], "after_live": after_live, "result": result, "new_entity_ids": newids,
           "detail": detail}
    with open(OUT, 'a') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    print('recorded', unit_id, change_idx, result, '| before', classify(u, ch, before))


if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'classify':
        cmd_classify(*sys.argv[2:5])
    elif c == 'payload':
        cmd_payload(*sys.argv[2:6])
    elif c == 'diff':
        cmd_diff(*sys.argv[2:])
    elif c == 'record':
        cmd_record(*sys.argv[2:])
    else:
        if c != 'cls': raise SystemExit('unknown cmd')


def cmd_cls(unit_id, change_idx, cur):
    u, ch = find(unit_id, change_idx)
    print('state', classify(u, ch, cur), '| excluded', excluded(u, ch), '| byte-equal-new', cur == ch['new'])


if __name__ == '__main__' and sys.argv[1] == 'cls':
    cmd_cls(*sys.argv[2:5])
