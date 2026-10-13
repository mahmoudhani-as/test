import json, re, sys
from urllib.parse import urlsplit, parse_qsl

W, IN, OUT, NEW, CAND = sys.argv[1:6]
ACC = "b736921f-da3e-4889-8620-d3b0969c69b0"
ACC_NAME = "Visit Diriyah"

inp = json.load(open(IN))
ads = {a['id']: a for a in json.load(open(W + '/ads.json'))}
sq = {s['id']: s for s in json.load(open(W + '/squads_all.json'))}
cp = {c['id']: c for c in json.load(open(W + '/campaigns_transcribed.json'))}
cr = json.load(open(W + '/creatives.json'))
extra = json.load(open(W + '/extra_reasons.json'))
cand = json.load(open(CAND))
units = cand['units']

ROUND_ORDER = ['apply/', 'apply2/', 'apply3/', 'apply4/', 'apply5/', 'apply6/', 'apply7/']
def round_idx(f):
    for i, p in enumerate(ROUND_ORDER):
        if f.startswith(p):
            return i
    return -1

DS_ORDER = ["INVALID_NOT_EFFECTIVE_ACTIVE", "INVALID_NO_CREATIVE_EFFECTIVE_ACTIVE", "INVALID_NOT_ACTIVE",
            "INVALID_NOT_APPROVED_REVIEW_STATUS", "INVALID_PENDING_REVIEW_STATUS", "INVALID_EFFECTIVE_INVALID"]
def canon_ds(ds):
    return '|'.join([s for s in DS_ORDER if s in ds] + sorted(s for s in ds if s not in DS_ORDER))

def eff_status(a):
    s = sq[a['ad_squad_id']]
    c = cp[s['campaign_id']]
    if a['review_status'] == 'REJECTED':
        return 'REJECTED'
    if c['status'] != 'ACTIVE':
        return 'CAMPAIGN_' + c['status']
    if s['status'] != 'ACTIVE':
        return 'ADSET_' + s['status']
    if a['status'] != 'ACTIVE':
        return a['status']
    if a['review_status'] in ('PENDING', 'PENDING_REVIEW', 'IN_REVIEW'):
        return 'PENDING_REVIEW'
    return 'ACTIVE'

def url_diff(old, new):
    if old == new:
        return 'URL unchanged vs 11-Oct'
    if old is None:
        return 'URL now present (was null on 11-Oct)'
    if new is None:
        return 'URL now missing (was set on 11-Oct)'
    o, n = urlsplit(old), urlsplit(new)
    parts = []
    if (o.scheme, o.netloc, o.path) != (n.scheme, n.netloc, n.path):
        parts.append('base changed %s://%s%s -> %s://%s%s' % (o.scheme, o.netloc, o.path, n.scheme, n.netloc, n.path))
    oq, nq = parse_qsl(o.query, keep_blank_values=True), parse_qsl(n.query, keep_blank_values=True)
    od, nd = dict(oq), dict(nq)
    for k, v in nq:
        if k not in od:
            parts.append('+%s=%s' % (k, v))
        elif od[k] != v:
            parts.append('%s: %s -> %s' % (k, od[k], v))
    for k, v in oq:
        if k not in nd:
            parts.append('-%s (was %s)' % (k, v))
    if not parts:
        parts.append('query order/encoding differs')
    return 'URL changed vs 11-Oct: ' + '; '.join(parts)

def apply_ref(key, url):
    hist = units.get(key) or []
    if not hist:
        return 'no apply-round record for this slot'
    hist = sorted(hist, key=lambda h: round_idx(h['file']))
    last = hist[-1]
    rnd = last['file'].split('/')[0]
    if last['result'] in ('Fixed', 'AlreadyFixed'):
        if url == last.get('after_expected'):
            return 'URL = target of latest apply round (%s %s)' % (rnd, last['result'])
        return 'URL DIFFERS from target of latest apply round (%s %s)' % (rnd, last['result'])
    msg = 'latest apply round %s = %s (its target not applied)' % (rnd, last['result'])
    if url == last.get('after_expected'):
        return msg + ', but URL already equals that target'
    for h in reversed(hist[:-1]):
        if h['result'] in ('Fixed', 'AlreadyFixed') and url == h.get('after_expected'):
            return msg + '; URL = value set by %s (%s)' % (h['file'].split('/')[0], h['result'])
    return msg

COMP_RE = re.compile(r'^creative\.composite_properties\.creative_ids\[(\d+)\] -> creative ([0-9a-f-]{36}) \.web_view_properties\.url$')

