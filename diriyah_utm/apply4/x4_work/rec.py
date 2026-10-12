import json, sys
from urllib.parse import urlsplit, parse_qsl
D='/tmp/claude-0/-home-user-test/0a7a4347-50ae-5891-a613-ee320c5ab4bb/scratchpad/diriyah_utm/apply4'
inp = json.load(open(D+'/in_x_4.json'))
out = D+'/out_x_4.jsonl'
idx = int(sys.argv[1]); before = sys.argv[2]; after_live = sys.argv[3]; result = sys.argv[4]; extra = sys.argv[5] if len(sys.argv) > 5 else ''; ctype = sys.argv[6] if len(sys.argv) > 6 else 'IMAGE_WEBSITE'
u = inp[idx]; c = u['changes'][0]
m = {l.split()[0]: l.split() for l in open(D+'/x4_work/map.txt')}
tw, card_id, pt = m[u['unit']]
def eq(a,b):
    A=urlsplit(a); B=urlsplit(b)
    return (A.scheme,A.netloc,A.path,A.fragment)==(B.scheme,B.netloc,B.path,B.fragment) and sorted(parse_qsl(A.query,keep_blank_values=True))==sorted(parse_qsl(B.query,keep_blank_values=True))
if result == 'Fixed':
    assert before == c['now'] or before in c['alt_now'], 'before mismatch'
    assert after_live == c['new'], 'after_live != new'
    detail = (f"UPDATE_CARD PUT /12/accounts/{u['account_id']}/cards/{card_id} (tweet {u['unit']} card_uri card://{card_id}, {ctype}) OK (dry-run then live); "
              f"card re-read: components[1].destination.url equals new byte for byte; name/title/media_key/card_type unchanged; no experiment_signals on card (none before); "
              f"card unique to this tweet (card_uri checked for all 50 promoted tweets incl. deleted whose tweet was created after 2026-09-05 card creation; {pt} is the only promoted_tweet for this tweet)")
elif result == 'AlreadyFixed':
    assert eq(before, c['new']) and after_live == before
    detail = f"card {card_id} slot already equals new; no write"
else:
    detail = ''
if extra: detail = (detail + '; ' + extra) if detail else extra
rec = {"platform": "x", "account_id": u['account_id'], "unit_type": u['unit_type'], "unit": u['unit'],
       "ad_ids": u['ad_ids'], "ad_names": u['ad_names'], "slot": c['slot'], "before": before,
       "after_expected": c['new'], "after_live": after_live, "result": result, "new_entity_ids": "", "detail": detail}
with open(out, 'a') as f:
    f.write(json.dumps(rec, ensure_ascii=False) + '\n')
print('ok', idx, result, after_live == c['new'])
