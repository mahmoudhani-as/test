import json, collections
exec(open('tr.py').read().split("if __name__")[0])
calls, order, results = load()
cand=json.load(open('cand_tweets.json'))
got={}
for tid in order:
    name, inp = calls[tid]
    if name.endswith('x_ads_native_action') and inp.get('action')=='LIST_TWEETS' and inp.get('result_fields')==['id_str','card_uri']:
        d=json.loads(results[tid])
        for t in d['data']['data']['data']:
            got[t['id_str']]=t.get('card_uri')
print('candidates', len(cand), 'returned', len(got), 'missing', sorted(set(cand)-set(got)))
units=json.load(open('../in_x_6.json'))
pre_tw={t['id_str']:t['card_uri'] for t in json.load(open('pre_tweets.json'))['data']['data']['data']}
by_card=collections.defaultdict(list)
for tw,cu in got.items():
    if cu: by_card[cu].append(tw)
summary={}
for u in units:
    cu=pre_tw[u['unit']]
    users=by_card.get(cu, [])
    print(u['unit'], cu, 'tweets carrying this card:', users)
    summary[u['unit']]={'card_uri':cu,'card_id':cu.split('//')[1],'tweets_with_card':users}
json.dump(summary, open('share_summary.json','w'), indent=1)
print('no-card tweets among candidates:', [k for k,v in got.items() if not v])
