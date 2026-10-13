# Build the 13-Oct re-read outputs for Snapchat account b736921f-da3e-4889-8620-d3b0969c69b0 ("Visit Diriyah").
# usage: python3 -I build.py <work_dir> <input.json> <out.jsonl> <new_out.jsonl> <scratch_root>
import json, re, sys, glob, os
from datetime import datetime, timezone
from urllib.parse import urlsplit, parse_qsl
from collections import defaultdict

W, IN, OUT, NEW, ROOT = sys.argv[1:6]
ACC = "b736921f-da3e-4889-8620-d3b0969c69b0"
ACC_NAME = "Visit Diriyah"
READ_AT = "2026-10-13 ~10:14-10:17Z"
NOW = datetime(2026, 10, 13, 10, 17, tzinfo=timezone.utc)

inp = json.load(open(IN))
ads = json.load(open(W + '/ads_by_id.json'))
sq = json.load(open(W + '/adsquads_by_id.json'))
cp = json.load(open(W + '/campaigns_by_id.json'))
cr = json.load(open(W + '/creatives_by_id.json'))

# previous (12-Oct) re-read, keyed by (ad_id, slot)
prev = {}
pf = ROOT + '/reread2/out/snapchat_b736921fda3e48898620d3b0969c69b0.jsonl'
if os.path.exists(pf):
    for l in open(pf):
        l = l.strip()
        if l:
            x = json.loads(l)
            prev[(x['ad_id'], x['slot'])] = x

# apply-round history keyed by "unit||slot"
ROUND_ORDER = ['apply', 'apply2', 'apply3', 'apply4', 'apply5', 'apply6', 'apply7', 'apply8']
units = defaultdict(list)
for f in glob.glob(ROOT + '/apply*/out_snapchat_*.jsonl'):
    rnd = os.path.relpath(f, ROOT).split('/')[0]
    if rnd not in ROUND_ORDER:
        continue
    for line in open(f):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get('account_id') != ACC:
            continue
        units[(r.get('unit') or '') + '||' + (r.get('slot') or '')].append(
            {'round': rnd, 'result': r.get('result'), 'after_expected': r.get('after_expected')})

DS_ORDER = ["INVALID_NOT_EFFECTIVE_ACTIVE", "INVALID_NO_CREATIVE_EFFECTIVE_ACTIVE", "INVALID_NOT_ACTIVE",
            "INVALID_NOT_APPROVED_REVIEW_STATUS", "INVALID_PENDING_REVIEW_STATUS", "INVALID_EFFECTIVE_INVALID"]
def canon_ds(ds):
    ds = ds or []
    return '|'.join([s for s in DS_ORDER if s in ds] + sorted(s for s in ds if s not in DS_ORDER))

def eff_status(a):
    # same derivation as the 11-Oct pull and the 12-Oct re-read
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

def ended(ts):
    if not ts:
        return False
    return datetime.fromisoformat(ts.replace('Z', '+00:00')) < NOW

def url_diff(old, new, label):
    if old == new:
        return 'URL unchanged vs %s' % label
    if old is None:
        return 'URL now present (was null on %s)' % label
    if new is None:
        return 'URL now missing (was set on %s)' % label
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
    if o.fragment != n.fragment:
        parts.append('fragment: %r -> %r' % (o.fragment, n.fragment))
    if not parts:
        parts.append('query order/encoding differs')
    return 'URL changed vs %s: %s' % (label, '; '.join(parts))

def apply_ref(key, url):
    hist = units.get(key) or []
    if not hist:
        return 'no apply-round record for this slot'
    hist = sorted(hist, key=lambda h: ROUND_ORDER.index(h['round']))
    last = hist[-1]
    if last['result'] in ('Fixed', 'AlreadyFixed'):
        if url == last.get('after_expected'):
            return 'URL = target of latest apply round (%s %s)' % (last['round'], last['result'])
        return 'URL DIFFERS from target of latest apply round (%s %s)' % (last['round'], last['result'])
    msg = 'latest apply round %s = %s (its target not applied)' % (last['round'], last['result'])
    if url == last.get('after_expected'):
        return msg + ', but URL already equals that target'
    for h in reversed(hist[:-1]):
        if h['result'] in ('Fixed', 'AlreadyFixed') and url == h.get('after_expected'):
            return msg + '; URL = value set by %s (%s)' % (h['round'], h['result'])
    return msg

