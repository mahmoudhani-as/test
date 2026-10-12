import json, collections
ACC="18ce55o46ul"; ACCN="H&S-DiriyahCo"
OUT="/tmp/claude-0/-home-user-test/c5fcace8-62b1-55a4-9129-dbfe4d94e847/scratchpad/live/x_18ce55o46ul.jsonl"
SERVABLE={"osvh1","ou7mx","owpmd","oysbu","p00bw","p8rhd","p9ppt","pct00","pct0p"}
camps={}
for l in open('campaigns.tsv'):
    i,n,s=l.rstrip('\n').split('\t'); camps[i]=(n,s)
lis={}
for l in open('line_items.tsv'):
    i,n,s,c=l.rstrip('\n').split('\t'); lis[i]=(n,s,c)
pts=[l.rstrip('\n').split('\t') for l in open('pt_all.tsv')]
tw={}
for l in open('tweets.tsv'):
    t,n,cu,_=l.rstrip('\n').split('\t'); tw[t]=(n or None, cu or None)
turls=collections.defaultdict(list)
for l in open('tweet_urls.tsv'):
    t,idx,u,tco=l.rstrip('\n').split('\t'); turls[t].append((int(idx),u,tco))
cards=collections.OrderedDict()
for l in open('cards_all.tsv'):
    cid,ct,cn,slot,u=l.rstrip('\n').split('\t')
    cards.setdefault(cid,{'type':ct,'name':cn,'slots':[]})['slots'].append((slot,u))
organic=set(l.strip() for l in open('organic.txt'))
card_use=collections.Counter()
for p in pts:
    cu=tw[p[2]][1]
    if cu and cu.startswith('card://'): card_use[cu[7:]]+=1
MISSING_CARD_ERR=("card not returned by GET /12/accounts/18ce55o46ul/cards?card_uris=card://{cid}&include_legacy_cards=true&with_deleted=true "
                  "(HTTP 200, empty data array); GET /12/accounts/18ce55o46ul/cards/all?card_uris=...&with_deleted=true also returned an empty data array; "
                  "the card is not returned for this ad account (likely created under another account), so its destination URL could not be read")
CARD_EDIT="card update: PUT /12/accounts/18ce55o46ul/cards/{cid} (UPDATE_CARD) with the full components/slides array and the new destination.url{shared}"
TWEET_EDIT="no in-place edit: links in a published tweet's text are immutable; publish a new tweet with the corrected link and promote it (new promoted_tweet) in place of this one"
rows=[]
for pid,li,tid,pst,appr in pts:
    lin,lis_,cid_=lis[li]; cn,cs=camps[cid_]
    name,cu=tw[tid]
    # effective status
    if cs!='ACTIVE': eff=f"CAMPAIGN_{cs}"
    elif lis_!='ACTIVE': eff=f"LINE_ITEM_{lis_}"
    elif pst!='ACTIVE': eff=f"AD_{pst}"
    else: eff="ACTIVE" if cid_ in SERVABLE else "ACTIVE_NOT_SERVABLE (campaign servable=false, e.g. ended flight/budget)"
    if appr!='ACCEPTED': eff+=f" / approval={appr}"
    base={"platform":"x","account_id":ACC,"account_name":ACCN,
          "campaign_id":cid_,"campaign_name":cn,"campaign_status":cs,
          "adset_id":li,"adset_name":lin,"adset_status":lis_,
          "ad_id":pid,"ad_name":name,"ad_status":pst,"effective_status":eff,
          "creative_id":tid,"creative_name":None,"slot":None,"base_url":None,"url_tags":None,"url":None,
          "tracking_template":None,"editable":None,"edit_method":None,"notes":None}
    common=[f"promoted_tweet {pid} -> tweet {tid}", f"approval_status={appr}"]
    if tid in organic: common.append("boosted organic post (nullcast=false)")
    else: common.append("promoted-only post (nullcast=true)")
    out=[]
    if cu and cu.startswith('card://'):
        cid=cu[7:]
        if cid in cards:
            c=cards[cid]
            shared=card_use[cid]
            sh=f"; card is used by {shared} promoted tweets in this account, an update changes all of them" if shared>1 else ""
            for slot,u in c['slots']:
                r=dict(base); r['creative_name']=c['name']
                r['slot']=f"card.{slot}"; r['base_url']=u; r['url']=u
                r['editable']="yes"; r['edit_method']=CARD_EDIT.format(cid=cid,shared=sh)
                r['notes']="; ".join(common+[f"card_uri={cu}", f"card_type={c['type']}"])
                out.append(r)
        else:
            r=dict(base); r['slot']=f"card.destination.url (card_uri={cu})"
            r['editable']="unknown"; r['edit_method']="unknown: card could not be read"
            r['notes']="; ".join(common+["ERROR: "+MISSING_CARD_ERR.format(cid=cid)])
            out.append(r)
    elif cu=='tombstone://card':
        common.append("card_uri=tombstone://card (the website card attached to this tweet was deleted; no card destination)")
    for idx,u,tco in sorted(turls.get(tid,[])):
        r=dict(base); r['slot']=f"tweet.entities.urls[{idx}].expanded_url"
        r['base_url']=u; r['editable']="no"; r['edit_method']=TWEET_EDIT
        n=common+[f"link in tweet text (t.co={tco})"]
        if u.startswith('https://x.com/i/web/status/'):
            r['url']=None
            n.append("long-form post: the API returns only the truncated 'show more' link to the full post; the actual destination link inside the full post text is not exposed by the Ads API tweets endpoint (no note_tweet field), so the final landing URL could not be read")
        else:
            r['url']=u
            if 'bit.ly' in u: n.append("bit.ly short link; redirect target not resolved (read-only API pull)")
        r['notes']="; ".join(n)
        out.append(r)
    if not out:
        r=dict(base); r['editable']="no"; r['edit_method']="n/a: no URL slot (would require a new tweet with a website card)"
        r['notes']="; ".join(common+["no website card and no link in tweet text (media/text-only post)" + ("" if cu!='tombstone://card' else "")])
        out.append(r)
    rows.extend(out)
with open(OUT,'w') as f:
    for r in rows: f.write(json.dumps(r,ensure_ascii=False)+'\n')
print(len(rows))
