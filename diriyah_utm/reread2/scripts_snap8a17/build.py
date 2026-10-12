import json, re, sys
W = sys.argv[1]
IN = sys.argv[2]
OUT = sys.argv[3]
ACC = "8a1750fe-a8a8-4c73-b591-3a5a34937436"
ads = {a['id']: a for a in json.load(open(W + '/ads.json'))}
crs = {c['id']: c for c in json.load(open(W + '/creatives.json'))}
sqs = json.load(open(W + '/adsquads_status.json'))
rows = json.load(open(IN))
SLOT_RE = re.compile(r'^composite_properties\.creative_ids\[(\d+)\] -> creative ([0-9a-f-]{36}) \((.*)\)\.web_view_properties\.url$')

def norm_status(now_list, old_str):
    old = (old_str or '').split('|') if old_str else []
    def key(s):
        return (0, old.index(s)) if s in old else (1, now_list.index(s))
    return '|'.join(sorted(now_list, key=key))

out = []
for r in rows:
    ad_id = r['ad_id']; slot = r['slot']
    rec = {"platform": "snapchat", "account_id": ACC, "ad_id": ad_id, "slot": slot,
           "url": None, "status_now": None, "creative_id_now": None, "found": False, "note": ""}
    a = ads.get(ad_id)
    if a is None:
        rec['note'] = 'ad not returned by GET /adaccounts/{id}/ads on 12-Oct (deleted)'
        out.append(rec); continue
    notes = []
    rec['status_now'] = norm_status(a['delivery_status'], r['status_11oct'])
    rec['creative_id_now'] = a['creative_id']
    rec['found'] = True
    if set(a['delivery_status']) != set((r['status_11oct'] or '').split('|')):
        notes.append('delivery status changed vs 11-Oct (was %s)' % r['status_11oct'])
    notes.append('ad.status=%s; review_status=%s' % (a['status'], a['review_status']))
    if a.get('review_status_reasons'):
        notes.append('review_status_reasons: ' + ' / '.join(a['review_status_reasons']))
    if a['creative_id'] != r['creative_id']:
        notes.append('ad creative changed vs 11-Oct (was %s)' % r['creative_id'])
    c = crs.get(a['creative_id'])
    if c is None:
        rec['found'] = False
        notes.append('ad creative %s not found in GET /adaccounts/{id}/creatives' % a['creative_id'])
        rec['note'] = '; '.join(notes); out.append(rec); continue
    if slot is None:
        props = [k for k in ('web_view_properties','deep_link_properties','collection_properties','app_install_properties','lead_generation_properties') if k in c]
        if props:
            notes.append('NOTE: input slot null but creative now has ' + ','.join(props))
        notes.append('no URL slot: creative %s type=%s has no web_view/deep_link/collection/lead-gen/app-install properties (plain Snap ad, no attachment); url kept null as on 11-Oct' % (c['id'], c['type']))
        notes.append('creative review_status=%s' % c['review_status'])
    elif slot == 'web_view_properties.url':
        url = (c.get('web_view_properties') or {}).get('url')
        rec['url'] = url
        notes.append('creative type=%s review_status=%s updated_at=%s' % (c['type'], c['review_status'], c['updated_at']))
        if url is None:
            notes.append('creative has no web_view_properties.url now')
    else:
        m = SLOT_RE.match(slot)
        if not m:
            notes.append('UNPARSED SLOT'); rec['note'] = '; '.join(notes); out.append(rec); continue
        idx = int(m.group(1)); sub_old = m.group(2)
        kids = (c.get('composite_properties') or {}).get('creative_ids') or []
        if c['type'] != 'COMPOSITE' or idx >= len(kids):
            notes.append('creative %s is type %s with %d sub-creatives; slot position not present' % (c['id'], c['type'], len(kids)))
        else:
            sub = kids[idx]
            if sub != sub_old:
                notes.append('sub-creative at creative_ids[%d] changed vs 11-Oct: was %s, now %s' % (idx, sub_old, sub))
            sc = crs.get(sub)
            if sc is None:
                rec['found'] = False
                notes.append('sub-creative %s not found (deleted)' % sub)
            else:
                rec['url'] = (sc.get('web_view_properties') or {}).get('url')
                notes.append('composite creative %s (review_status=%s); URL read from sub-creative %s creative_ids[%d] type=%s review_status=%s updated_at=%s' % (c['id'], c['review_status'], sub, idx, sc['type'], sc['review_status'], sc['updated_at']))
    if slot is not None:
        if rec['url'] == r['url_11oct']:
            notes.append('URL unchanged vs 11-Oct')
        else:
            notes.append('URL changed vs 11-Oct')
    notes.append('adsquad.status=%s; campaign PAUSED (read 2026-10-12 ~13:50Z)' % sqs.get(a['ad_squad_id'], 'UNKNOWN'))
    rec['note'] = '; '.join(notes)
    out.append(rec)

with open(OUT, 'w') as f:
    for rec in out:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')
print('wrote', len(out))
