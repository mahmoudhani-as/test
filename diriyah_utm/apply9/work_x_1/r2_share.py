# Share-check evidence copied from this agent's LIST_PROMOTED_TWEETS (req c34a9a0c-8830-457e-8207-3f74025902ee) and LIST_TWEETS (req eff7b439-14d3-4667-80b3-5aeae5706b85)
import json
W='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply9/work_x_1'
rows=[
 {"line_item_id":"xwb2v","id":"b6006s","entity_status":"ACTIVE","created_at":"2026-10-13T10:48:54Z","updated_at":"2026-10-13T10:51:26Z","approval_status":"ACCEPTED","tweet_id":"2095131822749524008","deleted":False},
 {"line_item_id":"xwb2v","id":"b6006t","entity_status":"ACTIVE","created_at":"2026-10-13T10:48:54Z","updated_at":"2026-10-13T10:51:24Z","approval_status":"ACCEPTED","tweet_id":"2095139958206177684","deleted":False},
 {"line_item_id":"xwb2t","id":"b6006m","entity_status":"ACTIVE","created_at":"2026-10-13T10:48:51Z","updated_at":"2026-10-13T10:53:16Z","approval_status":"ACCEPTED","tweet_id":"2095139956872167629","deleted":False},
 {"line_item_id":"wyz5p","id":"b5bcus","entity_status":"ACTIVE","created_at":"2026-09-02T13:21:07Z","updated_at":"2026-09-03T12:09:30Z","approval_status":"ACCEPTED","tweet_id":"2095139956872167629","deleted":False},
 {"line_item_id":"wyz5q","id":"b5bcut","entity_status":"ACTIVE","created_at":"2026-09-02T13:21:07Z","updated_at":"2026-09-03T12:09:17Z","approval_status":"ACCEPTED","tweet_id":"2095139958206177684","deleted":False},
 {"line_item_id":"wyz5q","id":"b5bcdy","entity_status":"ACTIVE","created_at":"2026-09-02T12:48:47Z","updated_at":"2026-09-03T12:10:16Z","approval_status":"ACCEPTED","tweet_id":"2095131822749524008","deleted":False},
]
tweet_card={"2095131822749524008":"2095131819687464963","2095139956872167629":"2095139954829447168","2095139958206177684":"2095139954837917698"}
out={'list_req':'c34a9a0c-8830-457e-8207-3f74025902ee','total_count':367,'sort':'created_at-desc','oldest_listed_created_at':'2026-08-30T10:49:06Z',
     'cards_created':'2026-09-02T12:48:46Z..13:21:05Z','tweets_req':'eff7b439-14d3-4667-80b3-5aeae5706b85','promoted_tweet_req_b5bcdy':'73458115-518d-4fc0-8a78-9dd51525306f',
     'tweet_card':tweet_card,'rows':rows}
json.dump(out, open(W+'/r2_share.json','w'), indent=1)
for t,c in tweet_card.items():
    print(t,'card',c,'promoted by',[(r['id'],r['line_item_id'],r['created_at']) for r in rows if r['tweet_id']==t])