out = []
for r in inp:
    ad_id, slot = r['ad_id'], r['slot']
    rec = {"platform": "snapchat", "account_id": ACC, "ad_id": ad_id, "slot": slot, "url": None,
           "status_now": None, "creative_id_now": None, "found": False, "note": ""}
    a = ads.get(ad_id)
    if a is None:
        rec['note'] = 'ad not returned by GET /v1/adaccounts/{id}/ads on 12-Oct (deleted)'
        out.append(rec)
        continue
    s = sq[a['ad_squad_id']]
    c = cp[s['campaign_id']]
    st = eff_status(a)
    rec['status_now'] = st
    rec['creative_id_now'] = a['creative_id']
    rec['found'] = True
    notes = ['ad.status=%s' % a['status'], 'ad.review_status=%s' % a['review_status'],
             'adsquad.status=%s' % s['status'], 'campaign.status=%s' % c['status'],
             'delivery_status=%s' % canon_ds(a['delivery_status'])]
    if st != r['status_11oct']:
        notes.append('STATUS CHANGED vs 11-Oct (was %s)' % r['status_11oct'])
    m_rs = re.search(r'ad\.review_status=(\w+)', r.get('notes_11oct') or '')
    if m_rs and m_rs.group(1) != a['review_status']:
        notes.append('ad review_status changed vs 11-Oct: %s -> %s' % (m_rs.group(1), a['review_status']))
    if ad_id in extra:
        notes.append(extra[ad_id])
    elif a.get('review_status_reasons'):
        notes.append('ad review reasons: ' + ' / '.join(a['review_status_reasons']))
    if a['creative_id'] != r['creative_id']:
        notes.append('AD CREATIVE CHANGED vs 11-Oct (was %s)' % r['creative_id'])
    cre = cr.get(a['creative_id'])
    url = None
    ref_cid = None
    if cre is None:
        rec['found'] = False
        notes.append('creative %s not found in GET /v1/adaccounts/{id}/creatives (deleted)' % a['creative_id'])
    elif slot == 'creative.web_view_properties.url':
        notes.append('creative.type=%s' % cre['type'])
        notes.append('creative.review_status=%s' % cre['review_status'])
        notes.append('creative.updated_at=%s' % cre['updated_at'])
        wv = cre.get('web_view_properties')
        if wv is None:
            notes.append('creative has no web_view_properties now')
        else:
            url = wv.get('url')
        ref_cid = cre['id'] + '||' + slot
    else:
        m = COMP_RE.match(slot or '')
        if not m:
            notes.append('UNPARSED SLOT')
        else:
            idx, sub_old = int(m.group(1)), m.group(2)
            notes.append('composite creative %s type=%s review_status=%s' % (cre['id'], cre['type'], cre['review_status']))
            kids = (cre.get('composite_properties') or {}).get('creative_ids') or []
            if idx >= len(kids):
                notes.append('composite has no sub-creative at index %d now (%d subs)' % (idx, len(kids)))
            else:
                sub = kids[idx]
                if sub != sub_old:
                    notes.append('SUB-CREATIVE AT INDEX %d CHANGED vs 11-Oct: was %s, now %s' % (idx, sub_old, sub))
                sc = cr.get(sub)
                if sc is None:
                    rec['found'] = False
                    notes.append('sub-creative %s not found (deleted)' % sub)
                else:
                    url = (sc.get('web_view_properties') or {}).get('url')
                    notes.append('URL read from sub-creative %s creative_ids[%d] type=%s review_status=%s updated_at=%s' % (
                        sub, idx, sc['type'], sc['review_status'], sc['updated_at']))
                    ref_cid = cre['id'] + '||' + slot
    rec['url'] = url
    if rec['found'] or url is not None:
        notes.append(url_diff(r['url_11oct'], url))
    if ref_cid:
        ar = apply_ref(ref_cid, url)
        if ar:
            notes.append(ar)
    notes.append('read via GET /v1/adaccounts/{id}/ads, /adsquads, /campaigns, /creatives on 2026-10-12 ~22:45-22:55Z')
    rec['note'] = '; '.join(notes)
    out.append(rec)

with open(OUT, 'w') as f:
    for rec in out:
        f.write(json.dumps({k: rec[k] for k in ["platform", "account_id", "ad_id", "slot", "url", "status_now",
                                                "creative_id_now", "found", "note"]}, ensure_ascii=False) + '\n')

# Task 2: ads not in the input
in_ids = {r['ad_id'] for r in inp}
new_rows = []
for a in ads.values():
    if a['id'] in in_ids:
        continue
    s = sq[a['ad_squad_id']]
    c = cp[s['campaign_id']]
    cre = cr.get(a['creative_id'])
    slots = []
    if cre is not None:
        if cre['type'] == 'COMPOSITE':
            for i, sub in enumerate((cre.get('composite_properties') or {}).get('creative_ids') or []):
                sc = cr.get(sub) or {}
                slots.append(('creative.composite_properties.creative_ids[%d] -> creative %s .web_view_properties.url' % (i, sub),
                              (sc.get('web_view_properties') or {}).get('url')))
        else:
            slots.append(('creative.web_view_properties.url', (cre.get('web_view_properties') or {}).get('url')))
    else:
        slots.append(('creative.web_view_properties.url', None))
    for sl, u in slots:
        new_rows.append({"platform": "snapchat", "account_id": ACC, "account_name": ACC_NAME,
                         "campaign_name": c['name'], "adset_name": s['name'], "ad_id": a['id'], "ad_name": a['name'],
                         "effective_status": eff_status(a), "slot": sl, "url": u})
with open(NEW, 'w') as f:
    for x in new_rows:
        f.write(json.dumps(x, ensure_ascii=False) + '\n')
print('rows', len(out), 'new rows', len(new_rows), 'new ads', len({x['ad_id'] for x in new_rows}))
