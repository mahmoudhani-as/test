#!/usr/bin/env python3
"""Read-only helper for apply8 Snapchat batch 1 (in_snapchat_1.json). It never calls any API.

  h.py show <u>                 print unit u (index) and its changes, URLs split into params
  h.py cls <u> <c> <url>        classify a live URL for change c of unit u: NEW / NOW / ALT / OTHER, with a param diff
  h.py str <text>               print each non-ASCII / invisible character of a string with its code point
  h.py results <spec.json>      build the final results list from a spec (see build_results)
"""
import json, sys, re, unicodedata
from urllib.parse import urlsplit, parse_qsl

BASE = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
INP = BASE + '/apply8/in_snapchat_1.json'


def units():
    return json.load(open(INP))


def sub_id(u, ch):
    m = re.search(r'-> creative ([0-9a-f-]{36})', ch['slot'])
    return m.group(1) if m else u['unit']


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


def split(url):
    p = urlsplit(url)
    return '%s://%s%s' % (p.scheme, p.netloc, p.path), parse_qsl(p.query, keep_blank_values=True), p.fragment


def show(ui):
    u = units()[ui]
    print('unit', ui, u['unit'], 'acct', u['account_id'], 'ads', u['ad_ids'], u['ad_names'], u.get('status_11oct'))
    for ci, ch in enumerate(u['changes']):
        print(' [%d] sub=%s slot=%s' % (ci, sub_id(u, ch), ch['slot']))
        for lab in ('now', 'new'):
            base, q, frag = split(ch[lab])
            print('   %s len=%d %s' % (lab, len(ch[lab]), base))
            for k, v in q:
                print('        %s=%s' % (k, v))
        for a in ch.get('alt_now', []):
            print('   alt', a)


def cls(ui, ci, url):
    u = units()[ui]
    ch = u['changes'][ci]
    st = classify(url, ch)
    print('state', st, '| len', len(url), '| ==now', url == ch['now'], '| ==new', url == ch['new'])
    tgt = ch['new'] if st == 'NEW' else ch['now']
    a, b = split(url), split(tgt)
    if a[0] != b[0]:
        print('  base differs:', a[0], 'vs', b[0])
    da, db = dict(a[1]), dict(b[1])
    for k in sorted(set(da) | set(db)):
        if da.get(k) != db.get(k):
            print('  param %s: live=%r plan=%r' % (k, da.get(k), db.get(k)))


def strinfo(s):
    print('len', len(s), 'double_space', '  ' in s, 'edge_space', s != s.strip())
    for i, c in enumerate(s):
        if ord(c) > 126 or ord(c) < 32:
            print('  %3d U+%04X %s %s' % (i, ord(c), unicodedata.category(c), unicodedata.name(c, '?')))


def build_results(spec_f):
    """spec: list of {"u": i, "c": j, "result": ..., "before": "now"|"new"|"alt:k"|{"literal": s},
    "after_live": same forms, "detail": "...", "new_entity_ids": ""}. Prints the JSON results list."""
    us = units()
    spec = json.load(open(spec_f))
    seen = set()
    out = []

    def val(form, ch):
        if isinstance(form, dict):
            return form['literal']
        if form == 'now':
            return ch['now']
        if form == 'new':
            return ch['new']
        if form.startswith('alt:'):
            return ch['alt_now'][int(form[4:])]
        raise ValueError(form)

    for s in spec:
        u = us[s['u']]
        ch = u['changes'][s['c']]
        key = (s['u'], s['c'])
        assert key not in seen, ('duplicate', key)
        seen.add(key)
        before, after = val(s['before'], ch), val(s['after_live'], ch)
        r = s['result']
        if r == 'Fixed':
            assert after == ch['new']
            assert before == ch['now'] or before in ch.get('alt_now', [])
        if r == 'AlreadyFixed':
            assert same_url(before, ch['new'])
        out.append({"platform": "snapchat", "account_id": u['account_id'], "unit_type": u['unit_type'], "unit": u['unit'],
                    "ad_ids": u['ad_ids'], "ad_names": u['ad_names'], "slot": ch['slot'], "before": before,
                    "after_expected": ch['new'], "after_live": after, "result": r,
                    "new_entity_ids": s.get('new_entity_ids', ''), "detail": s['detail']})
    total = sum(len(u['changes']) for u in us)
    missing = [(i, j) for i, u in enumerate(us) for j in range(len(u['changes'])) if (i, j) not in seen]
    print('changes in input', total, 'in spec', len(out), 'missing', missing, file=sys.stderr)
    print(json.dumps(out, ensure_ascii=False))


if __name__ == '__main__':
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == 'show':
        show(int(args[0]))
    elif cmd == 'cls':
        cls(int(args[0]), int(args[1]), args[2])
    elif cmd == 'str':
        strinfo(args[0])
    elif cmd == 'results':
        build_results(args[0])
    else:
        raise SystemExit('unknown command')
