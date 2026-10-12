import json, sys
OUT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/out_google_sl_1.jsonl'
IN = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/in_google_sl_1.json'
units = {u['unit']: u for u in json.load(open(IN))}
def rec(unit_id, before, after_live, result, detail, new_entity_ids=''):
    u = units[unit_id]
    c = u['changes'][0]
    row = {"platform": "google", "account_id": u['account_id'], "unit_type": u['unit_type'], "unit": u['unit'],
           "ad_ids": u['ad_ids'], "ad_names": u['ad_names'], "slot": c['slot'], "before": before,
           "after_expected": c['new'], "after_live": after_live, "result": result,
           "new_entity_ids": new_entity_ids, "detail": detail}
    with open(OUT, 'a') as f:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')
    return row