# which ads use each creative (directly or as a composite sub-creative)
users = defaultdict(set)
for a in ads.values():
    users[a['creative_id']].add(a['id'])
    c = cr.get(a['creative_id'])
    if c and c.get('type') == 'COMPOSITE':
        for sub in (c.get('composite_properties') or {}).get('creative_ids') or []:
            users[sub].add(a['id'])

COMP_RE = re.compile(r'^creative\.composite_properties\.creative_ids\[(\d+)\] -> creative ([0-9a-f-]{36}) \.web_view_properties\.url$')

out = []
for r in inp:
    ad_id, slot = r['ad_id'], r['slot']
    rec = {"platform": "snapchat", "account_id": ACC, "ad_id": ad_id, "slot": slot, "url": None,
           "status_now": None, "creative_id_now": None, "found": False, "note": ""}
    a = ads.get(ad_id)
    if a is None:
        rec['note'] = 'ad not returned by GET /v1/adaccounts/{id}/ads on 13-Oct (deleted)'
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
             'delivery_status=%s' % canon_ds(a.get('delivery_status'))]
    if st in ('ACTIVE', 'PENDING_REVIEW'):
        why = []
        if ended(s.get('end_time')):
            why.append('ad squad end_time %s passed' % s['end_time'])
        if ended(c.get('end_time')):
            why.append('campaign end_time %s passed' % c['end_time'])
        if 'INVALID_EFFECTIVE_INVALID' in (a.get('delivery_status') or []):
            why.append('ad delivery_status INVALID_EFFECTIVE_INVALID')
        if why:
            notes.append('not delivering: ' + ', '.join(why))
    if st != r['status_11oct']:
        notes.append('STATUS CHANGED vs 11-Oct (was %s)' % r['status_11oct'])
    m_rs = re.search(r'ad\.review_status=(\w+)', r.get('notes_11oct') or '')
    if m_rs and m_rs.group(1) != a['review_status']:
        notes.append('ad review_status changed vs 11-Oct: %s -> %s' % (m_rs.group(1), a['review_status']))
    if a.get('review_status_reasons'):
        notes.append('ad review reasons: ' + ' / '.join(a['review_status_reasons']))
    if a['creative_id'] != r['creative_id']:
        notes.append('AD CREATIVE CHANGED vs 11-Oct (was %s)' % r['creative_id'])
    cre = cr.get(a['creative_id'])
    url = None
    ref_key = None
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
        others = sorted(users[cre['id']] - {ad_id})
        if others:
            notes.append('creative shared with ad(s) %s' % ', '.join(others))
        ref_key = cre['id'] + '||' + slot
    else:
        m = COMP_RE.match(slot or '')
        if not m:
            notes.append('UNPARSED SLOT')
        else:
            idx, sub_old = int(m.group(1)), m.group(2)
            notes.append('composite creative %s type=%s review_status=%s updated_at=%s' % (cre['id'], cre['type'], cre['review_status'], cre['updated_at']))
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
                    others = sorted(users[sub] - {ad_id})
                    if others:
                        notes.append('sub-creative shared with ad(s) %s' % ', '.join(others))
                    ref_key = cre['id'] + '||' + slot
    rec['url'] = url
    if rec['found'] or url is not None:
        notes.append(url_diff(r['url_11oct'], url, '11-Oct'))
        p = prev.get((ad_id, slot))
        if p is not None and (p.get('found') or p.get('url') is not None):
            notes.append(url_diff(p.get('url'), url, '12-Oct re-read').replace('URL changed vs 12-Oct re-read', 'changed since 12-Oct re-read'))
    if ref_key:
        notes.append(apply_ref(ref_key, url))
    notes.append('UTMs live inside web_view_properties.url (Snapchat has no separate url_tags field)')
    notes.append('read via GET /v1/adaccounts/{id}/ads, /adsquads, /campaigns, /creatives on %s' % READ_AT)
    rec['note'] = '; '.join(notes)
    out.append(rec)

with open(OUT, 'w') as f:
    for rec in out:
        f.write(json.dumps({k: rec[k] for k in ["platform", "account_id", "ad_id", "slot", "url", "status_now",
                                                "creative_id_now", "found", "note"]}, ensure_ascii=False) + '\n')

# Task 2: ads not in the input (the ads list never returns deleted ads)
in_ids = {r['ad_id'] for r in inp}
new_rows = []
for a in sorted(ads.values(), key=lambda x: x['id']):
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
