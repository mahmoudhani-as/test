import json,sys
# args: unit_id before after_live result detail
inp=json.load(open('in_snapchat_2.json'))
uid,before,after_live,result,detail=sys.argv[1:6]
u=[x for x in inp if x['unit']==uid][0]
ch=u['changes'][0]
if result=='Fixed':
    assert after_live==ch['new'], 'readback mismatch'
rec={"platform":"snapchat","account_id":u['account_id'],"unit_type":u['unit_type'],"unit":uid,"ad_ids":u['ad_ids'],"ad_names":u['ad_names'],"slot":ch['slot'],"before":before,"after_expected":ch['new'],"after_live":after_live,"result":result,"new_entity_ids":"","detail":detail}
with open('out_snapchat_2.jsonl','a') as f: f.write(json.dumps(rec,ensure_ascii=False)+'\n')
print('ok',uid,result, 'before==now' if before==ch['now'] else ('before in alt' if before in ch['alt_now'] else ('before==new' if before==ch['new'] else 'before OTHER')))
