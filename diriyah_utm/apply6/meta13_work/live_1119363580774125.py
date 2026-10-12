import json, sys
sys.path.insert(0, '.')
from lib import *
live = {
 "name": "company_general_2026_sep_resi-patio-kv3_adset-id-1469e841_display_ar_v2 2026-09-30-fbd35dfed8bfb15d9caa0fe88d3334cd",
 "threads_user_id": "17841460099388007",
 "object_story_spec": {"page_id": "111467331865347", "instagram_user_id": "17841456393254006"},
 "asset_feed_spec": {
  "optimization_type": "PLACEMENT", "call_to_action_types": ["LEARN_MORE"], "ad_formats": ["AUTOMATIC_FORMAT"],
  "reasons_to_shop": False, "shops_bundle": False,
  "bodies": [{"text": "منازل الدرعية.. منزلٌ يجمع بين المجتمع، والثقافة، والطبيعة، وتفاصيل الحياة اليومية.",
              "adlabels": [{"name": "ar_kv3_body_s", "id": "120253320109440058"}, {"name": "ar_kv3_body_v", "id": "120253320109470058"}]}],
  "titles": [{"text": "منزل في مدينة صممت للحياة",
              "adlabels": [{"name": "ar_kv3_title_s", "id": "120253320109430058"}, {"name": "ar_kv3_title_v", "id": "120253320109460058"}]}],
  "descriptions": [{"text": "تعرّف أكثر",
              "adlabels": [{"name": "ar_kv3_desc_v", "id": "120253320109410058"}, {"name": "ar_kv3_desc_s", "id": "120253320109420058"}]}],
  "link_urls": [{"website_url": "https://www.diriyahcompany.sa/ar/life-in-diriyah?utm_source=meta&utm_medium=paid-social&utm_campaign=2c0ef446_diriyah-living_sep26&utm_term=3e71b680_residential_ar&utm_content=1469e841_resi-patio-kv3_display_ar",
              "adlabels": [{"name": "ar_kv3_url_s", "id": "120253320109450058"}, {"name": "ar_kv3_url_v", "id": "120253320109490058"}]}],
  "images": [{"hash": "6174eee6bff23635acaaf74bf8935221", "adlabels": [{"name": "ar_kv3_img_vertical", "id": "120253320109480058"}]},
             {"hash": "88bc524040c95b7abc5fc45f7bdbe586", "adlabels": [{"name": "ar_kv3_img_square", "id": "120253320109500058"}]}],
  "asset_customization_rules": [
   {"priority": 1,
    "body_label": {"name": "ar_kv3_body_v", "id": "120253320109470058"},
    "title_label": {"name": "ar_kv3_title_v", "id": "120253320109460058"},
    "link_url_label": {"name": "ar_kv3_url_v", "id": "120253320109490058"},
    "image_label": {"name": "ar_kv3_img_vertical", "id": "120253320109480058"},
    "description_label": {"name": "ar_kv3_desc_v", "id": "120253320109410058"},
    "customization_spec": {"age_min": 13, "age_max": 65, "publisher_platforms": ["facebook", "instagram"],
                           "instagram_positions": ["story", "reels"], "facebook_positions": ["story", "facebook_reels"]}},
   {"priority": 2,
    "body_label": {"name": "ar_kv3_body_s", "id": "120253320109440058"},
    "title_label": {"name": "ar_kv3_title_s", "id": "120253320109430058"},
    "link_url_label": {"name": "ar_kv3_url_s", "id": "120253320109450058"},
    "image_label": {"name": "ar_kv3_img_square", "id": "120253320109500058"},
    "description_label": {"name": "ar_kv3_desc_s", "id": "120253320109420058"},
    "customization_spec": {"age_min": 13, "age_max": 65}}],
  "additional_data": {"multi_share_end_card": False, "is_click_to_message": False}},
 "degrees_of_freedom_spec": dof_all_optout(),
 "creative_sourcing_spec": {"destination_screenshot_spec": {"enroll_status": "OPT_OUT"}},
}
json.dump(live, open('live_1119363580774125.json', 'w'), ensure_ascii=False, indent=1)
