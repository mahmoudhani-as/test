import json
from urllib.parse import urlsplit, parse_qsl
units={u['unit']:u for u in json.load(open('../in_tiktok_10.json'))}
TI0={"brand_safety_postbid_partner":"UNSET","tracking_pixel_id":"0"}
TIP={"brand_safety_postbid_partner":"UNSET","tracking_pixel_id":"7347671240183693330"}
cfg={
 "1851290981720097":{"call_to_action_id":"7582890708235799560","creative_auto_add_toggle":False,"dark_post_status":"ON",
   "product_info":{"product_image_list":[{"web_uri":"tos-alisg-i-6zvbrtwab1-sg/8c96e5bc05f2bbcd1a20a07a9ece6223"}],"product_titles":["boarding pass"],
     "selling_points":["Fast & Reliable Service","Weekday Dining Deals","Popular Brand Trust","No Hidden Fees","Free Parking Included","Dine at Top Restaurants","Secure Online Ordering"]},
   "product_info_enabled":"NON_CATALOG","product_set_id":"0","tracking_info":TI0},
 "1851292558668913":{"call_to_action_id":"7582895815220349960","creative_auto_add_toggle":False,"dark_post_status":"ON","product_info_enabled":"NON_CATALOG","product_set_id":"0","tracking_info":TI0},
 "1851300482116657":{"call_to_action_id":"7582928193947028488","catalog_creative_toggle":False,"creative_auto_add_toggle":False,"dark_post_status":"ON","product_info_enabled":"NON_CATALOG","product_specific_type":"UNSET","tracking_info":TIP},
 "1851300984489202":{"call_to_action_id":"7582930003143232520","catalog_creative_toggle":False,"creative_auto_add_toggle":False,"dark_post_status":"ON","product_info_enabled":"NON_CATALOG","product_specific_type":"UNSET","tracking_info":TIP},
 "1873225871586577":{"call_to_action_id":"7672735502981811221","dark_post_status":"ON","tracking_info":TI0},
 "1876857771963474":{"call_to_action_id":"7687615715360164871","dark_post_status":"ON","tracking_info":TI0},
}
out={}
for ad,c in cfg.items():
    new=units[ad]['changes'][0]['new']
    q=parse_qsl(urlsplit(new).query,keep_blank_values=True)
    assert all(k.startswith('utm_') and k!='utm_id' for k,_ in q)
    ac=dict(c); ac['utm_params']=[{"key":k,"value":v} for k,v in q]
    p={"advertiser_id":"7338057963233443842","smart_plus_ad_id":ad,"landing_page_url_list":[{"landing_page_url":new}],"ad_configuration":ac}
    out[ad]=p
    print(json.dumps(p,ensure_ascii=True))
json.dump(out,open('sp_payloads.json','w'),ensure_ascii=False,indent=1)
