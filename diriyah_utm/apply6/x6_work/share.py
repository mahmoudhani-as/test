import json, sys, datetime, collections
exec(open('tr.py').read().split("if __name__")[0])
calls, order, results = load()
pages=[]
for tid in order:
    name, inp = calls[tid]
    if name.endswith('x_ads_native_action') and inp.get('action')=='LIST_PROMOTED_TWEETS' and (inp.get('params') or {}).get('count')=='200' and 'promoted_tweet_ids' not in (inp.get('params') or {}):
        pages.append((tid, inp, json.loads(results[tid])))
allpt=[]
for tid, inp, d in pages:
    data=d['data']['data']['data']
    print(tid, (inp['params'].get('cursor')), len(data), 'next', d['data']['data'].get('next_cursor'))
    allpt+=data
print('total', len(allpt), 'unique ids', len({p['id'] for p in allpt}))
json.dump(allpt, open('pt_all.json','w'))
units=json.load(open('../in_x_6.json'))
def ts(i): return datetime.datetime.fromtimestamp(((int(i)>>22)+1288834974657)/1000, datetime.timezone.utc)
cards=json.load(open('pre_cards_list.json'))['data']['data']['data']
earliest=min(datetime.datetime.fromisoformat(c['created_at'].replace('Z','+00:00')) for c in cards)
print('earliest card created', earliest)
by_tweet=collections.defaultdict(list)
for p in allpt: by_tweet[p['tweet_id']].append((p['id'], p['deleted']))
for u in units:
    print(u['unit'], 'promoted by', by_tweet[u['unit']], 'unit ad_ids', u['ad_ids'])
cand=sorted({p['tweet_id'] for p in allpt if ts(p['tweet_id'])>=earliest})
print('candidate tweets created >= earliest card:', len(cand))
json.dump(cand, open('cand_tweets.json','w'))
