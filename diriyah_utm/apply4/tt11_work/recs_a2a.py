from rec import rec, unit
rows=[
 ("1874956515381633","5 images, adgroup 1866980896932194","20261012174305C6D033D76185732D1A34","09:43:06",""),
 ("1874956278666242","5 images, adgroup 1866980899041010","20261012174353DD1CDC67D295228DEDCE","09:43:54",""),
 ("1874952313665937","5 images, adgroup 1866980896932194","20261012174415218335986A0EC580A478","09:44:17",""),
 ("1874951789893937","5 images, adgroup 1866980899041010","202610121744408A82D4051BC171B7B589","09:44:41"," (write response body echoed a stale snapshot with old utm_params/modify_time; the re-read is authoritative)"),
]
for uid,info,req,mt,extra in rows:
    c=unit(uid)['changes'][0]
    d=(f"pre-read ad/get req 20261012173712F5382101C8B6F6F1BC7F (re-confirmed req 20261012174231BD443DA14975C920A2C9): URL == now (BC_AUTH_TT Spark Push CAROUSEL_ADS, identity 0f6eebaa-ba16-5ad3-aa97-4171805e2af1 / BC 6807778858780065797, {info}, music_id 7647465303001156353, CTA BOOK_NOW, no tiktok_item_id, tracking_pixel_id 0, utm_params 5 keys matching old URL, no utm_id). "
       "dry_run preview: full ad/update body = identity fields, ad_format, image_ids, music_id, ad_text (no trailing space, as read), call_to_action BOOK_NOW, dark_post ON, creative_authorized false, vast_moat false as read; only landing_page_url + utm_params changed; no tiktok_item_id, no pixel (0), aigc/deeplink not sent. "
       f"Live write code 0 OK req {req} need_audit=false{extra}. Re-read req 20261012174449950BBDF762E91D339147: landing_page_url == new byte for byte; utm_params = 5 keys matching new, no utm_id; ad_name/identity/image_ids/music_id/ad_text/CTA/dark_post/aigc NOT_DECLARED/creative_auto_enhancement IMAGE_QUALITY+IMAGE_RESIZE unchanged; operation_status DISABLE, secondary_status AD_STATUS_CAMPAIGN_DISABLE unchanged; modify_time 2026-10-12 {mt}.")
    rec(uid, c['now'], c['new'], 'Fixed', d)
