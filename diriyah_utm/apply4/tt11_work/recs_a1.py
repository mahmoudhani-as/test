from rec import rec, unit
common = ("Pixel confirmed via pixel/list req 20261012173732773D3EE385C26811274C (Visit Diriyah - Base Pixel 7347671240183693330), sent as exact string. "
 "dry_run preview: body = creative fields as read (ad_name, identity 7d136a20-71e2-5fb6-9927-ad76b915fac7 / BC_AUTH_TT / BC 6846326855419559942, ad_format SINGLE_VIDEO, video_id, image_ids, ad_text byte-identical with no trailing space, call_to_action_id, dark_post ON, creative_authorized true, vast_moat false) with only landing_page_url and utm_params changed; tiktok_item_id left out (Spark recipe from ad 1826384400556033). ")
rows = [
 ("1840143241069634", "call_to_action_id 7537258581314341896, utm_params 5 keys incl utm_id 5732", "2026101217391895033A7E77337E9A69C4", "09:39:20", "7537233298003741959", "v10033g50000d211e67og65p63agav20", "v10033g50000d2cpobfog65ia71an6c0", "ENABLE"),
 ("1840143241068594", "call_to_action_id 7537258624389811207, utm_params 5 keys incl utm_id 5912", "2026101217401465484E3ED00E66EE3F32", "09:40:16", "7537233298574036242", "v10033g50000d211govog65naec3sdlg", "v10033g50000d2cpobfog65ia71an6e0", "DISABLE"),
 ("1840143241068578", "call_to_action_id 7537227055633583112, utm_params 4 keys (no utm_term/utm_id)", "20261012174022995D32AC3FBD11919866", "09:40:24", "7537233298444012807", "v10033g50000d211e67og65p63agav20", "v10033g50000d2cpobfog65vslt2g8d0", "DISABLE"),
 ("1840143241068546", "call_to_action_id 7537227055633566728, utm_params 4 keys (no utm_term/utm_id)", "20261012174037A6F64BB121AF5CB50A52", "09:40:39", "7537232814987611413", "v10033g50000d211govog65naec3sdlg", "v10033g50000d2cpobfog65ia71an6dg", "DISABLE"),
]
for uid, pre, req, mt, item, vold, vnew, ops in rows:
    u=unit(uid); c=u['changes'][0]
    d=(f"pre-read ad/get req 20261012173636F3747BF32560DA77DFC9: URL == now (BC_AUTH_TT Spark ad, {pre}). " + common +
       f"Live full ad/update code 0 OK req {req} need_audit=false. Re-read req 20261012174048F922D8DFBEC87B60F60C: landing_page_url == new byte for byte; utm_params = 5 keys matching new, no utm_id; "
       f"tiktok_item_id {item} / identity / ad_name / ad_text / image_ids / call_to_action_id / dark_post / pixel unchanged; operation_status {ops}, secondary_status AD_STATUS_CAMPAIGN_DISABLE unchanged; modify_time 2026-10-12 {mt}. "
       f"SIDE EFFECT: ad-level video_id now reads {vnew} (was {vold}), same known behaviour as ad 1826384400556033 (TikTok re-resolves video_id to the existing post's own video); tiktok_item_id unchanged, same post served.")
    rec(uid, c['now'], c['new'], 'Fixed', d)
