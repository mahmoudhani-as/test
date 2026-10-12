import json, sys
# usage: rec.py ad_id result after_live detail [new_entity_ids]
W='/tmp/claude-0/-home-user-test/0a7a4347-50ae-5891-a613-ee320c5ab4bb/scratchpad/diriyah_utm/apply4/tt8_work'
OUT=W+'/../out_tiktok_8.jsonl'
ad_id, result, after_live, detail = sys.argv[1:5]
d=json.loads(open(W+'/pre_read_text.json').read())
a={x['ad_id']:x for x in d['data']['data']['data']['list']}[ad_id]
u=[x for x in json.load(open(W+'/../in_tiktok_8.json')) if x['unit']==ad_id][0]
ch=u['changes'][0]
before=a['landing_page_url']
if result=='Fixed': assert after_live==ch['new'], 'mismatch'
rec={"platform":"tiktok","account_id":u['account_id'],"unit_type":u['unit_type'],"unit":u['unit'],"ad_ids":u['ad_ids'],"ad_names":u['ad_names'],"slot":ch['slot'],"before":before,"after_expected":ch['new'],"after_live":after_live,"result":result,"new_entity_ids":(sys.argv[5] if len(sys.argv)>5 else ""),"detail":detail}
done=set()
try:
    for l in open(OUT): done.add(json.loads(l)['unit'])
except FileNotFoundError: pass
assert ad_id not in done, 'already recorded'
with open(OUT,'a') as f: f.write(json.dumps(rec,ensure_ascii=False)+"\n")
print('ok', ad_id, result)
