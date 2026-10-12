"""Check live state of one Snapchat change against the plan and build the PUT payload.

usage: python3 -I snap_prep.py <unit_id> <change_idx> <before_obj.json>
before_obj.json = the (sub-)creative object exactly as read (the "creative" dict).
Prints state NEW / NOW / ALT / OTHER, and for NOW/ALT writes <before>.payload.json
({"creatives":[obj with only web_view_properties.url = new]}) and prints it.
"""
import json, sys, copy, unicodedata
from urllib.parse import urlsplit, parse_qsl

BASE = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
INP = BASE + '/apply6/in_snapchat_2.json'
EXCL = BASE + '/work/excl_platform_refused_v2.json'


def same_url(a, b):
    if a == b:
        return True
    pa, pb = urlsplit(a), urlsplit(b)
    if (pa.scheme, pa.netloc, pa.path, pa.fragment) != (pb.scheme, pb.netloc, pb.path, pb.fragment):
        return False
    return sorted(parse_qsl(pa.query, keep_blank_values=True)) == sorted(parse_qsl(pb.query, keep_blank_values=True))


def odd_chars(s):
    out = []
    for i, ch in enumerate(s):
        if ord(ch) > 126 or ch in '\t\r\n' or (ch == ' ' and i + 1 < len(s) and s[i + 1] == ' '):
            if unicodedata.category(ch) in ('Lo',):  # plain letters (Arabic etc.) - skip
                continue
            out.append((i, 'U+%04X' % ord(ch), unicodedata.name(ch, '?')))
    return out


def main():
    uid, idx, bf = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    units = json.load(open(INP))
    u = [x for x in units if x['unit'] == uid][0]
    ch = u['changes'][idx]
    excl = json.load(open(EXCL))
    for e in excl:
        if e['platform'] == 'snapchat' and (e['ad_id'] in u['ad_ids'] or e['ad_id'] == uid) and e['slot'] == ch['slot']:
            print('EXCLUDED (platform-refused) - do not write')
            return
    obj = json.load(open(bf))
    cur = obj['web_view_properties']['url']
    if same_url(cur, ch['new']):
        state = 'NEW'
    elif cur == ch['now']:
        state = 'NOW'
    elif cur in ch['alt_now']:
        state = 'ALT'
    else:
        state = 'OTHER'
    print('slot', ch['slot'])
    print('type', obj.get('type'), 'review_status', obj.get('review_status'), 'updated_at', obj.get('updated_at'))
    print('state', state)
    for k in ('name', 'headline', 'brand_name'):
        if k in obj:
            print('  %s: len=%d odd=%s' % (k, len(obj[k]), odd_chars(obj[k])))
    if state in ('NOW', 'ALT'):
        p = copy.deepcopy(obj)
        p['web_view_properties']['url'] = ch['new']
        payload = {'creatives': [p]}
        json.dump(payload, open(bf + '.payload.json', 'w'), ensure_ascii=False)
        print(json.dumps(payload, ensure_ascii=False))


main()
