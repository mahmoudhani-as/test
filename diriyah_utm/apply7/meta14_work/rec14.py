import json, sys, datetime
from urllib.parse import urlsplit, parse_qsl

ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
IN = ROOT + '/apply7/in_meta_14.json'
OUT = ROOT + '/apply7/out_meta_14.jsonl'
PROG = ROOT + '/apply7/meta14_work/progress.jsonl'
EXCL = ROOT + '/work/excl_platform_refused_v2.json'


def unit(ad_id):
    for u in json.load(open(IN)):
        if u['unit'] == ad_id:
            return u
    raise KeyError(ad_id)


def excluded(ad_id, slot):
    return any(str(x.get('ad_id')) == str(ad_id) and x.get('slot') == slot for x in json.load(open(EXCL)))


def same_url(a, b):
    if a is None or b is None:
        return False
    A, B = urlsplit(a), urlsplit(b)
    return (A.scheme, A.netloc, A.path, A.fragment) == (B.scheme, B.netloc, B.path, B.fragment) and \
        sorted(parse_qsl(A.query, keep_blank_values=True)) == sorted(parse_qsl(B.query, keep_blank_values=True))


def classify(ad_id, idx, cur):
    c = unit(ad_id)['changes'][idx]
    if excluded(ad_id, c['slot']):
        return 'Excluded'
    if same_url(cur, c['new']):
        return 'AlreadyFixed'
    if cur == c['now'] or cur in c['alt_now']:
        return 'Write'
    return 'Skipped'


def progress(**kw):
    kw['ts'] = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    with open(PROG, 'a') as f:
        f.write(json.dumps(kw) + '\n')


def record(ad_id, idx, before, after_live, result, new_ids, detail):
    u = unit(ad_id)
    c = u['changes'][idx]
    if result == 'Fixed':
        assert after_live == c['new'], 'after_live != new'
        assert before == c['now'] or before in c['alt_now'], 'before not now/alt_now'
    if result == 'AlreadyFixed':
        assert same_url(before, c['new'])
    rec = {"platform": "meta", "account_id": u['account_id'], "unit_type": u['unit_type'], "unit": u['unit'],
           "ad_ids": u['ad_ids'], "ad_names": u['ad_names'], "slot": c['slot'], "before": before,
           "after_expected": c['new'], "after_live": after_live, "result": result,
           "new_entity_ids": new_ids, "detail": detail}
    with open(OUT, 'a') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print('recorded', ad_id, c['slot'], result, 'after==new:', after_live == c['new'])
