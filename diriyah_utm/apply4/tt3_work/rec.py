import json, sys
# usage: rec.py ad_id result after_live detail
ad, result, after_live, detail = sys.argv[1:5]
inp=json.load(open('../in_tiktok_3.json'))
d=json.loads(open('pre_get_text.txt').read())
byid={a['ad_id']:a for a in d['data']['data']['data']['list']}
u=[x for x in inp if x['unit']==ad][0]; ch=u['changes'][0]
row={"platform":"tiktok","account_id":u['account_id'],"unit_type":u['unit_type'],"unit":u['unit'],"ad_ids":u['ad_ids'],"ad_names":u['ad_names'],"slot":ch['slot'],"before":byid[ad]['landing_page_url'],"after_expected":ch['new'],"after_live":after_live,"result":result,"new_entity_ids":"","detail":detail}
if result=='Fixed': assert after_live==ch['new']
with open('../out_tiktok_3.jsonl','a') as f: f.write(json.dumps(row,ensure_ascii=False)+'\n')
print('recorded',ad,result)
