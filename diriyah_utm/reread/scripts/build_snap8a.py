import json, re, sys
W, INP, OUT, NEWOUT = sys.argv[1:5]
ACC = "8a1750fe-a8a8-4c73-b591-3a5a34937436"
inp = json.load(open(INP))
ads = {a['ad']['id']: a['ad'] for a in json.load(open(W + '/ads.txt'))['data']['data']['ads']}
crs = {c['creative']['id']: c['creative'] for c in json.load(open(W + '/creatives.txt'))['data']['data']['creatives']}
h = json.load(open(W + '/hier.json'))

def order_status(cur, prev):
    prev_l = prev.split('|') if prev else []
    first = [s for s in prev_l if s in cur]
    rest = [s for s in cur if s not in first]
    return '|'.join(first + rest)

out = []
for r in inp:
    ad = ads.get(r['ad_id'])
    rec = {"platform": "snapchat", "account_id": ACC, "ad_id": r['ad_id'], "slot": r['slot']}
    if ad is None:
        rec.update(url=None, status_now=None, creative_id_now=None, found=False,
                   note="ad not returned by GET adaccounts/{id}/ads on 12-Oct-2026 (deleted)")
        out.append(rec); continue
    sq = h['adsquads'][ad['ad_squad_id']]
    camp = h['campaigns'][sq[2]]
    status_now = order_status(ad.get('delivery_status') or [], r.get('status_11oct'))
    notes = [f"ad.status={ad['status']}; adsquad.status={sq[1]}; campaign.status={camp[1]}; ad.type={ad['type']}; review_status={ad.get('review_status')}"]
    cid = ad['creative_id']
    if cid != r['creative_id']:
        notes.append(f"CREATIVE CHANGED since 11-Oct (was {r['creative_id']})")
    cr = crs.get(cid)
    url = None; found = True
    slot = r['slot']
    if cr is None:
        found = False
        notes.append(f"creative {cid} not returned by creatives list (deleted)")
    elif slot is None:
        notes.append(f"no URL slot: creative.type={cr['type']} has no web_view/deep_link properties (unchanged from 11-Oct)")
        if cr.get('web_view_properties'):
            url = cr['web_view_properties'].get('url'); notes.append("NOTE: creative now HAS web_view url")
    elif slot == 'web_view_properties.url':
        url = (cr.get('web_view_properties') or {}).get('url')
        notes.append(f"creative.type={cr['type']}; url read from creative {cid}.web_view_properties.url")
        if url is None:
            notes.append("web_view_properties.url missing now")
    else:
        m = re.match(r'composite_properties\.creative_ids\[(\d+)\] -> creative ([0-9a-f-]{36}) ', slot)
        idx, child = int(m.group(1)), m.group(2)
        kids = (cr.get('composite_properties') or {}).get('creative_ids') or []
        cur_child = kids[idx] if idx < len(kids) else None
        if cur_child != child:
            notes.append(f"COMPOSITE CHILD CHANGED: position {idx} now {cur_child} (was {child})")
        ch = crs.get(child)
        if ch is None:
            found = False
            notes.append(f"child creative {child} not returned (deleted)")
        else:
            url = (ch.get('web_view_properties') or {}).get('url')
            notes.append(f"composite {cid} -> child {child} (type={ch['type']}); url read from child web_view_properties.url")
    if found and slot is not None:
        if url == r['url_11oct']:
            notes.append("URL unchanged vs 11-Oct")
        else:
            notes.append("URL CHANGED vs 11-Oct")
    notes.append("UTMs inline in URL (Snapchat has no separate url_tags field)")
    rec.update(url=url, status_now=status_now, creative_id_now=cid, found=found, note="; ".join(notes))
    out.append(rec)

with open(OUT, 'w') as f:
    for rec in out:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

# Task 2: ads not in input
in_ids = {r['ad_id'] for r in inp}
new = []
for aid, ad in ads.items():
    if aid in in_ids: continue
    # would expand slots here; none expected
    new.append(aid)
with open(NEWOUT, 'w') as f:
    pass
print("rows", len(out), "new ads", len(new), new)
