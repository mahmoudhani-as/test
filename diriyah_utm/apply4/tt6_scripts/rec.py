import json, sys
# usage: rec.py ad_id result after_live write_req verify_req modify_time diffsummary [extra]
W='/tmp/claude-0/-home-user-test/0a7a4347-50ae-5891-a613-ee320c5ab4bb/scratchpad/diriyah_utm/apply4/'
ad_id, result, after_live, wreq, vreq, mtime, diffs = sys.argv[1:8]
extra = sys.argv[8] if len(sys.argv)>8 else ''
d=json.loads(open(W+'tt6_work/pre_read_text.json').read())
a={x['ad_id']:x for x in d['data']['data']['data']['list']}[ad_id]
u=[x for x in json.load(open(W+'in_tiktok_6.json')) if x['unit']==ad_id][0]
ch=u['changes'][0]
before=a['landing_page_url']
assert before==ch['now'] or before in ch['alt_now']
which = 'now' if before==ch['now'] else 'alt_now'
if result=='Fixed':
    assert after_live==ch['new'], 'mismatch'
old_utm=json.dumps({p['key']:p['value'] for p in (a.get('utm_params') or [])},ensure_ascii=False)
cta = f"call_to_action_id {a['call_to_action_id']} (CTA portfolio, sent back as exact string)" if a.get('call_to_action_id') else f"CTA {a.get('call_to_action')}"
txt=a.get('ad_text') or ''
trail = txt!=txt.rstrip()
if a['identity_type']=='CUSTOMIZED_USER':
    kind=f"CUSTOMIZED_USER manual SINGLE_VIDEO, identity {a['identity_id']}, video_id {a['video_id']}"
    sent=f"ad_name, identity, ad_format, video_id, image_ids, ad_text, {('call_to_action_id' if a.get('call_to_action_id') else 'call_to_action')}, display_name, avatar, aigc {a.get('aigc_disclosure_type')}, creative_authorized {str(a['creative_authorized']).lower()}, vast_moat false" + (f", creative_auto_enhancement_strategy_list {a['creative_auto_enhancement_strategy_list']}" if a.get('creative_auto_enhancement_strategy_list') else '')
else:
    kind=f"AUTH_CODE Spark Ad (Spark Pull: identity {a['identity_id']}, tiktok_item_id {a['tiktok_item_id']}, no video_id/image_ids, ad_text empty)"
    sent=f"ad_name, identity_type/identity_id and tiktok_item_id sent back unchanged as exact strings, ad_format, promotional_music_disabled {str(a.get('promotional_music_disabled')).lower()}, {('call_to_action_id' if a.get('call_to_action_id') else 'call_to_action')}, creative_authorized {str(a['creative_authorized']).lower()}, vast_moat false (empty ad_text, display_name, app_name, avatar not sent)"
pix = "pixel 7347671240183693330 (Visit Diriyah - Base Pixel, pixel/list req 202610121801039437A1BDC2B1FFD2EF8C; ad/get shows it rounded as 7347671240183693000) sent as exact string" if a.get('tracking_pixel_id') not in (0,None) else "tracking_pixel_id 0 (no pixel) so not sent"
txtnote = "ad_text trailing space trimmed by gateway (read had a trailing space; user accepted 'apply everything')" if trail else "ad_text byte-identical (no leading/trailing whitespace)"
if a['identity_type']!='CUSTOMIZED_USER': txtnote="ad_text empty (Spark post caption), not sent"
detail=(f"pre-read ad/get req 20261012175847D4A25FFC2E5CB76EF115: URL == {which} ({kind}, adgroup {a['adgroup_id']}, {cta}, op_status {a['operation_status']}, modify_time {a['modify_time']}, utm_params before {len(a.get('utm_params') or [])} keys {old_utm}). "
 f"{pix}. dry_run preview body: only landing_page_url and utm_params changed (utm_params set to the 5 UTMs of new, no utm_id); other fields sent back as read ({sent}); {txtnote}. "
 f"Live full ad/update code 0 OK req {wreq} need_audit=false. Re-read req {vreq}: landing_page_url == new byte for byte; utm_params = 5 keys matching new, no utm_id; {diffs}; modify_time {mtime}.")
if extra: detail += " " + extra
rec={"platform":"tiktok","account_id":u['account_id'],"unit_type":u['unit_type'],"unit":u['unit'],"ad_ids":u['ad_ids'],"ad_names":u['ad_names'],"slot":ch['slot'],"before":before,"after_expected":ch['new'],"after_live":after_live,"result":result,"new_entity_ids":"","detail":detail}
with open(W+'out_tiktok_6.jsonl','a') as f: f.write(json.dumps(rec,ensure_ascii=False)+"\n")
print('ok', ad_id, result)
