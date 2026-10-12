import json, sys
from urllib.parse import urlsplit, parse_qsl
BASE='/tmp/claude-0/-home-user-test/0a7a4347-50ae-5891-a613-ee320c5ab4bb/scratchpad/diriyah_utm/apply4/'
IN=json.load(open(BASE+'in_tiktok_11.json'))
OUT=BASE+'out_tiktok_11.jsonl'
def unit(uid):
    for u in IN:
        if u['unit']==uid: return u
    raise KeyError(uid)
def rec(uid, before, after_live, result, detail, new_ids=""):
    u=unit(uid); c=u['changes'][0]
    if result=='Fixed':
        assert after_live==c['new'], (after_live, c['new'])
    r={"platform":"tiktok","account_id":u['account_id'],"unit_type":u['unit_type'],"unit":u['unit'],
       "ad_ids":u['ad_ids'],"ad_names":u['ad_names'],"slot":c['slot'],"before":before,
       "after_expected":c['new'],"after_live":after_live,"result":result,"new_entity_ids":new_ids,"detail":detail}
    with open(OUT,'a') as f: f.write(json.dumps(r, ensure_ascii=False)+"\n")
    print("ok", uid, result)
if __name__=='__main__':
    a=json.loads(sys.stdin.read())
    rec(a['unit'], a['before'], a['after_live'], a['result'], a['detail'], a.get('new_entity_ids',''))
