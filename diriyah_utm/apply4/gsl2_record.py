import json, sys
IN='/tmp/claude-0/-home-user-test/0a7a4347-50ae-5891-a613-ee320c5ab4bb/scratchpad/diriyah_utm/apply4/in_google_sl_2.json'
OUT='/tmp/claude-0/-home-user-test/0a7a4347-50ae-5891-a613-ee320c5ab4bb/scratchpad/diriyah_utm/apply4/out_google_sl_2.jsonl'
# args: unit before after_live result detail
unit, before, after_live, result, detail = sys.argv[1:6]
units = json.load(open(IN))
u = [x for x in units if x['unit']==unit][0]
ch = u['changes'][0]
if result == 'Fixed':
    assert after_live == ch['new'], 'after_live != new'
rec = {"platform":"google","account_id":u['account_id'],"unit_type":u['unit_type'],"unit":u['unit'],"ad_ids":u['ad_ids'],"ad_names":u['ad_names'],"slot":ch['slot'],"before":before,"after_expected":ch['new'],"after_live":after_live,"result":result,"new_entity_ids":"","detail":detail}
with open(OUT,'a') as f:
    f.write(json.dumps(rec, ensure_ascii=False)+'\n')
print('ok', unit, result, before==ch['now'])
