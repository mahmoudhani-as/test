from rec import rec, unit
RR="20261012174747C633462D0F56573278A7"
car=[
 ("1874943913104801","1 image, adgroup 1866980899041010, operation_status ENABLE","20261012174524F86621EB6B8A4E8E85F3","09:45:25","ENABLE"),
 ("1874943317387714","1 image, adgroup 1866980896932194, operation_status ENABLE","20261012174544F5C0A18C0D5F182E594B","09:45:45","ENABLE"),
]
for uid,info,req,mt,ops in car:
    c=unit(uid)['changes'][0]
    d=(f"pre-read ad/get req 20261012173712F5382101C8B6F6F1BC7F (re-confirmed req 20261012174231BD443DA14975C920A2C9): URL == now (BC_AUTH_TT Spark Push CAROUSEL_ADS, identity 0f6eebaa-ba16-5ad3-aa97-4171805e2af1 / BC 6807778858780065797, {info}, music_id 7647465303001156353, CTA BOOK_NOW, no tiktok_item_id, tracking_pixel_id 0, utm_params 5 keys matching old URL, no utm_id). "
       "dry_run preview: full ad/update body = identity fields, ad_format, image_ids, music_id, ad_text (no trailing space, as read), call_to_action BOOK_NOW, dark_post ON, creative_authorized false, vast_moat false as read; only landing_page_url + utm_params changed; no tiktok_item_id, no pixel (0), aigc/deeplink not sent. "
       f"Live write code 0 OK req {req} need_audit=false. Re-read req {RR}: landing_page_url == new byte for byte; utm_params = 5 keys matching new, no utm_id; ad_name/identity/image_ids/music_id/ad_text/CTA/dark_post/aigc NOT_DECLARED unchanged; operation_status {ops}, secondary_status AD_STATUS_CAMPAIGN_DISABLE unchanged; modify_time 2026-10-12 {mt}.")
    rec(uid, c['now'], c['new'], 'Fixed', d)

vid=[
 ("1870052721331313","adgroup 1866980899041010, tiktok_item_id 7679779371967630613, video v10033g50000d92i7pvog65ibdthhk50; utm_params had 5 keys whose utm_content (ad-id-02E30F_manazel-alhadawi-kv2_display) did not match the URL's utm_content (...video1_video) - now realigned to new",
  "Live write code 0 OK req 20261012174612C64A60FD99D105A18F43 need_audit=false.","09:46:14","video_id unchanged (v10033g50000d92i7pvog65ibdthhk50)."),
 ("1869522880650450","adgroup 1866980899041010, tiktok_item_id 7657582071820324113, video v10033g50000d92i7pvog65ibdthhk50; utm_params utm_content (ad-id-02E30F_manazel-alhadawi-kv2_display) did not match the URL's utm_content - now realigned to new",
  "Live write code 0 OK req 202610121746382BC5B6D7C42D0F7DC50A need_audit=false.","09:46:41","SIDE EFFECT: ad-level video_id now reads v14033g50000d92i937og65ih829f900 (was v10033g50000d92i7pvog65ibdthhk50), same known behaviour as ad 1826384400556033 (TikTok re-resolves video_id to the existing post's own video); tiktok_item_id unchanged, same post served."),
 ("1869522559450418","adgroup 1866980896932194, tiktok_item_id 7657602497988676885, video v10033g50000d92i4vvog65tdbo7qcu0; ad_text contains U+2019 apostrophe, sent as read; utm_params utm_content (ad-id-2CEFE3_manazel-alhadawi-kv2_display) did not match the URL's utm_content - now realigned to new",
  "Live attempt 1 rejected: TikTok 40002 'Invalid Value: no permission to access this ad or id not exist.' req 2026101217470426AC1495502248CE3974 (transient; same error seen once on ad 1840143241068562 in this batch); re-read req 202610121747128848B057D967A1ADE2A7 showed ad unchanged; identity/video/info req 20261012174719C6164ECA0C14A51C758C confirmed post 7657602497988676885 available. Attempt 2 (same payload) code 0 OK req 20261012174730BC59B5F4CCD31E9E657A need_audit=false.","09:47:40","video_id unchanged (v10033g50000d92i4vvog65tdbo7qcu0)."),
]
for uid,info,wr,mt,side in vid:
    c=unit(uid)['changes'][0]
    d=(f"pre-read ad/get req 20261012173712F5382101C8B6F6F1BC7F (re-confirmed req 20261012174231BD443DA14975C920A2C9): URL == now (BC_AUTH_TT Spark SINGLE_VIDEO, identity 0f6eebaa-ba16-5ad3-aa97-4171805e2af1 / BC 6807778858780065797, {info}; CTA BOOK_NOW, tracking_pixel_id 0, no utm_id). "
       "dry_run preview: full ad/update body = identity fields, ad_format, video_id, image_ids, ad_text (no trailing space, as read), call_to_action BOOK_NOW, dark_post ON, creative_authorized true, vast_moat false as read; only landing_page_url + utm_params changed; tiktok_item_id left out (Spark recipe from ad 1826384400556033), no pixel (0). "
       f"{wr} Re-read req {RR}: landing_page_url == new byte for byte; utm_params = 5 keys matching new, no utm_id; tiktok_item_id / identity / ad_name / ad_text / image_ids / CTA / dark_post / aigc unchanged; operation_status DISABLE, secondary_status AD_STATUS_CAMPAIGN_DISABLE unchanged; modify_time 2026-10-12 {mt}. {side}")
    rec(uid, c['now'], c['new'], 'Fixed', d)
