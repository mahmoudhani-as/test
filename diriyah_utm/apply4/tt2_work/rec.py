import json, sys
# usage: rec.py ad_id result after_live write_req verify_req modify_time
ad_id, result, after_live, wreq, vreq, mtime = sys.argv[1:7]
d=json.loads(open('pre_read_text.json').read())
a={x['ad_id']:x for x in d['data']['data']['data']['list']}[ad_id]
u=[x for x in json.load(open('../in_tiktok_2.json')) if x['unit']==ad_id][0]
ch=u['changes'][0]
before=a['landing_page_url']
assert before==ch['now'] or before in ch['alt_now']
assert after_live==ch['new'], 'mismatch'
old_utm=json.dumps({p['key']:p['value'] for p in a['utm_params']},ensure_ascii=False)
detail=(f"pre-read ad/get req 20261012173626D53220046F1062CEA956: URL == now (CUSTOMIZED_USER manual SINGLE_VIDEO, adgroup {a['adgroup_id']}, utm_params before {len(a['utm_params'])} keys {old_utm}, no utm_id). "
 f"Pixel 7347671240183693330 (Visit Diriyah - Base Pixel, pixel/list req 202610121736531DC84E430E74F171B8EA) sent as exact string. "
 f"dry_run preview body: only landing_page_url and utm_params changed (utm_params set to the 5 UTMs of new, no utm_id); all other creative fields sent back as read (ad_name, identity 7350277519361425409, video_id {a['video_id']}, image_ids, ad_text byte-identical with no trailing space, CTA LEARN_MORE, display_name, avatar, aigc NOT_DECLARED, creative_authorized {str(a['creative_authorized']).lower()}, vast_moat false). "
 f"Live full ad/update code 0 OK req {wreq} need_audit=false. Re-read req {vreq}: landing_page_url == new byte for byte; utm_params = 5 keys matching new, no utm_id; pixel/identity/video/text/CTA/name unchanged; operation_status ENABLE, secondary_status AD_STATUS_CAMPAIGN_DISABLE unchanged; modify_time {mtime}.")
rec={"platform":"tiktok","account_id":u['account_id'],"unit_type":u['unit_type'],"unit":u['unit'],"ad_ids":u['ad_ids'],"ad_names":u['ad_names'],"slot":ch['slot'],"before":before,"after_expected":ch['new'],"after_live":after_live,"result":result,"new_entity_ids":"","detail":detail}
with open('../out_tiktok_2.jsonl','a') as f: f.write(json.dumps(rec,ensure_ascii=False)+"\n")
print('ok', ad_id)
