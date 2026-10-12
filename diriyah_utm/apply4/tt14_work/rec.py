import json, sys
# usage: rec.py <ad_id> <result> <before> <after_live> <detail> [new_entity_ids]
units={u['unit']:u for u in json.load(open('../in_tiktok_14.json'))}
ad,result,before,after_live,detail=sys.argv[1:6]
nid=sys.argv[6] if len(sys.argv)>6 else ""
u=units[ad]; ch=u['changes'][0]
if result=='Fixed': assert after_live==ch['new'], 'after_live != new'
r={"platform":"tiktok","account_id":u['account_id'],"unit_type":u['unit_type'],"unit":u['unit'],"ad_ids":u['ad_ids'],"ad_names":u['ad_names'],
   "slot":ch['slot'],"before":before,"after_expected":ch['new'],"after_live":after_live,"result":result,"new_entity_ids":nid,"detail":detail}
with open('../out_tiktok_14.jsonl','a') as f: f.write(json.dumps(r,ensure_ascii=False)+"\n")
print('recorded',ad,result)
