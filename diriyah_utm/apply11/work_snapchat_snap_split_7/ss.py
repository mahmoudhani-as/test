#!/usr/bin/env python3
"""Helper for apply11 Snapchat snap_split batch 7 (in_snapchat_snap_split_7.json). Reads/builds work files only.

  ss.py show   <u>                                  -> print unit u (index)
  ss.py state  <u> <creative.json> <ad.json>...     -> files hold objects exactly as read (creative dict, ad dicts).
                                                       Classifies the slot, checks each ad points at the unit creative,
                                                       reports odd characters, writes u<u>_create_payload.json and prints it
                                                       (non-letter non-ASCII chars as \\uXXXX escapes).
  ss.py cmpcreate <u> <orig_creative.json> <new_creative.json>
                                                    -> every field of the new creative vs the original (only url may differ)
  ss.py adpayload <ad.json> <new_creative_id> <out.json>
                                                    -> {"ads":[ad as read, creative_id=new]} (printed with escapes)
  ss.py cmpad <before_ad.json> <after_ad.json>      -> every differing field of the ad
  ss.py same <u> <url_file>                         -> compare a URL (first line of file) with the unit's new / now
"""
import json, sys, copy, unicodedata
from urllib.parse import urlsplit, parse_qsl

BASE = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
INP = BASE + '/apply11/in_snapchat_snap_split_7.json'
WORK = BASE + '/apply11/work_snapchat_snap_split_7'
EXCL = BASE + '/work/excl_platform_refused_v2.json'
NOT_COPIED = {'id', 'updated_at', 'created_at', 'review_status', 'review_status_details', 'semantic_id', 'packaging_status'}
AD_VOLATILE = {'updated_at', 'review_status', 'review_status_reasons', 'delivery_status'}


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


def load_one(f, key):
    o = json.load(open(f))
    if isinstance(o, dict) and key + 's' in o:
        o = o[key + 's'][0]
    if isinstance(o, dict) and key in o and 'id' not in o:
        o = o[key]
    return o


def excluded(u):
    for e in json.load(open(EXCL)):
        if e.get('platform') == 'snapchat' and (e.get('ad_id') in u['ad_ids'] or e.get('ad_id') in (u['unit'], u['creative_id'])):
            return True
    return False


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


def cmd_show(ui):
    u = units()[ui]
    print(ui, u['unit'], 'creative', u['creative_id'], 'recipe', u['recipe'])
    print('  ads', u['ad_ids'], u['ad_names'])
    for ch in u['changes']:
        print('  slot', ch['slot'])
        print('  now ', ch['now'])
        for a in ch.get('alt_now', []):
            print('  alt ', a)
        print('  new ', ch['new'])


def cmd_state(ui, cf, adfs):
    u = units()[ui]
    assert len(u['changes']) == 1 and u['changes'][0]['slot'] == 'creative.web_view_properties.url', 'unexpected slot'
    ch = u['changes'][0]
    c = load_one(cf, 'creative')
    print('creative', c['id'], 'type', c.get('type'), 'review', c.get('review_status'), 'updated', c.get('updated_at'))
    assert c['ad_account_id'] == u['account_id'], 'account mismatch'
    ok = True
    if c['id'] != u['creative_id']:
        print('NOTE: file creative id != unit creative id', c['id'], u['creative_id'])
    if c.get('type') != 'WEB_VIEW':
        print('NOT WEB_VIEW'); ok = False
    seen = set()
    for f in adfs:
        a = load_one(f, 'ad')
        seen.add(a['id'])
        print('ad', a['id'], 'squad', a['ad_squad_id'], 'creative', a['creative_id'], 'status', a['status'], 'type', a.get('type'),
              'review', a.get('review_status'), 'match_unit_creative', a['creative_id'] == u['creative_id'])
        if a['id'] not in u['ad_ids']:
            print('  AD NOT IN UNIT'); ok = False
    missing = set(u['ad_ids']) - seen
    if missing:
        print('ads not read:', missing)
    cur = c['web_view_properties']['url']
    st = classify(cur, ch)
    if excluded(u):
        st = 'EXCLUDED'
    print('state', st)
    print('cur', cur)
    for line in str_report(c):
        print('STR', line)
    if st in ('NOW', 'ALT') and ok:
        p = {k: copy.deepcopy(v) for k, v in c.items() if k not in NOT_COPIED}
        p['web_view_properties']['url'] = ch['new']
        pf = '%s/u%d_create_payload.json' % (WORK, ui)
        json.dump({'creatives': [p]}, open(pf, 'w'), ensure_ascii=False, indent=1)
        print('not copied:', sorted(k for k in c if k in NOT_COPIED))
        print('payload_file', pf)
        print(safe_dumps({'creatives': [p]}))


