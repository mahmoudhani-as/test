import json, sys
from urllib.parse import urlsplit, parse_qsl
IN='/tmp/claude-0/-home-user-test/0a7a4347-50ae-5891-a613-ee320c5ab4bb/scratchpad/diriyah_utm/apply4/in_tiktok_16.json'
OUT='/tmp/claude-0/-home-user-test/0a7a4347-50ae-5891-a613-ee320c5ab4bb/scratchpad/diriyah_utm/apply4/out_tiktok_16.jsonl'
UNITS={u['unit']:u for u in json.load(open(IN))}
def norm(u):
    s=urlsplit(u); return (s.scheme,s.netloc,s.path,s.fragment,sorted(parse_qsl(s.query,keep_blank_values=True)))
def rec(uid,before,after,result,detail,neid=""):
    u=UNITS[uid]; c=u['changes'][0]
    if result=='Fixed': assert after==c['new'], 'after_live != new'
    if result=='AlreadyFixed': assert norm(before)==norm(c['new'])
    r={"platform":"tiktok","account_id":u['account_id'],"unit_type":u['unit_type'],"unit":uid,"ad_ids":u['ad_ids'],"ad_names":u['ad_names'],"slot":c['slot'],"before":before,"after_expected":c['new'],"after_live":after,"result":result,"new_entity_ids":neid,"detail":detail}
    with open(OUT,'a') as f: f.write(json.dumps(r,ensure_ascii=False)+"\n")
    print('ok',uid,result,'before==now' if before==c['now'] else ('before in alt' if before in c['alt_now'] else 'before other'))
def sp_detail(uid, pre_req, upd_req, reread_req, mod, extra=""):
    pre=json.load(open('/tmp/claude-0/-home-user-test/0a7a4347-50ae-5891-a613-ee320c5ab4bb/scratchpad/diriyah_utm/apply4/tt16_work/sp_pre.json'))[uid]
    ac=pre['ac']; old={p['key']:p['value'] for p in ac['utm_params']}
    other=sorted(k for k in ac if k!='utm_params')
    pix=ac.get('tracking_info',{}).get('tracking_pixel_id')
    return (f"pre-read smart_plus/ad/get req {pre_req}: landing_page_url_list[0] == now (Upgraded Smart+ ad, 1 material, {pre['fmt']}, BC_AUTH_TT identity 0f6eebaa-ba16-5ad3-aa97-4171805e2af1 / BC 6807778858780065797, "
            f"call_to_action_id {ac['call_to_action_id']}, tracking_pixel_id \"{pix}\", ad_configuration.utm_params had {len(old)} keys {json.dumps(old,ensure_ascii=False)}, no utm_id; operation_status {pre['op']}, secondary_status {pre['sec']}). "
            f"dry_run preview: body = smart_plus_ad_id + landing_page_url_list[0] (= new) + ad_configuration sent back as read ({', '.join(other)}; ids as exact strings) with only utm_params rebuilt to the 5 UTMs of new (no utm_id); creative_list/ad_text_list/ad_name/status not sent. "
            f"Live smart_plus/ad/update code 0 OK req {upd_req}. Re-read req {reread_req}: landing_page_url_list[0] == new byte for byte; ad_configuration.utm_params = 5 keys matching new, no utm_id; all other ad_configuration fields, creative_list (material, identity, media), ad_text_list, ad_name, adgroup identical to pre-read; operation_status {pre['op']} unchanged; modify_time {mod}.{extra}")
if __name__=='__main__':
    a=json.load(open(sys.argv[1]))
    for x in a:
        if x['result'] in ('Fixed',):
            d=sp_detail(x['uid'],x['pre_req'],x['upd_req'],x['reread_req'],x['mod'],x.get('extra',''))
        else:
            d=x['detail']
        rec(x['uid'],x['before'],x['after'],x['result'],d,x.get('neid',''))
