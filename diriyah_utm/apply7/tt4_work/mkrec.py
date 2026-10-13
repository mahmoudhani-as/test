# usage: python3 -I mkrec.py <ad_id> [--write] [extra note]
# Composes the record for an ad from decisions.json (+ for written ads: payload, resp_dry/resp_live, postcheck) and optionally appends it via rec.py.
import json, sys, subprocess
sys.path.insert(0,'/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply7/tt4_work')
from common import *
ad=sys.argv[1]; _a=[x for x in sys.argv[2:] if x!='--write']; note=_a[0] if _a else ''
D=json.load(open(T+'decisions.json'))[ad]
u=INPD[ad]; ch=u['changes'][0]; new=ch['new']
cls=D['cls']
ub=[k for k,v in D['utm_before']]
tn=D['text']
def desc():
    if cls=='CUSTOMIZED_USER':
        return (f"CUSTOMIZED_USER manual {D['ad_format']}, identity {D['identity_id']}, adgroup {D['adgroup_id']}, video_id {D['video_id']}, "
                f"{len(D['image_ids'] or [])} image, {D['cta_kind']} {D['cta']}")
    if cls=='BC_AUTH_TT_NO_ITEM':
        return (f"{D['ad_format']}, BC_AUTH_TT identity {D['identity_id']} / BC {D['bc']}, no tiktok_item_id (not a post), adgroup {D['adgroup_id']}, "
                f"music_id {D['music_id']}, {len(D['image_ids'] or [])} image, {D['cta_kind']} {D['cta']}, dark_post {D['dark_post']}, "
                f"creative_authorized {D['creative_authorized']}, enhancement list {D['enh']}")
    if cls=='SPARK_PUSH_HOLD':
        return (f"{D['ad_format']}, BC_AUTH_TT identity {D['identity_id']} / BC {D['bc']}, tiktok_item_id {D['item']}, video_id {D['video_id']}, adgroup {D['adgroup_id']}")
    return f"{cls} {D['ad_format']} identity {D['identity_id']}"
status=f"operation_status {D['op']}, secondary_status {D['sec']}, modify_time {D['modify_time']}"
utmdesc=(f"utm_params {len(ub)} keys {ub}" + (' incl. utm_id' if 'utm_id' in ub else ' (no utm_id)')) if ub else 'no utm_params'
if D['decision']=='Hold':
    rec={"ad_id":ad,"result":"NotAttempted","before":D['cur'],"after_live":D['cur'],
         "detail":(f"held for the user: Spark Push ad (BC_AUTH_TT, tiktok_item_id {D['item']}) - an API URL edit makes TikTok re-publish the post 30-60 min later "
                   f"and detach the ad from its original post (53 of 75 earlier writes); not written until the user decides. "
                   f"Pre-read ad/get req {D['rid']}: URL == now{'' if D['exact_now'] else ' (same params, other order)'} ({desc()}, {utmdesc}; {status}). No dry run or write sent.")}
elif D['decision']=='AlreadyFixed':
    rec={"ad_id":ad,"result":"AlreadyFixed","before":D['cur'],"after_live":D['url_field'],
         "detail":f"pre-read ad/get req {D['rid']}: live landing URL (incl. utm_params) already equals new ({desc()}, {utmdesc}; {status}). No write."}
elif D['decision']=='Skipped':
    rec={"ad_id":ad,"result":"Skipped","before":D['cur'],"after_live":D['url_field'],
         "detail":f"changed since plan: {D['cur']} (pre-read ad/get req {D['rid']}; {desc()}, {utmdesc}; {status}; problems: {D['probs']}). No write."}
