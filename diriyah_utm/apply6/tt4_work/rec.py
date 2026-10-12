# Writes one result line per change of in_tiktok_4.json from the saved live pre-read (pre_all.json).
import json
from urllib.parse import urlsplit, parse_qsl
W='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/'
OUT=W+'out_tiktok_4.jsonl'
inp=json.load(open(W+'in_tiktok_4.json'))
pre=json.load(open(W+'tt4_work/pre_all.json'))
done=set()
try:
    for line in open(OUT, encoding='utf-8'):
        if line.strip(): done.add((json.loads(line)['unit'], json.loads(line)['slot']))
except FileNotFoundError:
    pass
def same_url(x,y):
    sx,sy=urlsplit(x),urlsplit(y)
    return (sx.scheme,sx.netloc,sx.path,sx.fragment)==(sy.scheme,sy.netloc,sy.path,sy.fragment) and sorted(parse_qsl(sx.query,keep_blank_values=True))==sorted(parse_qsl(sy.query,keep_blank_values=True))
EXTRA={'1826384400556033': " Evidence of the re-publish on this ad: it was written on 11-Oct (apply2, ad/update req 20261011195250095434D43DBC49B7EE57) and its 11-Oct read-back showed tiktok_item_id 7481276898408975624; it now reads tiktok_item_id 7695385229300600070 with modify_time 2026-10-11 12:25:04, so it is no longer on its original post."}
lines=[]
for u in inp:
    a=pre[u['unit']]
    assert a['ad_id']==u['unit'] and a['advertiser_id']==u['account_id'] and a['ad_name']==u['ad_names'][0]
    for ch in u['changes']:
        assert ch['slot']=='ad.landing_page_url'
        if (u['unit'],ch['slot']) in done: continue
        cur=a['landing_page_url']
        is_push = a['identity_type']=='BC_AUTH_TT' and bool(a.get('tiktok_item_id'))
        assert is_push, u['unit']
        if cur==ch['new'] or same_url(cur,ch['new']):
            state='AlreadyFixed'
        elif cur==ch['now']:
            state='now'
        elif cur in ch['alt_now']:
            state='alt_now'
        else:
            state='other'
        assert state in ('now','alt_now'), (u['unit'], state)   # all 20 read == plan "now"
        up=a.get('utm_params') or []
        upd=', '.join(f"{x['key']}={x['value']}" for x in up)
        detail=(f"held for the user: Spark Push ad (BC_AUTH_TT, tiktok_item_id {a['tiktok_item_id']}) - an API URL edit makes TikTok re-publish the post 30-60 min later and detach the ad from its original post (53 of 75 earlier writes); not written until the user decides. "
                f"Pre-read ad/get req {a['_req']}: landing_page_url == plan '{state}' value byte for byte; identity {a['identity_id']} / BC {a.get('identity_authorized_bc_id')}; "
                f"ad_format {a['ad_format']}, video_id {a.get('video_id')}, "
                f"{'call_to_action_id '+a['call_to_action_id'] if a.get('call_to_action_id') else 'call_to_action '+str(a.get('call_to_action'))}; "
                f"operation_status {a['operation_status']} / {a['secondary_status']}; modify_time {a['modify_time']}; "
                f"separately stored utm_params ({len(up)} keys, unchanged): {upd}. No dry run or live write was sent.")
        detail+=EXTRA.get(u['unit'],'')
        lines.append({"platform":"tiktok","account_id":u['account_id'],"unit_type":u['unit_type'],"unit":u['unit'],"ad_ids":u['ad_ids'],"ad_names":u['ad_names'],
            "slot":ch['slot'],"before":cur,"after_expected":ch['new'],"after_live":cur,"result":"NotAttempted","new_entity_ids":"","detail":detail})
with open(OUT,'a',encoding='utf-8') as f:
    for l in lines:
        f.write(json.dumps(l,ensure_ascii=False)+'\n')
print('appended',len(lines))
