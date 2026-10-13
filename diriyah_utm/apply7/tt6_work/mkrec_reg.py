# usage: python3 -I mkrec_reg.py <ad_id> [note] [--write]
# Composes the Fixed/Failed record for a written regular ad from decisions.json, resp_dry/resp_live and postcheck; --write appends it via rec.py.
import json, sys, subprocess
sys.path.insert(0,'/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply7/tt6_work')
from common import *
ad=sys.argv[1]; _a=[x for x in sys.argv[2:] if x!='--write']; note=_a[0] if _a else ''
D=json.load(open(T+'decisions.json'))[ad]
P=json.load(open(T+f'payload_{ad}.json'))
dry=json.loads(open(T+f'resp_dry_{ad}.json').read())
live=json.loads(open(T+f'resp_live_{ad}.json').read())
pc=json.load(open(T+f'postcheck_{ad}.json'))
new=INPD[ad]['changes'][0]['new']
body=dry['data']['data']['request']['body']
ld=live['data']['data']
cr=P['creatives'][0]
sent=[k for k in cr if k not in ('ad_id',)]
desc=f"CUSTOMIZED_USER manual {D['ad_format']}, identity {D['identity_id']}, adgroup {D['adgroup_id']}, video_id {D['video_id']}, {len(D['image_ids'] or [])} image, CTA {D['cta']}"
ub=[k for k,v in D['utm_before']]
tn=D['text']
txtdesc=('ad_text byte-identical' + (' incl. '+'/'.join(tn['nonprint']) if tn['nonprint'] else '') + (' (had a TRAILING SPACE: ad_text trailing space trimmed by gateway)' if tn['trailing_ws'] else ' (no trailing space)'))
detail=(f"pre-read ad/get req {D['rid']}: URL == now ({desc}, utm_params {len(ub)} keys {ub} (no utm_id), pixel shown rounded {D['pixel']}, "
        f"operation_status {D['op']}, secondary_status {D['sec']}, modify_time {D['modify_time']}). Pixel 7347671240183693330 (Visit Diriyah - Base Pixel, pixel/list req 20261012222006D041C4FD11D0938CEAE8) sent as exact string. "
        f"dry_run: call input and preview body == built payload ({body==P}); creative fields sent as read ({', '.join(k for k in sent if k not in ('landing_page_url','utm_params','tracking_pixel_id'))}; {txtdesc}) "
        f"with only landing_page_url = new and utm_params = the {len(cr.get('utm_params',[]))} UTMs of new (no utm_id); no tiktok_item_id sent. "
        f"Live full ad/update code {ld['code']} {ld['message']} req {ld['request_id']} need_audit={(ld.get('data') or {}).get('need_audit')}. "
        f"Re-read ad/get req {pc['post_rid']}: landing_page_url {'==' if pc['url_ok'] else '!='} new byte for byte; utm_params {len(pc['utm_keys_after'])} keys {'matching new' if pc['utm_ok'] else 'NOT matching new'}{'' if 'utm_id' not in pc['utm_keys_after'] else ' WITH utm_id'}; "
        f"same {pc['nkeys'][1]} keys, other fields changed: {pc['diffs'] if pc['diffs'] else 'none'}; operation_status {pc['status'][1][0]}, secondary_status {pc['status'][1][1]} (before {pc['status'][0][0]}/{pc['status'][0][1]}); "
        f"modify_time {pc['modify_time'][0]} -> {pc['modify_time'][1]}." + (' '+note if note else ''))
ok = pc['url_ok'] and pc['utm_ok'] and pc['eff_equals_new'] and pc['after_live']==new
rec=[{"ad_id":ad,"result":"Fixed" if ok else "Failed","before":D['cur'],"after_live":pc['after_live'],"detail":detail}]
json.dump(rec,open(T+f'rec_{ad}.json','w'),ensure_ascii=False)
print(json.dumps(rec,ensure_ascii=False,indent=1))
if '--write' in sys.argv: subprocess.run(['python3','-I',T+'rec.py',T+f'rec_{ad}.json'],check=True)
