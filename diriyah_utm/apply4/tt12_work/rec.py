import json
from urllib.parse import urlsplit, parse_qsl
IN='/tmp/claude-0/-home-user-test/0a7a4347-50ae-5891-a613-ee320c5ab4bb/scratchpad/diriyah_utm/apply4/in_tiktok_12.json'
OUT='/tmp/claude-0/-home-user-test/0a7a4347-50ae-5891-a613-ee320c5ab4bb/scratchpad/diriyah_utm/apply4/out_tiktok_12.jsonl'
UNITS={u['unit']:u for u in json.load(open(IN))}
def norm(u):
    s=urlsplit(u); return (s.scheme,s.netloc,s.path,s.fragment,sorted(parse_qsl(s.query,keep_blank_values=True)))
def unit(uid): return UNITS[uid]
def rec(uid,before,after,result,detail,neid=""):
    u=UNITS[uid]; c=u['changes'][0]
    if result=='Fixed': assert after==c['new'], 'after_live != new'
    if result=='AlreadyFixed': assert norm(before)==norm(c['new'])
    r={"platform":"tiktok","account_id":u['account_id'],"unit_type":u['unit_type'],"unit":uid,"ad_ids":u['ad_ids'],"ad_names":u['ad_names'],"slot":c['slot'],"before":before,"after_expected":c['new'],"after_live":after,"result":result,"new_entity_ids":neid,"detail":detail}
    with open(OUT,'a') as f: f.write(json.dumps(r,ensure_ascii=False)+"\n")
    print('ok',uid,result,'before==now' if before==c['now'] else ('before in alt' if before in c['alt_now'] else 'before other'))
