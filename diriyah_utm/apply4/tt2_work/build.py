import json, sys
from urllib.parse import urlsplit, parse_qsl
d=json.loads(open('pre_read_text.json').read())
lst=d['data']['data']['data']['list']
byid={a['ad_id']:a for a in lst}
inp=json.load(open('../in_tiktok_2.json'))
PIX="7347671240183693330"
out={}
for u in inp:
    a=byid[u['unit']]; ch=u['changes'][0]
    new=ch['new']
    q=parse_qsl(urlsplit(new).query, keep_blank_values=True)
    assert all(k!='utm_id' for k,v in q)
    assert str(a['tracking_pixel_id']).startswith('73476712401836')
    cr={
      "ad_id": a['ad_id'],
      "ad_name": a['ad_name'],
      "identity_id": a['identity_id'],
      "identity_type": a['identity_type'],
      "ad_format": a['ad_format'],
      "video_id": a['video_id'],
      "image_ids": a['image_ids'],
      "ad_text": a['ad_text'],
      "call_to_action": a['call_to_action'],
      "landing_page_url": new,
      "utm_params": [{"key":k,"value":v} for k,v in q],
      "tracking_pixel_id": PIX,
      "display_name": a['display_name'],
      "avatar_icon_web_uri": a['avatar_icon_web_uri'],
      "aigc_disclosure_type": a['aigc_disclosure_type'],
      "creative_authorized": a['creative_authorized'],
      "vast_moat_enabled": a['vast_moat_enabled'],
    }
    assert a['call_to_action_id'] in (None,'') and a['music_id'] in (None,'') and a['card_id'] in (None,'') and a['page_id'] in (None,'')
    assert a['deeplink']=='' and a['impression_tracking_url'] in (None,'') and a['click_tracking_url'] in (None,'') and a['playable_url']==''
    out[a['ad_id']]={"advertiser_id":u['account_id'],"adgroup_id":a['adgroup_id'],"creatives":[cr]}
json.dump(out,open('payloads.json','w'),ensure_ascii=False,indent=1)
if len(sys.argv)>1:
    print(json.dumps(out[sys.argv[1]],ensure_ascii=False))
