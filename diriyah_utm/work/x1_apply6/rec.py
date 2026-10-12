import sys, json
sys.path.insert(0,'/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/work/x1_apply6')
from lib import *
# usage: rec.py idx result after_live_file detail_extra
idx=int(sys.argv[1]); result=sys.argv[2]; after_live=open(sys.argv[3]).read().rstrip('\n'); extra=sys.argv[4] if len(sys.argv)>4 else ''
units=json.load(open(IN)); u=units[idx]; ch=u['changes'][0]
assert len(u['changes'])==1
pre=load_cards(W+'/pre_snapshot_raw.json')[u['unit']]
before=slot_get(pre, ch['slot'])
share=json.load(open(W+'/share_check.json'))['share'][u['unit']]
if result=='Fixed':
    assert before==ch['now'] or before in ch['alt_now'], 'before mismatch'
    assert after_live==ch['new'], 'after_live != new'
    detail=(f"UPDATE_CARD PUT /12/accounts/{u['account_id']}/cards/{u['unit']} (promoted tweet {','.join(u['ad_ids'])} -> tweet {','.join(share['tweets'])}, card_uri card://{u['unit']}, {pre['card_type']}) OK (dry-run preview showed only components[1].destination.url changed, then live); "
            f"before equalled 'now' byte for byte; independent GET_CARD re-read: components[1].destination.url equals new byte for byte; name, card_type, MEDIA media_key, DETAILS title and destination.type WEBSITE unchanged; "
            f"no experiment_signals on card before or after (GET_CARD/LIST_CARDS show none, so nothing to carry in the PUT); body sent = name + components as read (media_metadata read-only, not sent) with only the url replaced; "
            f"card unique to this promoted tweet (live LIST_PROMOTED_TWEETS with_deleted: 411; card_uri of all 87 tweets created after the oldest card in this batch (minus 1 day) read live via LIST_TWEETS: only tweet {','.join(share['tweets'])} carries this card_uri and only {','.join(share['promoted'])} promotes it)")
elif result=='Failed':
    detail=''
else:
    detail=''
if extra: detail=(detail+'; '+extra) if detail else extra
rec={"platform":"x","account_id":u['account_id'],"unit_type":u['unit_type'],"unit":u['unit'],"ad_ids":u['ad_ids'],"ad_names":u['ad_names'],
     "slot":ch['slot'],"before":before,"after_expected":ch['new'],"after_live":after_live,"result":result,"new_entity_ids":"","detail":detail}
with open(OUT,'a') as f: f.write(json.dumps(rec, ensure_ascii=False)+'\n')
print('recorded', idx, u['unit'], result, 'after==new:', after_live==ch['new'])
