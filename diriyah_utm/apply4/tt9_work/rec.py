import json, sys
from urllib.parse import urlsplit, parse_qsl
W='/tmp/claude-0/-home-user-test/0a7a4347-50ae-5891-a613-ee320c5ab4bb/scratchpad/diriyah_utm/apply4/'
IN=W+'in_tiktok_9.json'; OUT=W+'out_tiktok_9.jsonl'
def norm(u):
    s=urlsplit(u); return (s.scheme,s.netloc,s.path,s.fragment,sorted(parse_qsl(s.query,keep_blank_values=True)))
# usage: rec.py <unit> <result> <before> <after_live> <detail> [new_entity_ids]
unit,result,before,after,detail=sys.argv[1:6]
neid=sys.argv[6] if len(sys.argv)>6 else ""
units={u['unit']:u for u in json.load(open(IN))}
u=units[unit]; c=u['changes'][0]
if result=='Fixed': assert after==c['new'], 'after_live != new byte for byte'
if result=='AlreadyFixed': assert norm(before)==norm(c['new'])
done=set()
try:
    for l in open(OUT): done.add(json.loads(l)['unit'])
except FileNotFoundError: pass
assert unit not in done, 'already recorded'
rec={"platform":"tiktok","account_id":u['account_id'],"unit_type":u['unit_type'],"unit":unit,"ad_ids":u['ad_ids'],"ad_names":u['ad_names'],"slot":c['slot'],"before":before,"after_expected":c['new'],"after_live":after,"result":result,"new_entity_ids":neid,"detail":detail}
with open(OUT,'a') as f: f.write(json.dumps(rec,ensure_ascii=False)+"\n")
print('ok',unit,result, 'before==now' if before==c['now'] else ('before in alt' if before in c['alt_now'] else 'before other'))
