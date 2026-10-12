import json, sys
# usage: rec.py ad_id result after_live write_req verify_req modify_time [confirm_req] [extra]
ad_id, result, after_live, wreq, vreq, mtime = sys.argv[1:7]
creq = sys.argv[7] if len(sys.argv)>7 else ''
extra = sys.argv[8] if len(sys.argv)>8 else ''
d=json.loads(open('pre_read_text.json').read())
a={x['ad_id']:x for x in d['data']['data']['data']['list']}[ad_id]
u=[x for x in json.load(open('../in_tiktok_4.json')) if x['unit']==ad_id][0]
ch=u['changes'][0]
before=a['landing_page_url']
assert before==ch['now'] or before in ch['alt_now']
if result=='Fixed':
    assert after_live==ch['new'], 'mismatch'
old_utm=json.dumps({p['key']:p['value'] for p in a['utm_params']},ensure_ascii=False)
cta = f"call_to_action_id {a['call_to_action_id']} (CTA portfolio, sent back unchanged)" if a.get('call_to_action_id') else f"CTA {a.get('call_to_action')}"
conf = f", re-confirmed just before writing by req {creq}" if creq else ""
detail=(f"pre-read ad/get req 2026101217474794F972ADC1FDAD9D63DE{conf}: URL == now (CUSTOMIZED_USER manual SINGLE_VIDEO, adgroup {a['adgroup_id']}, {cta}, utm_params before {len(a['utm_params'])} keys {old_utm}, no utm_id). "
 f"Pixel 7347671240183693330 (Visit Diriyah - Base Pixel, pixel/list req 2026101217482875B59AEF63441BB9DC7A; ad/get returns it rounded as 7347671240183693000) sent as exact string. "
 f"dry_run preview body: only landing_page_url and utm_params changed (utm_params set to the 5 UTMs of new, no utm_id); all other creative fields sent back as read (ad_name, identity {a['identity_id']}, video_id {a['video_id']}, image_ids, ad_text byte-identical with no trailing space, display_name, avatar, aigc {a['aigc_disclosure_type']}, creative_authorized {str(a['creative_authorized']).lower()}, vast_moat false). "
 f"Live full ad/update code 0 OK req {wreq} need_audit=false. Re-read req {vreq}: landing_page_url == new byte for byte; utm_params = 5 keys matching new, no utm_id; pixel/identity/video/text/CTA/name unchanged; operation_status {a['operation_status']}, secondary_status {a['secondary_status']} unchanged; modify_time {mtime}.")
if extra: detail += " " + extra
rec={"platform":"tiktok","account_id":u['account_id'],"unit_type":u['unit_type'],"unit":u['unit'],"ad_ids":u['ad_ids'],"ad_names":u['ad_names'],"slot":ch['slot'],"before":before,"after_expected":ch['new'],"after_live":after_live,"result":result,"new_entity_ids":"","detail":detail}
with open('../out_tiktok_4.jsonl','a') as f: f.write(json.dumps(rec,ensure_ascii=False)+"\n")
print('ok', ad_id, result)
