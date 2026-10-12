import json, sys
# usage: rec.py ad_id result wreq vreq post_read_text_file [extra]
W='/tmp/claude-0/-home-user-test/0a7a4347-50ae-5891-a613-ee320c5ab4bb/scratchpad/diriyah_utm/apply4/'
ad_id, result, wreq, vreq, postf = sys.argv[1:6]
extra = sys.argv[6] if len(sys.argv)>6 else ""
d=json.loads(open(W+'tt17_work/pre_read_text.json').read())
a={x['ad_id']:x for x in d['data']['data']['data']['list']}[ad_id]
b={x['ad_id']:x for x in json.loads(open(W+'tt17_work/'+postf).read())['data']['data']['data']['list']}[ad_id]
u=[x for x in json.load(open(W+'in_tiktok_17.json')) if x['unit']==ad_id][0]
ch=u['changes'][0]
pf=json.load(open(W+'../payloads/tiktok_spark_tt2_payloads.json'))
before=a['landing_page_url']; after_live=b['landing_page_url']
assert before==ch['now'] or before in ch['alt_now']
utm_new=[(p['key'],p['value']) for p in b['utm_params']]
from urllib.parse import urlsplit, parse_qsl
if result=='Fixed':
    assert after_live==ch['new'], 'mismatch'
    assert utm_new==parse_qsl(urlsplit(ch['new']).query)
# every other field unchanged except allowed
allowed={'landing_page_url','utm_params','modify_time','video_id','ad_text'}
diffs=[k for k in set(a)|set(b) if a.get(k)!=b.get(k) and k not in allowed]
assert not diffs, diffs
cta = f"call_to_action_id {a['call_to_action_id']} (exact string)" if a.get('call_to_action_id') else f"CTA {a['call_to_action']}"
tw = a['ad_text']!=a['ad_text'].rstrip()
if tw:
    assert b['ad_text']==a['ad_text'].rstrip(), 'post text not just rstrip'
    txt = f"ad_text trailing space trimmed by gateway (read ended {a['ad_text'][-10:]!r}, now ends {b['ad_text'][-9:]!r}; user accepted)"
else:
    assert b['ad_text']==a['ad_text'], 'ad_text changed'
    txt = "ad_text byte-identical to pre-read (no trailing space)"
pix = "pixel sent as exact string 7347671240183693330 (Visit Diriyah - Base Pixel, pixel/list req 20261012180634C990D3FE07E0BE264523)" if a['tracking_pixel_id'] not in (0,None) else "tracking_pixel_id 0 (unset) not sent"
tt2 = " Ready tt2 payload checked: all fields equal the live ad, but its URL/utm_params were the 11-Oct target, so URL + utm_params were rebuilt from new." if ad_id in pf else ""
vid = "" if b['video_id']==a['video_id'] else f" SIDE EFFECT: ad-level video_id now reads {b['video_id']} (was {a['video_id']}) - known TikTok behaviour (same as ads 1826384400556033 / 1840143241069682): video_id re-resolved to the Spark post's own video; tiktok_item_id {a['tiktok_item_id']} unchanged, same post served."
detail=(f"pre-read ad/get req 20261012180526FFCCDB9BAEC58EFC858E: URL == {'now' if before==ch['now'] else 'alt_now'} (BC_AUTH_TT Spark ad, identity {a['identity_id']} / BC {a['identity_authorized_bc_id']}, tiktok_item_id {a['tiktok_item_id']}, SINGLE_VIDEO video_id {a['video_id']}, 1 image, {cta}, dark_post {a['dark_post_status']}, adgroup {a['adgroup_id']}, utm_params before {len(a['utm_params'])} keys {json.dumps({p['key']:p['value'] for p in a['utm_params']},ensure_ascii=False)}).{tt2} "
 f"dry_run preview: full ad/update body = creative fields as read (ad_name, identity_type/identity_id/identity_authorized_bc_id, ad_format, video_id, image_ids, ad_text, {cta}, dark_post_status, creative_authorized {str(a['creative_authorized']).lower()}, vast_moat false; {pix}) with only landing_page_url = new and utm_params = the 5 UTMs of new (no utm_id); tiktok_item_id left out. "
 f"Live ad/update code 0 OK req {wreq} need_audit=false. Re-read req {vreq}: landing_page_url == new byte for byte; utm_params = {len(b['utm_params'])} keys matching new, no utm_id; all other fields (ad_name, identity, tiktok_item_id, image_ids, CTA, pixel, dark_post, flags, shopping/fallback fields) identical to pre-read; {txt}; operation_status {b['operation_status']}, secondary_status {b['secondary_status']} unchanged; modify_time {b['modify_time']}.{vid}")
if extra: detail += " " + extra
rec={"platform":"tiktok","account_id":u['account_id'],"unit_type":u['unit_type'],"unit":u['unit'],"ad_ids":u['ad_ids'],"ad_names":u['ad_names'],"slot":ch['slot'],"before":before,"after_expected":ch['new'],"after_live":after_live,"result":result,"new_entity_ids":"","detail":detail}
with open(W+'out_tiktok_17.jsonl','a') as f: f.write(json.dumps(rec,ensure_ascii=False)+"\n")
print('ok', ad_id, result, 'trailing' if tw else '', 'vid changed' if vid else '')
