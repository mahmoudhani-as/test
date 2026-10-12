#!/usr/bin/env python3
"""Helper for apply6 Snapchat batch 1.

Usage:
  snaph.py state   <before.json> <unit_id> <sub_creative_id>
      -> prints state (NEW/NOW/ALT/OTHER) and writes <before>.payload.json
         ({"creatives":[obj]} with only web_view_properties.url replaced)
  snaph.py diff    <before.json> <after.json>
      -> lists every field that differs (ignores url, updated_at, review fields, semantic_id)
  snaph.py record  <unit_id> <sub_creative_id> <before_url> <after_live_url> <result> <detail> [new_entity_ids]
      -> appends one result line to out_snapchat_1.jsonl
"""
import json, sys, os
from urllib.parse import urlsplit, parse_qsl

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INP = os.path.join(BASE, 'in_snapchat_1.json')
OUT = os.path.join(BASE, 'out_snapchat_1.jsonl')


def load_units():
    return json.load(open(INP))


def find_change(unit_id, sub_id):
    for u in load_units():
        if u['unit'] != unit_id:
            continue
        for c in u['changes']:
            s = c['slot']
            if '-> creative ' in s:
                sid = s.split('-> creative ')[1].split()[0]
            else:
                sid = u['unit']
            if sid == sub_id:
                return u, c
    raise SystemExit('change not found: %s %s' % (unit_id, sub_id))


def same_url(a, b):
    if a == b:
        return True
    pa, pb = urlsplit(a), urlsplit(b)
    if (pa.scheme, pa.netloc, pa.path, pa.fragment) != (pb.scheme, pb.netloc, pb.path, pb.fragment):
        return False
    return sorted(parse_qsl(pa.query, keep_blank_values=True)) == sorted(parse_qsl(pb.query, keep_blank_values=True))


def classify(cur, c):
    if same_url(cur, c['new']):
        return 'NEW'
    if cur == c['now']:
        return 'NOW'
    if cur in c['alt_now']:
        return 'ALT'
    return 'OTHER'


def nonascii_report(obj, path=''):
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            out += nonascii_report(v, path + '.' + k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out += nonascii_report(v, '%s[%d]' % (path, i))
    elif isinstance(obj, str):
        if any(ord(ch) > 127 for ch in obj) or obj != obj.strip():
            out.append((path, len(obj), ' '.join('U+%04X' % ord(ch) for ch in obj)))
    return out


def cmd_state(before, unit_id, sub_id):
    obj = json.load(open(before))
    assert obj['id'] == sub_id, ('id mismatch', obj['id'], sub_id)
    u, c = find_change(unit_id, sub_id)
    assert obj['ad_account_id'] == u['account_id'], 'account mismatch'
    cur = obj['web_view_properties']['url']
    st = classify(cur, c)
    print('type', obj.get('type'), 'review_status', obj.get('review_status'))
    print('state', st)
    print('cur ', cur)
    print('new ', c['new'])
    for p, n, cps in nonascii_report(obj):
        print('NONASCII', p, 'len', n, ':', cps)
    payload_obj = json.loads(json.dumps(obj))
    payload_obj['web_view_properties']['url'] = c['new']
    payload = {'creatives': [payload_obj]}
    pf = before.replace('.json', '.payload.json')
    json.dump(payload, open(pf, 'w'), ensure_ascii=False)
    print('payload_file', pf)
    print(json.dumps(payload, ensure_ascii=False))


IGNORE = {'updated_at', 'review_status', 'review_status_details', 'semantic_id', 'packaging_status'}


def flat(obj, path=''):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(flat(v, path + '.' + k if path else k))
        if not obj:
            out[path] = {}
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(flat(v, '%s[%d]' % (path, i)))
        if not obj:
            out[path] = []
    else:
        out[path] = obj
    return out


def cmd_diff(a, b):
    fa, fb = flat(json.load(open(a))), flat(json.load(open(b)))
    diffs = []
    for k in sorted(set(fa) | set(fb)):
        if fa.get(k, '<missing>') != fb.get(k, '<missing>'):
            diffs.append(k)
            tag = 'IGNORED' if k in IGNORE else ('URL' if k == 'web_view_properties.url' else 'OTHER')
            print(tag, k, '|', repr(fa.get(k, '<missing>'))[:300], '->', repr(fb.get(k, '<missing>'))[:300])
    other = [k for k in diffs if k not in IGNORE and k != 'web_view_properties.url']
    print('OTHER_FIELD_CHANGES', len(other), other)


def cmd_record(unit_id, sub_id, before_url, after_live, result, detail, new_ids=''):
    u, c = find_change(unit_id, sub_id)
    if result == 'Fixed':
        assert after_live == c['new'], 'readback mismatch: not Fixed'
    if result == 'AlreadyFixed':
        assert same_url(before_url, c['new']), 'not equal to new'
    rec = {"platform": "snapchat", "account_id": u['account_id'], "unit_type": u['unit_type'], "unit": unit_id,
           "ad_ids": u['ad_ids'], "ad_names": u['ad_names'], "slot": c['slot'], "before": before_url,
           "after_expected": c['new'], "after_live": after_live, "result": result,
           "new_entity_ids": new_ids, "detail": detail}
    # refuse duplicates
    if os.path.exists(OUT):
        for line in open(OUT):
            line = line.strip()
            if line:
                r = json.loads(line)
                if r['unit'] == unit_id and r['slot'] == c['slot']:
                    raise SystemExit('duplicate record for %s %s' % (unit_id, c['slot']))
    with open(OUT, 'a') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    print('recorded', unit_id, sub_id, result, 'before==now' if before_url == c['now'] else (
        'before in alt' if before_url in c['alt_now'] else ('before==new' if same_url(before_url, c['new']) else 'before OTHER')))


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'state':
        cmd_state(*sys.argv[2:5])
    elif cmd == 'diff':
        cmd_diff(*sys.argv[2:4])
    elif cmd == 'record':
        cmd_record(*sys.argv[2:])
    else:
        raise SystemExit(__doc__)
