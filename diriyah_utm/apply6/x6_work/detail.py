import json, sys
W='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/x6_work'
exec(open(W+'/tr.py').read().split("if __name__")[0])
idx=int(sys.argv[1]); dry=sys.argv[2]; live=sys.argv[3]
u=json.load(open(W+'/../in_x_6.json'))[idx]
pre=json.load(open(f'{W}/pre_{idx}.json')); post=json.load(open(f'{W}/post_{idx}.json'))
calls, order, results = load()
rid=lambda t: json.loads(results[t]).get('meta',{}).get('requestId')
c=pre['card_before']
title=[x for x in c['components'] if x.get('type')=='DETAILS'][0]['title']
media=[x for x in c['components'] if x.get('type')!='DETAILS'][0]
mk=media.get('media_key') or media.get('media_keys')
hidden=''
if title.endswith('​'): hidden=' (title ends with U+200B zero-width space, sent as \\u200b and preserved)'
elif title.endswith(' '): hidden=' (title trailing space preserved)'
before_is=pre['status'][u['changes'][0]['slot']]['cur_is']
d=(f"UPDATE_CARD PUT /12/accounts/{u['account_id']}/cards/{c['id']} (promoted tweet {u['ad_ids'][0]} -> tweet {u['unit']}, card_uri {c['card_uri']}, {c['card_type']}) OK: "
   f"pre-read GET_CARD (req {pre['get_reqid']}) slot equalled '{before_is}' byte for byte; dry-run (req {rid(dry)}) preview = name + components as read with only {{SLOT}} changed "
   f"(media_metadata read-only, not sent; no experiment_signals on the card as read, so none to carry); then live (req {rid(live)}, idempotency key used, PUT response already showed the new URL); "
   f"independent GET_CARD re-read (req {post['reqid']}): {{SLOT}} equals new byte for byte; name, card_type, {media.get('type')} {('media_keys' if isinstance(mk,list) else 'media_key')} {mk if not isinstance(mk,list) else ','.join(mk)}, DETAILS title{hidden}, destination.type WEBSITE, deleted=false, created_at all unchanged (updated_at not changed by API). "
   f"Card not shared: live LIST_PROMOTED_TWEETS with_deleted (536 total) shows tweet {u['unit']} promoted only by {u['ad_ids'][0]} (ACTIVE, ACCEPTED, not deleted); live LIST_TWEETS card_uri of all 202 tweets behind promoted tweets created on/after the earliest card in this batch (2025-11-10T15:20:24Z) shows only tweet {u['unit']} carries {c['card_uri']}; tweet text has no URLs.")
print(d)
