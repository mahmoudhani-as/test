import json, sys
from urllib.parse import urlsplit, parse_qsl

ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
IN = ROOT + '/apply6/in_tiktok_1.json'
OUT = ROOT + '/apply6/out_tiktok_1.jsonl'
UNITS = {u['unit']: u for u in json.load(open(IN))}


def norm(u):
    s = urlsplit(u)
    return (s.scheme, s.netloc, s.path, s.fragment, sorted(parse_qsl(s.query, keep_blank_values=True)))


def classify(uid, cur):
    c = UNITS[uid]['changes'][0]
    if norm(cur) == norm(c['new']):
        return 'AlreadyFixed'
    if cur == c['now'] or cur in c['alt_now']:
        return 'write'
    return 'Skipped'


def done():
    s = set()
    try:
        for l in open(OUT):
            l = l.strip()
            if l:
                s.add(json.loads(l)['unit'])
    except FileNotFoundError:
        pass
    return s


def rec(uid, before, after, result, detail, neid=""):
    u = UNITS[uid]
    c = u['changes'][0]
    assert uid not in done(), 'already recorded ' + uid
    if result == 'Fixed':
        assert after == c['new'], 'after_live != new'
    if result == 'AlreadyFixed':
        assert norm(before) == norm(c['new'])
    r = {"platform": "tiktok", "account_id": u['account_id'], "unit_type": u['unit_type'], "unit": uid,
         "ad_ids": u['ad_ids'], "ad_names": u['ad_names'], "slot": c['slot'], "before": before,
         "after_expected": c['new'], "after_live": after, "result": result, "new_entity_ids": neid,
         "detail": detail}
    with open(OUT, 'a') as f:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print('recorded', uid, result,
          'before==now' if before == c['now'] else ('before in alt' if before in c['alt_now'] else 'before other'))
