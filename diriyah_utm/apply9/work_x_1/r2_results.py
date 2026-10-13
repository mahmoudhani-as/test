# Prints this attempt's results array (stdout only).
import json
W='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply9/work_x_1'
IN='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply9/in_x_1.json'
U=json.load(open(IN, encoding='utf-8'))
p0=json.load(open(W+'/r2_pre_0.json', encoding='utf-8'))
p123=json.load(open(W+'/r2_pre_123.json', encoding='utf-8'))
sh=json.load(open(W+'/r2_share.json', encoding='utf-8'))
post0=json.load(open(W+'/post_0.json', encoding='utf-8'))  # earlier attempt of this batch
EARLY404={'2095139956872167629':'f8e0d165-d4eb-4721-98c5-3661de36e81b','2095139958206177684':'086df080-f651-47ba-84c5-8409fa2ffbda'}
out=[]
for i,u in enumerate(U):
    for ch in u['changes']:
        r={'platform':u['platform'],'account_id':u['account_id'],'unit_type':u['unit_type'],'unit':u['unit'],'ad_ids':u['ad_ids'],'ad_names':u['ad_names'],
           'slot':ch['slot'],'after_expected':ch['new'],'new_entity_ids':''}
        if i==0:
            assert p0['cur']==ch['new']
            r['before']=p0['cur']; r['after_live']=p0['cur']; r['result']='AlreadyFixed'
            r['detail']=(f"Re-read GET_CARD /12/accounts/{u['account_id']}/cards/{u['unit']} req {p0['get_req']} (VIDEO_WEBSITE, not deleted): "
                         f"{ch['slot']} == new byte for byte, so no dry run and no live write in this attempt. "
                         f"The value was written earlier in this apply9 run by the previous attempt of this batch (apply9/work_x_1/post_0.json: "
                         f"UPDATE_CARD live req {post0['write_req']}, 1 attempt; its read-back GET_CARD req {post0['get_req']} also showed url == new).")
        else:
            rd=p123[str(i)]
            assert rd['url']==ch['now'] and rd['tweet']==u['unit']
            card=rd['card']; tw=u['unit']
            prom=[x for x in sh['rows'] if x['tweet_id']==tw]
            others=[x for x in prom if x['id'] not in u['ad_ids']]
            assert others and {x['id'] for x in prom}-{x['id'] for x in others}==set(u['ad_ids'])
            oth='; '.join(f"{x['id']} (line item {x['line_item_id']}, created {x['created_at']}, {x['entity_status']}, {x['approval_status']})" for x in others)
            r['before']=rd['url']; r['after_live']=rd['url']; r['result']='Skipped'
            r['detail']=(f"card shared by other promoted tweets: tweet {tw} (this unit) is also promoted by {oth}, which is not in ad_ids {u['ad_ids']} "
                         f"(LIST_PROMOTED_TWEETS req {sh['list_req']}, created_at-desc, {sh['total_count']} total; the listing covers every promoted tweet created since "
                         f"{sh['oldest_listed_created_at']}, before the card existed). No dry run and no live write. "
                         f"How the slot was read: the unit id is the tweet id, not a card id. " +
                         (f"GET_CARD {tw} in this attempt: 404 NOT_FOUND 'Card {tw} was not found for Account 4503599737345965' (req da1bc68e-29f8-4f03-b584-7c834abbf1ff); "
                          f"GET_PROMOTED_TWEET {u['ad_ids'][0]} req {sh['promoted_tweet_req_b5bcdy']} gives tweet_id {tw}"
                          if i==1 else
                          f"LIST_PROMOTED_TWEETS req {sh['list_req']} gives {u['ad_ids'][0]} tweet_id {tw}; the earlier attempt of this batch got 404 NOT_FOUND on GET_CARD {tw} "
                          f"(req {EARLY404[tw]}, per apply9/work_x_1/results9.py); this attempt did not repeat that call") +
                         f". The tweet carries card://{card} (LIST_TWEETS req {sh['tweets_req']}; no link in the tweet text). "
                         f"GET_CARD {card} req {rd['get_req']} ({rd['card_type']}, not deleted) shows {ch['slot']} == now byte for byte.")
        out.append(r)
print(json.dumps(out, ensure_ascii=False, indent=1))
print('COUNT', len(out), 'expected', sum(len(u['changes']) for u in U))
