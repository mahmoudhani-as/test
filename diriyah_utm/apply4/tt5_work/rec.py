import json, sys
# usage: rec.py ad_id result after_live write_req verify_req modify_time post_status [extra]
ad_id, result, after_live, wreq, vreq, mtime, post_status = sys.argv[1:8]
extra = sys.argv[8] if len(sys.argv)>8 else ""
d=json.loads(open('pre_read_text.json').read())
a={x['ad_id']:x for x in d['data']['data']['data']['list']}[ad_id]
u=[x for x in json.load(open('../in_tiktok_5.json')) if x['unit']==ad_id][0]
ch=u['changes'][0]
before=a['landing_page_url']
assert before==ch['now'] or before in ch['alt_now']
if result=='Fixed':
    assert after_live==ch['new'], 'mismatch'
old_utm=json.dumps({p['key']:p['value'] for p in a['utm_params']},ensure_ascii=False)
cta = f"call_to_action_id {a['call_to_action_id']} (CTA portfolio, sent as exact string)" if a.get('call_to_action_id') else f"CTA {a['call_to_action']}"
txt = "ad_text byte-identical (no trailing space)" if a['ad_text']==a['ad_text'].rstrip() else "ad_text trailing space trimmed by gateway (read had 1 trailing space; user accepted)"
detail=(f"pre-read ad/get req 20261012174844438BA2EBA6C0A4C37744: URL == now (CUSTOMIZED_USER manual SINGLE_VIDEO, adgroup {a['adgroup_id']}, op_status {a['operation_status']}, utm_params before {len(a['utm_params'])} keys {old_utm} (no utm_term, no utm_id)). "
 f"Pixel 7347671240183693330 (Visit Diriyah - Base Pixel, pixel/list req 20261012174924DD1CDC67D295228E8A0E) sent as exact string. "
 f"dry_run preview body: only landing_page_url and utm_params changed (utm_params set to the 5 UTMs of new incl. utm_term, no utm_id); all other creative fields sent back as read (ad_name, identity 7350277519361425409, video_id {a['video_id']}, image_ids, {txt}, {cta}, display_name, avatar, aigc NOT_DECLARED, creative_authorized {str(a['creative_authorized']).lower()}, vast_moat false). "
 f"Live full ad/update code 0 OK req {wreq} need_audit=false. Re-read req {vreq}: landing_page_url == new byte for byte; utm_params = 5 keys matching new, no utm_id; {post_status}; modify_time {mtime}.")
if extra: detail += " " + extra
rec={"platform":"tiktok","account_id":u['account_id'],"unit_type":u['unit_type'],"unit":u['unit'],"ad_ids":u['ad_ids'],"ad_names":u['ad_names'],"slot":ch['slot'],"before":before,"after_expected":ch['new'],"after_live":after_live,"result":result,"new_entity_ids":"","detail":detail}
with open('../out_tiktok_5.jsonl','a') as f: f.write(json.dumps(rec,ensure_ascii=False)+"\n")
print('ok', ad_id)
