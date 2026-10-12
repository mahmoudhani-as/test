import json,os
D='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
OUT=D+'/apply6/out_google_3.jsonl'
def unit_by_id():
    d=json.load(open(D+'/apply6/in_google_3.json'))
    return {u['unit']:u for u in d}
def done_units():
    s=set()
    if os.path.exists(OUT):
        for line in open(OUT):
            line=line.strip()
            if line: s.add(json.loads(line)['unit'])
    return s
def append(u,c,before,after_live,result,detail,new_entity_ids=""):
    if u['unit'] in done_units():
        raise SystemExit('already recorded '+u['unit'])
    rec={"platform":u['platform'],"account_id":u['account_id'],"unit_type":u['unit_type'],"unit":u['unit'],
         "ad_ids":u['ad_ids'],"ad_names":u['ad_names'],"slot":c['slot'],"before":before,
         "after_expected":c['new'],"after_live":after_live,"result":result,"new_entity_ids":new_entity_ids,"detail":detail}
    with open(OUT,'a') as f:
        f.write(json.dumps(rec,ensure_ascii=False)+'\n')
    return rec
