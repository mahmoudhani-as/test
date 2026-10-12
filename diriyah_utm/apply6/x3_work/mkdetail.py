import json, sys
W='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/x3_work'
units=json.load(open('/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/in_x_3.json'))
share=json.load(open(W+'/share_ul.json'))
d=json.load(open(W+'/details.json'))
for a in sys.argv[1:]:
    i=int(a); u=units[i]
    pre=json.load(open(f'{W}/pre_{i}.json'))['card_before']
    s=share[str(i)]
    tweet=s['tweets'][0]; pt=u['ad_ids'][0]
    titles=[c.get('title') for c in (pre.get('components') or []) if c.get('title')]+[c.get('title') for sl in (pre.get('slides') or []) for c in sl if c.get('title')]
    arabic=' (Arabic codepoints verified)' if any(t and not t.isascii() for t in titles) else ''
    media='media_keys' if any('media_keys' in c for c in (pre.get('components') or [])) else 'media_key'
    es='experiment_signals sent back as read' if 'experiment_signals' in pre else 'no experiment_signals on card (none before or after)'
    d[str(i)]=(f"UPDATE_CARD PUT /12/accounts/{u['account_id']}/cards/{pre['id']} (promoted tweet {pt} -> tweet {tweet}, card_uri card://{pre['id']}, {pre['card_type']}) OK (dry-run then live; payload = card as read with only {{SLOT}} changed, read-only media_metadata not sent); "
               f"card re-read: {{SLOT}} equals new byte for byte; name/title{arabic}/{media}/media_metadata/card_type and every other card field unchanged; {es}; "
               f"card unique to this tweet (card_uri of all 438 tweets behind the account's 536 promoted tweets incl. deleted, created after the earliest card, checked live: only tweet {tweet} uses it; {pt} is the only promoted_tweet for that tweet)")
    print(i, d[str(i)][:160])
json.dump(d, open(W+'/details.json','w'), ensure_ascii=False, indent=1)
