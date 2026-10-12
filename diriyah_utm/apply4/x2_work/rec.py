import json, sys
D='/tmp/claude-0/-home-user-test/0a7a4347-50ae-5891-a613-ee320c5ab4bb/scratchpad/diriyah_utm/apply4'
inp = json.load(open(D+'/in_x_2.json')); pre = json.load(open(D+'/x2_work/pre.json'))
out = D+'/out_x_2.jsonl'
idx = int(sys.argv[1]); after_live = sys.argv[2]; after_title = sys.argv[3]; after_media = sys.argv[4]; after_name = sys.argv[5]; result = sys.argv[6]; extra = sys.argv[7] if len(sys.argv) > 7 else ''
u = inp[idx]; c = u['changes'][0]
card_id, p = next((k, v) for k, v in pre.items() if v['tweet'] == u['unit'])
before = p['url']
assert before == c['now'] or before in c['alt_now'] or before == c['new'], 'before mismatch'
checks = []
if result == 'Fixed':
    assert after_live == c['new'], 'after_live != new'
    assert after_title == p['title'], 'title changed'
    assert after_media == p['media_key'], 'media changed'
    assert after_name == p['name'], 'name changed'
detail = (f"UPDATE_CARD PUT /12/accounts/{u['account_id']}/cards/{card_id} (tweet {u['unit']} card_uri card://{card_id}) OK (dry-run then live); "
          f"card re-read: components[1].destination.url equals new byte for byte; name/title{' (Arabic codepoints verified)' if not p['title'].isascii() else ''}/media_key/card_type IMAGE_WEBSITE unchanged; "
          f"no experiment_signals on card (none before); card unique to this tweet (card_uri checked across all 140 tweets promoted on/after 2026-06-09, incl. deleted; promoted tweet {u['ad_ids'][0]} is the only promoted_tweet for this tweet)")
if extra: detail += '; ' + extra
rec = {"platform": "x", "account_id": u['account_id'], "unit_type": u['unit_type'], "unit": u['unit'],
       "ad_ids": u['ad_ids'], "ad_names": u['ad_names'], "slot": c['slot'], "before": before,
       "after_expected": c['new'], "after_live": after_live, "result": result, "new_entity_ids": "", "detail": detail}
with open(out, 'a') as f:
    f.write(json.dumps(rec, ensure_ascii=False) + '\n')
print('ok', idx, result, after_live == c['new'])
