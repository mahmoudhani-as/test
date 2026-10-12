# usage: python3 rec.py <json_file_with_list_of_records>
# each record: {ad_id, result, before, after_live, detail, new_entity_ids?}; appends one line per change to out_tiktok_6.jsonl
import json, sys
W='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/'
X=W+'tt6_work2/'
OUT=W+'out_tiktok_6.jsonl'
inp={u['unit']:u for u in json.load(open(W+'in_tiktok_6.json'))}
try: done=set(json.load(open(X+'recorded.json')))
except FileNotFoundError: done=set()
recs=json.load(open(sys.argv[1]))
with open(OUT,'a',encoding='utf-8') as f:
    for r in recs:
        u=inp[r['ad_id']]; ch=u['changes'][0]
        assert r['ad_id'] not in done, 'already recorded by this run: '+r['ad_id']
        assert r['result'] in ('Fixed','AlreadyFixed','Failed','Skipped','NotAttempted')
        if r['result'] in ('Fixed','AlreadyFixed'): assert r['after_live']==ch['new'], r['ad_id']
        line={"platform":"tiktok","account_id":u['account_id'],"unit_type":u['unit_type'],"unit":u['unit'],"ad_ids":u['ad_ids'],"ad_names":u['ad_names'],
              "slot":ch['slot'],"before":r['before'],"after_expected":ch['new'],"after_live":r['after_live'],"result":r['result'],
              "new_entity_ids":r.get('new_entity_ids',''),"detail":r['detail']}
        f.write(json.dumps(line,ensure_ascii=False)+'\n'); done.add(r['ad_id'])
        print('recorded', r['ad_id'], r['result'])
json.dump(sorted(done), open(X+'recorded.json','w'))
