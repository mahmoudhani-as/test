# usage: python3 -I mkrec.py <ad_id> [--note "<text>"] [--prenote "<text>"] [--write]
# Composes the Fixed/Failed record for a written ad from decisions.json, resp_dry/resp_live and postcheck, prints it, and appends it with --write.
import json, sys
sys.path.insert(0,'/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply7/tt3_work')
from common import *
args=sys.argv[1:]; ad=args[0]
def opt(name):
    return args[args.index(name)+1] if name in args else ''
note=opt('--note'); prenote=opt('--prenote')
D=json.load(open(T+'decisions.json'))[ad]
P=json.load(open(T+f'payload_{ad}.json'))
dry=json.loads(open(T+f'resp_dry_{ad}.json',encoding='utf-8').read())
live=json.loads(open(T+f'resp_live_{ad}.json',encoding='utf-8').read())
pc=json.load(open(T+f'postcheck_{ad}.json'))
u=INPD[ad]; ch=u['changes'][0]; new=ch['new']
body=dry['data']['data']['request']['body']
ld=live['data']['data']
cr=P['creatives'][0]
sent=[k for k in cr if k not in ('ad_id','landing_page_url','utm_params','tracking_pixel_id')]
cls=D['cls']
if cls=='CUSTOMIZED_USER':
    desc=(f"CUSTOMIZED_USER manual {D['ad_format']} (identity {D['identity_id']}, no tiktok_item_id), adgroup {D['adgroup_id']}, video_id {D['video_id']}, "
          f"{len(D['image_ids'] or [])} image, CTA {D['cta']}")
else:
    desc=(f"{D['ad_format']}, BC_AUTH_TT identity {D['identity_id']} / BC {D['bc']}, no tiktok_item_id (not a post, so not a Spark Push hold), adgroup {D['adgroup_id']}, "
          f"music_id {D['music_id']}, {len(D['image_ids'] or [])} image, {D['cta_kind']} {D['cta']}, dark_post {D['dark_post']}, creative_authorized {D['creative_authorized']}, "
          f"enhancement list {D['enh']}{' (not sent)' if D['enh'] in ([],'<absent>') else ' (sent as read)'}")
ub=[k for k,v in D['utm_before']]
tn=D['text']
txt=('ad_text byte-identical' + (' incl. '+'/'.join(tn['nonprint']) if tn['nonprint'] else '') +
     (' (had a TRAILING SPACE: ad_text trailing space trimmed by gateway)' if tn['trailing_ws'] else ' (no edge whitespace)'))
px=cr.get('tracking_pixel_id')
pxd=(f"Pixel shown rounded {D['pixel']} sent as exact string {px} (Visit Diriyah - Base Pixel, pixel/list req 20261012222006D041C4FD11D0938CEAE8; pixel/list errored with TikTok 51010 during this run). "
     if px else "No pixel on the ad; none sent. ")
nutm=len(cr.get('utm_params',[]))
detail=((prenote+' ' if prenote else '')+
        f"Pre-read ad/get req {D['rid']}: URL == now ({desc}; utm_params {len(ub)} keys {ub}, no utm_id; {D['op']} / {D['sec']}; modify_time {D['modify_time']}). "
        + pxd +
        f"dry_run: call input and preview body == built payload ({body==P}); creative fields sent as read ({', '.join(sent)}; {txt}) "
        f"with only landing_page_url = new" + (f" and utm_params = the {nutm} UTMs of new (no utm_id)" if nutm else "; no utm_params on the ad, none added") +
        "; no tiktok_item_id/video_id change. "
        f"Live full ad/update code {ld['code']} {ld['message']} req {ld['request_id']} need_audit={ld['data'].get('need_audit')}. "
        f"Re-read ad/get req {pc['post_rid']}: landing_page_url {'==' if pc['url_ok'] else '!='} new byte for byte; "
        + (f"utm_params {len(pc['utm_keys_after'])} keys {'matching new' if pc['utm_ok'] else 'NOT matching new'}{'' if 'utm_id' not in pc['utm_keys_after'] else ' WITH utm_id'}; " if nutm else f"utm_params {'still none' if pc['utm_ok'] else 'CHANGED'}; ")
        + f"tiktok_item_id after: {pc['item_after']}; same {pc['nkeys'][1]} keys (before {pc['nkeys'][0]}), other fields changed: {pc['diffs'] if pc['diffs'] else 'none'}; "
        f"operation_status {pc['status'][1][0]}, secondary_status {pc['status'][1][1]} (before {pc['status'][0][0]}/{pc['status'][0][1]}); "
        f"modify_time {pc['modify_time'][0]} -> {pc['modify_time'][1]}." + (' '+note if note else ''))
ok = pc['url_ok'] and pc['utm_ok'] and pc['eff_equals_new'] and pc['after_live']==new
rec={"platform":"tiktok","account_id":u['account_id'],"unit_type":u['unit_type'],"unit":u['unit'],"ad_ids":u['ad_ids'],"ad_names":u['ad_names'],"slot":ch['slot'],
     "before":D['cur'],"after_expected":new,"after_live":pc['after_live'],"result":"Fixed" if ok else "Failed","new_entity_ids":"","detail":detail}
print(json.dumps(rec,ensure_ascii=False,indent=1))
if '--write' in args:
    done=set()
    for l in open(OUT,encoding='utf-8'):
        if l.strip(): done.add(json.loads(l)['unit'])
    assert ad not in done, 'already recorded'
    append_records([rec])
    print('APPENDED', ad, rec['result'])