def cmd_cmpcreate(ui, of, nf):
    u = units()[ui]
    ch = u['changes'][0]
    o, n = load_one(of, 'creative'), load_one(nf, 'creative')
    fo, fn = flat({k: v for k, v in o.items() if k not in NOT_COPIED}), flat({k: v for k, v in n.items() if k not in NOT_COPIED})
    other = []
    for k in sorted(set(fo) | set(fn)):
        vo, vn = fo.get(k, '<missing>'), fn.get(k, '<missing>')
        if vo != vn:
            tag = 'URL' if k == 'web_view_properties.url' else 'OTHER'
            if tag == 'OTHER':
                other.append(k)
            print('  %s %s: %r -> %r' % (tag, k, vo, vn))
    url = n['web_view_properties']['url']
    print('new creative', n.get('id'), 'review', n.get('review_status'), 'type', n.get('type'))
    print('url_equals_new_bytes', url == ch['new'])
    print('OTHER_FIELD_DIFFS=%d %s' % (len(other), other))
    print('volatile of new:', {k: n.get(k) for k in sorted(NOT_COPIED) if k in n})


def cmd_adpayload(af, ncid, out):
    a = load_one(af, 'ad')
    p = copy.deepcopy(a)
    p['creative_id'] = ncid
    json.dump({'ads': [p]}, open(out, 'w'), ensure_ascii=False, indent=1)
    print(safe_dumps({'ads': [p]}))


def cmd_cmpad(bf, af):
    b, a = load_one(bf, 'ad'), load_one(af, 'ad')
    fb, fa = flat(b), flat(a)
    other = []
    for k in sorted(set(fb) | set(fa)):
        vb, va = fb.get(k, '<missing>'), fa.get(k, '<missing>')
        if vb != va:
            base = k.split('[')[0]
            tag = 'CREATIVE' if k == 'creative_id' else ('VOLATILE' if base in AD_VOLATILE else 'OTHER')
            if tag == 'OTHER':
                other.append(k)
            print('  %s %s: %r -> %r' % (tag, k, vb, va))
    print('ad', a['id'], 'creative', a['creative_id'], 'status', b['status'], '->', a['status'], 'review', a.get('review_status'))
    print('OTHER_FIELD_DIFFS=%d %s' % (len(other), other))


def cmd_same(ui, f):
    u = units()[ui]
    ch = u['changes'][0]
    url = open(f).read().split('\n')[0]
    print('equals_new_bytes', url == ch['new'], 'same_url_new', same_url(url, ch['new']), 'equals_now', url == ch['now'])


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'show':
        cmd_show(int(a[1]))
    elif a[0] == 'state':
        cmd_state(int(a[1]), a[2], a[3:])
    elif a[0] == 'cmpcreate':
        cmd_cmpcreate(int(a[1]), a[2], a[3])
    elif a[0] == 'adpayload':
        cmd_adpayload(a[1], a[2], a[3])
    elif a[0] == 'cmpad':
        cmd_cmpad(a[1], a[2])
    elif a[0] == 'same':
        cmd_same(int(a[1]), a[2])