else:
    P=json.load(open(T+f'payload_{ad}.json'))
    dry=json.loads(open(T+f'resp_dry_{ad}.json').read())
    live=json.loads(open(T+f'resp_live_{ad}.json').read())
    pc=json.load(open(T+f'postcheck_{ad}.json'))
    body=dry['data']['data']['request']['body']
    ld=live['data']['data']
    cr=P['creatives'][0]
    sent=[k for k in cr if k not in ('ad_id','landing_page_url','utm_params','tracking_pixel_id')]
    pv_same = body==P
    pv_trim_only=False
    if not pv_same:
        b2=json.loads(json.dumps(body)); b2['creatives'][0]['ad_text']=cr.get('ad_text')
        pv_trim_only = (b2==P and body['creatives'][0].get('ad_text')==(cr.get('ad_text') or '').rstrip())
    PX=json.load(open(PIXF))
    pxdesc=(f"Pixel {cr['tracking_pixel_id']} ({PX.get(cr['tracking_pixel_id'])}, pixel/list req {PX.get('_rid')}; ad/get shows it rounded {D['pixel']}) sent as exact string. " if cr.get('tracking_pixel_id') else 'no pixel. ')
    txtdesc=('ad_text as read' + (' incl. '+'/'.join(tn['nonprint']) if tn['nonprint'] else '') + (' (had a TRAILING SPACE)' if tn['trailing_ws'] else ' (no trailing space)'))
    utmw=(f"utm_params = the {len(cr.get('utm_params',[]))} UTMs of new (no utm_id)" if 'utm_params' in cr else 'ad had no utm_params, none added')
    after_status=f"operation_status {pc['status'][1][0]}, secondary_status {pc['status'][1][1]} (before {pc['status'][0][0]}/{pc['status'][0][1]})"
    other = 'none' if not pc['diffs'] else ('only ad_text trailing space trimmed' if pc['text_only_trim'] else repr(pc['diffs']))
    detail=(f"pre-read ad/get req {D['rid']}: URL == now{'' if D['exact_now'] else ' (same params, other order)'} ({desc()}, {utmdesc}, {status}). {pxdesc}"
            f"dry_run: call input == built payload; preview body {'== payload' if pv_same else ('== payload except ad_text trailing space trimmed by the gateway' if pv_trim_only else '!= payload (CHECK)')}; "
            f"creative fields sent as read ({', '.join(sent)}; {txtdesc}) with only landing_page_url = new and {utmw}; no tiktok_item_id / video_id added. "
            f"Live full ad/update code {ld.get('code')} {ld.get('message')} req {ld.get('request_id')} need_audit={(ld.get('data') or {}).get('need_audit')}. "
            f"Re-read ad/get req {pc['post_rid']}: landing_page_url {'==' if pc['url_ok'] else '!='} new byte for byte; "
            + (f"utm_params {len(pc['utm_keys_after'])} keys {'matching new' if pc['utm_ok'] else 'NOT matching new'}{'' if 'utm_id' not in pc['utm_keys_after'] else ' WITH utm_id'}; " if pc['had_utm'] else f"utm_params {'still none' if pc['utm_ok'] else 'NOW PRESENT'}; ")
            + f"keys {pc['nkeys'][0]} -> {pc['nkeys'][1]}, other fields changed: {other}; {after_status}; modify_time {pc['modify_time'][0]} -> {pc['modify_time'][1]}; "
            f"tiktok_item_id after: {pc['item_after']}."
            + (' ad_text trailing space trimmed by gateway (accepted by the user).' if tn['trailing_ws'] else ''))
    ok = pc['url_ok'] and pc['utm_ok'] and pc['eff_equals_new'] and pc['after_live']==new and (not pc['diffs'] or pc['text_only_trim'])
    rec={"ad_id":ad,"result":"Fixed" if ok else "Failed","before":D['cur'],"after_live":pc['after_live'],"detail":detail}
if note: rec['detail']+=' '+note
json.dump([rec],open(T+f'rec_{ad}.json','w'),ensure_ascii=False)
print(json.dumps(rec,ensure_ascii=False,indent=1))
if '--write' in sys.argv: subprocess.run(['python3','-I',T+'rec.py',T+f'rec_{ad}.json'],check=True)
