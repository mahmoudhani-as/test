import json,sys
idx=int(sys.argv[1]); before=sys.argv[2]; after=sys.argv[3]; result=sys.argv[4]; newids=sys.argv[5]; detail=sys.argv[6]
u=json.load(open('in_meta_1.json'))[idx]
c=u['changes'][0]
if result=='Fixed':
    assert after==c['new'], 'after mismatch'
    assert before==c['now'] or before in c['alt_now']
rec={"platform":"meta","account_id":u['account_id'],"unit_type":u['unit_type'],"unit":u['unit'],"ad_ids":u['ad_ids'],"ad_names":u['ad_names'],"slot":c['slot'],"before":before,"after_expected":c['new'],"after_live":after,"result":result,"new_entity_ids":newids,"detail":detail}
open('out_meta_1.jsonl','a').write(json.dumps(rec,ensure_ascii=False)+"\n")
print('ok', after==c['new'])
