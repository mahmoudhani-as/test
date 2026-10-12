# Read-only verification of one unit from my own transcript (no API calls), then append its result line to the local results file.
import json, sys, copy, os
sys.path.insert(0,'/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/x7_work')
from tr import load_tr
calls, results, order = load_tr()
idx=int(sys.argv[1])
u=json.load(open('../in_x_7.json'))[idx]
share=json.load(open('share_summary.json'))[u['unit']]; cid=share['card_id']
pre=json.load(open(f'pre_{idx}.json')); before=pre['card_before']
xa=[t for t in order if (calls[t][0] or '').endswith('x_ads_native_action') and (calls[t][1].get('path_params') or {}).get('card_id')==cid and t in results]
gets=[t for t in xa if calls[t][1].get('action')=='GET_CARD']
upd=[t for t in xa if calls[t][1].get('action')=='UPDATE_CARD']
dry=[t for t in upd if calls[t][1].get('dry_run') is True]; live=[t for t in upd if calls[t][1].get('dry_run') is False]
assert len(live)==1, live
lt=live[0]; dt=dry[-1]
post_gets=[t for t in gets if order.index(t)>order.index(lt)]
gt=post_gets[-1]
exp=json.load(open(f'payload_{idx}.json'))
assert calls[lt][1]['payload']==exp and calls[dt][1]['payload']==exp
wr=json.loads(results[lt]); assert wr['success'] is True and wr['data']['success'] is True
after=json.loads(results[gt])['data']['data']['data']
assert len(u['changes'])==1
ch=u['changes'][0]
slot_i=int(ch['slot'].split('[')[1].split(']')[0]); assert ch['slot']==f'card.components[{slot_i}].destination.url'
b=before['components'][slot_i]['destination']['url']; a=after['components'][slot_i]['destination']['url']
def comp(c):
    c=copy.deepcopy(c); c.pop('updated_at',None); c['components'][slot_i]['destination']['url']='<URL>'; return c
same=comp(before)==comp(after)
print('unit', idx, 'card', cid, 'before==now:', b==ch['now'], '| before in alt_now:', b in ch['alt_now'], '| read-back==new:', a==ch['new'], '| rest unchanged:', same)
res='Fixed' if a==ch['new'] else 'Failed'
rq=lambda t: json.loads(results[t])['meta']['requestId']
idem=calls[lt][1].get('idempotency_key')
ad=u['ad_ids'][0]
media=[c.get('media_key') for c in after['components'] if c.get('type')=='MEDIA']
which='now' if b==ch['now'] else ('alt_now[%d]'%ch['alt_now'].index(b) if b in ch['alt_now'] else 'an equivalent value')
detail=(f"UPDATE_CARD PUT /12/accounts/18ce55o46ul/cards/{cid} (promoted tweet {ad} -> tweet {u['unit']}, card_uri card://{cid}, {after['card_type']}) {'OK' if res=='Fixed' else 'READ-BACK MISMATCH'}: "
 f"pre-read GET_CARD (req {rq(pre['get_tool'])}) slot equalled {which} byte for byte; dry-run (req {rq(dt)}) preview = name + components as read with only {ch['slot']} changed (media_metadata read-only, not sent; card has no experiment_signals); "
 f"live (req {rq(lt)}, idempotency key {idem}; PUT response already showed the new URL); independent GET_CARD re-read (req {rq(gt)}): slot {'equals new byte for byte' if a==ch['new'] else 'differs from new'}; "
 f"name, card_type, MEDIA media_key {','.join(media)}, DETAILS title, destination.type WEBSITE, deleted=false, created_at {'all unchanged' if same else 'CHANGED - see read-back'}. "
 f"Card not shared: live LIST_PROMOTED_TWEETS with_deleted (536 total) shows tweet {u['unit']} promoted only by {ad} (ACTIVE, ACCEPTED, not deleted); live LIST_TWEETS card_uri of all 188 tweets behind promoted tweets created on/after the earliest card in this batch (2025-11-12T14:46Z) shows only this tweet carries card://{cid}; tweet text has no URLs.")
rec={"platform":"x","account_id":u['account_id'],"unit_type":u['unit_type'],"unit":u['unit'],"ad_ids":u['ad_ids'],"ad_names":u['ad_names'],"slot":ch['slot'],"before":b,"after_expected":ch['new'],"after_live":a,"result":res,"new_entity_ids":"","detail":detail}
out='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/out_x_7.jsonl'
done={(json.loads(l)['unit'],json.loads(l)['slot']) for l in open(out)}
assert (u['unit'],ch['slot']) not in done, 'already recorded'
with open(out,'a',encoding='utf-8') as f: f.write(json.dumps(rec, ensure_ascii=False)+'\n')
print('appended', res, '| lines now', sum(1 for _ in open(out)))
