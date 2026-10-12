import json, sys
from urllib.parse import urlsplit, parse_qsl
D='/tmp/claude-0/-home-user-test/0a7a4347-50ae-5891-a613-ee320c5ab4bb/scratchpad/diriyah_utm/apply4'
inp = json.load(open(D+'/in_x_3.json'))
out = D+'/out_x_3.jsonl'
idx = int(sys.argv[1]); before = sys.argv[2]; after_live = sys.argv[3]; result = sys.argv[4]; detail = sys.argv[5]
u = inp[idx]; c = u['changes'][0]
def eq(a,b):
    A=urlsplit(a); B=urlsplit(b)
    return (A.scheme,A.netloc,A.path,A.fragment)==(B.scheme,B.netloc,B.path,B.fragment) and sorted(parse_qsl(A.query,keep_blank_values=True))==sorted(parse_qsl(B.query,keep_blank_values=True))
if result == 'Fixed':
    assert before == c['now'] or before in c['alt_now'], 'before mismatch'
    assert after_live == c['new'], 'after_live != new'
if result == 'AlreadyFixed':
    assert eq(before, c['new']) and after_live == before
rec = {"platform": "x", "account_id": u['account_id'], "unit_type": u['unit_type'], "unit": u['unit'],
       "ad_ids": u['ad_ids'], "ad_names": u['ad_names'], "slot": c['slot'], "before": before,
       "after_expected": c['new'], "after_live": after_live, "result": result, "new_entity_ids": "", "detail": detail}
with open(out, 'a') as f:
    f.write(json.dumps(rec, ensure_ascii=False) + '\n')
print('ok', idx, result, after_live == c['new'])
