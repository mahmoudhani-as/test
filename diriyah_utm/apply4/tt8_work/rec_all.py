import json, subprocess
W='/tmp/claude-0/-home-user-test/0a7a4347-50ae-5891-a613-ee320c5ab4bb/scratchpad/diriyah_utm/apply4/tt8_work'
pre={a['ad_id']:a for a in json.loads(open(W+'/pre_read_text.json').read())['data']['data']['data']['list']}
post={a['ad_id']:a for a in json.loads(open(W+'/post_read_text.json').read())['data']['data']['data']['list']}
inp=json.load(open(W+'/../in_tiktok_8.json'))
writes={}
for l in open(W+'/writes.txt'):
    p=l.split(); writes[p[0]]=p[1]
VI='20261012181923 5AE8EBF2B436F1238794'.replace(' ','')
done=set(json.loads(l)['unit'] for l in open(W+'/../out_tiktok_8.jsonl'))
for u in inp:
    i=u['unit']
    if i in done: continue
    a=pre[i]; b=post[i]; new=u['changes'][0]['new']
    assert b['landing_page_url']==new
    others=[k for k in sorted(set(a)|set(b)) if k not in ('landing_page_url','utm_params','modify_time') and a.get(k,'<absent>')!=b.get(k,'<absent>')]
    ub=json.dumps({p['key']:p['value'] for p in a['utm_params']},ensure_ascii=False)
    it=a['identity_type']
    if it=='BC_AUTH_TT':
        head=(f"Pre-read ad/get req 2026101218115324649A5FA30B9C3D8810 (re-checked req 202610121814002930075D728D23E77193 just before the write, unchanged): URL == now (BC_AUTH_TT Spark ad, identity 7d136a20-71e2-5fb6-9927-ad76b915fac7 / BC 6846326855419559942, tiktok_item_id {a['tiktok_item_id']}, adgroup {a['adgroup_id']}, op_status {a['operation_status']}, modify_time {a['modify_time']}, utm_params before {len(a['utm_params'])} keys {ub}). "
              f"dry_run preview body: creative fields sent back as read (ad_name, identity + BC id, ad_format, video_id {a['video_id']}, image_ids, ad_text, CTA {a['call_to_action']}, dark_post {a['dark_post_status']}, creative_authorized {str(a['creative_authorized']).lower()}, vast_moat false"
              + (f", creative_auto_enhancement_strategy_list {a['creative_auto_enhancement_strategy_list']}" if a['creative_auto_enhancement_strategy_list'] else "")
              + "; tiktok_item_id left out; no pixel as none set), with only landing_page_url = new and utm_params = the 5 UTMs of new (utm_id removed). ")
    else:
        head=(f"Pre-read ad/get req 2026101218115324649A5FA30B9C3D8810 (re-checked req 202610121814002930075D728D23E77193 just before the write, unchanged): URL == now (CUSTOMIZED_USER manual SINGLE_VIDEO, identity {a['identity_id']}, video_id {a['video_id']}, adgroup {a['adgroup_id']}, CTA {a['call_to_action']}, no pixel, op_status {a['operation_status']}, modify_time {a['modify_time']}, utm_params before {len(a['utm_params'])} keys {ub}). "
              f"dry_run preview body: creative fields sent back as read (ad_name, identity, ad_format, video_id, image_ids, ad_text, CTA, display_name {a['display_name']}, avatar, aigc {a['aigc_disclosure_type']}, creative_authorized true, vast_moat false), with only landing_page_url = new and utm_params = the 5 UTMs of new (utm_id removed). ")
    mid=f"Live full ad/update code 0 OK req {writes[i]} need_audit=false. "
    tail=f"Re-read req 202610121818571A3D5CD65C60470C8017: landing_page_url == new byte for byte; utm_params = 5 keys matching new, no utm_id; "
    oth=[k for k in others if k!='video_id']
    assert not oth, (i, oth)
    if 'video_id' in others:
        tail+=(f"ad_name/identity/image_ids/ad_text/CTA/dark_post/pixel/enhancement list/status unchanged (ad_text byte-identical); video_id now reads {b['video_id']} (was {a['video_id']}) = the existing post {a['tiktok_item_id']} own video id per identity/video/info req {VI if i!='1851307783558241' else ''} (known TikTok behaviour when the Spark creative is re-saved, same as tt7; tiktok_item_id unchanged); ")
    else:
        extra = " (incl. trailing space + U+200B, not trimmed)" if a['ad_text'].endswith(' ​') else ""
        tail+=f"all other fields identical to the pre-read (name/identity/video/images/ad_text{extra}/CTA/pixel/display/avatar/aigc/enhancement list/flags), ad_text byte-identical; "
    tail+=f"operation_status {b['operation_status']}, secondary_status {b['secondary_status']} unchanged; modify_time {b['modify_time']}."
    det=head+mid+tail
    r=subprocess.run(['python3',W+'/rec.py',i,'Fixed',b['landing_page_url'],det],capture_output=True,text=True)
    print(r.stdout.strip(), r.stderr.strip()[-300:])
