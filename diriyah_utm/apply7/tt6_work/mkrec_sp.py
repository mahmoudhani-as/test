# usage: python3 -I mkrec_sp.py <ad_id> [note] [--write]
# Composes the Fixed/Failed record for a written Smart+ ad from decisions.json, resp_dry/resp_live and postcheck; --write appends it via rec.py.
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
mats='; '.join(f"material {m['ad_material_id']} {m['fmt']} {m['identity_type']} identity {m['identity_id']}"+(f" / BC {m['bc']}" if m['bc'] else '')+(f" tiktok_item_id {m['item']}" if m['item'] else ' no tiktok_item_id')+(f" video {m['video']}" if m['video'] else '')+(f" {m['n_images']} image(s)" if m['n_images'] else '') for m in D['materials'])
ub=dict(D['utm_before'])
acs=[k for k in D['ac_keys'] if k!='utm_params']
detail=(f"pre-read smart_plus/ad/get req {D['rid']}: landing_page_url_list[{D['slot_index']}] == now (Upgraded Smart+ ad, {len(D['materials'])} material(s): {mats}; "
        f"ad_configuration.utm_params {'had %d keys %s'%(len(ub),json.dumps(ub,ensure_ascii=False)) if D['has_utm_params'] else 'absent'}; tracking_pixel_id {json.dumps(D['pixel'])} (string in smart_plus read); "
        f"operation_status {D['op']}, secondary_status {D['sec']}, modify_time {D['modify_time']}). "
        f"dry_run: call input and preview body == built payload ({body==P}): smart_plus_ad_id + landing_page_url_list (as read, only [{D['slot_index']}].landing_page_url = new) + ad_configuration sent back as read ({', '.join(acs)}) "
        f"with only utm_params = the {len(P['ad_configuration'].get('utm_params') or [])} UTMs of new (no utm_id); creative_list / ad_text_list / ad_name / status not sent. "
        f"Live smart_plus/ad/update code {ld['code']} {ld['message']} req {ld['request_id']}. "
        f"Re-read smart_plus/ad/get req {pc['post_rid']}: landing_page_url_list[{D['slot_index']}] {'==' if pc['url_ok'] else '!='} new byte for byte; ad_configuration.utm_params {len(pc['utm_keys_after'])} keys {'matching new' if pc['utm_ok'] else 'NOT matching new'}{'' if 'utm_id' not in pc['utm_keys_after'] else ' WITH utm_id'}; "
        f"other fields changed (ad_configuration, creative_list, ad_text_list, ad_name, adgroup, statuses): {pc['diffs'] if pc['diffs'] else 'none'}; post ids before {pc['items_before']} after {pc['items_after']}; "
        f"operation_status {pc['status'][1][0]}, secondary_status {pc['status'][1][1]} (before {pc['status'][0][0]}/{pc['status'][0][1]}); modify_time {pc['modify_time'][0]} -> {pc['modify_time'][1]}." + (' '+note if note else ''))
ok = pc['url_ok'] and pc['utm_ok'] and pc['eff_equals_new'] and pc['after_live']==new
rec=[{"ad_id":ad,"result":"Fixed" if ok else "Failed","before":D['cur'],"after_live":pc['after_live'],"detail":detail}]
json.dump(rec,open(T+f'rec_{ad}.json','w'),ensure_ascii=False)
print(json.dumps(rec,ensure_ascii=False,indent=1))
if '--write' in sys.argv: subprocess.run(['python3','-I',T+'rec.py',T+f'rec_{ad}.json'],check=True)
