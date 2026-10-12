# usage: record.py <after_live_json> <unit_ids_csv> <detail> [result_override]
import json, sys
from urllib.parse import urlsplit, parse_qsl
d={u['unit']:u for u in json.load(open('in_google_2.json'))}
before=json.load(open('g2_work/live_before.json'))
after=json.load(open(sys.argv[1]))
units=sys.argv[2].split(',')
detail=sys.argv[3]
ov=sys.argv[4] if len(sys.argv)>4 else None
with open('out_google_2.jsonl','a') as f:
    for uid in units:
        u=d[uid]; c=u['changes'][0]
        al=after.get(uid)
        res = ov or ('Fixed' if al==c['new'] else 'Failed')
        det = detail if res!='Failed' or ov else detail+'; READ-BACK MISMATCH'
        rec={"platform":"google","account_id":u['account_id'],"unit_type":u['unit_type'],"unit":uid,"ad_ids":u['ad_ids'],"ad_names":u['ad_names'],"slot":c['slot'],"before":before[uid],"after_expected":c['new'],"after_live":al,"result":res,"new_entity_ids":"","detail":det}
        f.write(json.dumps(rec,ensure_ascii=False)+'\n')
        print(uid,res)
