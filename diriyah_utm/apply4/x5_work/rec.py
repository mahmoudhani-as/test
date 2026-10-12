import json, sys
D='/tmp/claude-0/-home-user-test/0a7a4347-50ae-5891-a613-ee320c5ab4bb/scratchpad/diriyah_utm/apply4'
inp = json.load(open(D+'/in_x_5.json'))
out = D+'/out_x_5.jsonl'
idx = int(sys.argv[1]); before = sys.argv[2]; after_live = sys.argv[3]; result = sys.argv[4]; detail = sys.argv[5]
u = inp[idx]; c = u['changes'][0]
if result in ('Fixed', 'AlreadyFixed'):
    assert before == c['now'] or before in c['alt_now'] or before == c['new'], 'before mismatch'
if result == 'Fixed':
    assert after_live == c['new'], 'after_live != new'
rec = {"platform": "x", "account_id": u['account_id'], "unit_type": u['unit_type'], "unit": u['unit'],
       "ad_ids": u['ad_ids'], "ad_names": u['ad_names'], "slot": c['slot'], "before": before,
       "after_expected": c['new'], "after_live": after_live, "result": result, "new_entity_ids": "", "detail": detail}
with open(out, 'a') as f:
    f.write(json.dumps(rec, ensure_ascii=False) + '\n')
print('ok', idx, result, after_live == c['new'])
