# Build the reread7 outputs (14-Oct ~14:49-14:51Z, partial re-read of selected rows after the team's manual changes)
# for Snapchat account b736921f-da3e-4889-8620-d3b0969c69b0 ("Visit Diriyah"). READ-ONLY: only parses saved GET results.
# usage: python3 -I build7.py <work_dir> <input.json> <out.jsonl> <scratch_root>
import json, re, sys, glob, os
from datetime import datetime, timezone
from urllib.parse import urlsplit, parse_qsl
from collections import defaultdict

W, IN, OUT, ROOT = sys.argv[1:5]
ACC = "b736921f-da3e-4889-8620-d3b0969c69b0"
ACC_NAME = "Visit Diriyah"
READ_NOTE = ("read 2026-10-14 14:49-14:51Z (reread7) via GET /v1/adaccounts/{id}/creatives (all pages, 14:49-14:50Z), "
             "/ads (all pages, 14:50-14:51Z), /adsquads, /campaigns (14:51Z)")
NOW = datetime(2026, 10, 14, 14, 50, tzinfo=timezone.utc)

inp = json.load(open(IN))
ads = json.load(open(W + '/ads_by_id.json'))
sq = json.load(open(W + '/adsquads_by_id.json'))
cp = json.load(open(W + '/campaigns_by_id.json'))
cr = json.load(open(W + '/creatives_by_id.json'))

# previous re-read of this account (reread5, 13-Oct 14:01-14:03Z), keyed by (ad_id, slot)
PREV_LABEL = '13-Oct 14:01-14:03Z re-read (reread5)'
prev = {}
pf = ROOT + '/reread5/out/snapchat_b736921fda3e48898620d3b0969c69b0.jsonl'
if os.path.exists(pf):
    for l in open(pf):
        l = l.strip()
        if l:
            x = json.loads(l)
            prev[(x['ad_id'], x['slot'])] = x


# apply-round history keyed by "unit||slot" (unit = creative id, composite creative id, or ad id)
def round_no(name):
    m = re.match(r'^apply(\d*)$', name)
    return (int(m.group(1)) if m.group(1) else 1) if m else None


units = defaultdict(list)
for f in glob.glob(ROOT + '/apply*/out_snapchat_*.jsonl'):
    rnd = os.path.relpath(f, ROOT).split('/')[0]
    if round_no(rnd) is None:
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
            {'round': rnd, 'result': r.get('result'), 'after_expected': r.get('after_expected'),
             'unit_type': r.get('unit_type'), 'new_entity_ids': r.get('new_entity_ids')})

DS_ORDER = ["INVALID_NOT_EFFECTIVE_ACTIVE", "INVALID_NO_CREATIVE_EFFECTIVE_ACTIVE", "INVALID_NOT_ACTIVE",
            "INVALID_NOT_APPROVED_REVIEW_STATUS", "INVALID_PENDING_REVIEW_STATUS", "INVALID_EFFECTIVE_INVALID"]


def canon_ds(ds):
    ds = ds or []
    return '|'.join([s for s in DS_ORDER if s in ds] + sorted(s for s in ds if s not in DS_ORDER))


def eff_status(a):
    # same derivation as the 11-Oct pull (effective_status derived from campaign/ad squad/ad status + ad review_status)
    s = sq[a['ad_squad_id']]
    c = cp[s['campaign_id']]
    if a.get('review_status') == 'REJECTED':
        return 'REJECTED'
    if c['status'] != 'ACTIVE':
        return 'CAMPAIGN_' + c['status']
    if s['status'] != 'ACTIVE':
        return 'ADSET_' + s['status']
    if a['status'] != 'ACTIVE':
        return a['status']
    if a.get('review_status') in ('PENDING', 'PENDING_REVIEW', 'IN_REVIEW'):
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
    return 'URL CHANGED vs %s: %s' % (label, '; '.join(parts))


def apply_ref(keys, url):
    hist = []
    for k in keys:
        hist += units.get(k) or []
    if not hist:
        return 'no apply-round record for this slot'
    hist = sorted(hist, key=lambda h: round_no(h['round']))
    last = hist[-1]
    if last['result'] in ('Fixed', 'AlreadyFixed'):
        if url == last.get('after_expected'):
            return 'URL = target of latest apply round (%s %s)' % (last['round'], last['result'])
        return 'URL DIFFERS from target of latest apply round (%s %s)' % (last['round'], last['result'])
    msg = 'latest apply round %s = %s (its target not applied)' % (last['round'], last['result'])
    if last.get('new_entity_ids'):
        msg += ' [%s]' % last['new_entity_ids']
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


def creative_bits(c, prefix):
    bits = ['%s type=%s review_status=%s updated_at=%s' % (prefix, c.get('type'), c.get('review_status'), c.get('updated_at'))]
    if c.get('utm_autofix_permission'):
        bits.append('utm_autofix_permission=%s' % c['utm_autofix_permission'])
    return bits


out = []
for r in inp:
    ad_id, slot = r['ad_id'], r['slot']
    rec = {"platform": "snapchat", "account_id": ACC, "ad_id": ad_id, "slot": slot, "url": None,
           "status_now": None, "creative_id_now": None, "found": False, "note": ""}
    a = ads.get(ad_id)
    if a is None:
        rec['status_now'] = 'DELETED'
        rec['note'] = 'ad not returned by GET /v1/adaccounts/{id}/ads (all pages) - deleted; ' + READ_NOTE
        out.append(rec)
        continue
    s = sq[a['ad_squad_id']]
    c = cp[s['campaign_id']]
    base = eff_status(a)
    rec['status_now'] = base
    rec['creative_id_now'] = a['creative_id']
    rec['found'] = True
    ds_now = canon_ds(a.get('delivery_status'))
    notes = ['ad.status=%s' % a['status'], 'ad.review_status=%s' % a.get('review_status'), 'ad.type=%s' % a.get('type'),
             'ad.updated_at=%s' % a.get('updated_at'),
             'adsquad.status=%s' % s['status'], 'campaign.status=%s' % c['status'],
             'delivery_status=%s' % ds_now]
    if base in ('ACTIVE', 'PENDING_REVIEW'):
        why = []
        if ended(s.get('end_time')):
            why.append('ad squad end_time %s passed' % s['end_time'])
        if ended(c.get('end_time')):
            why.append('campaign end_time %s passed' % c['end_time'])
        sds = [x for x in (s.get('delivery_status') or []) if x not in ('INVALID_END_TIME', 'INVALID_NOT_EFFECTIVE_ACTIVE', 'INVALID_EFFECTIVE_INVALID')]
        if sds:
            why.append('ad squad delivery_status ' + '|'.join(sds))
        if set(a.get('delivery_status') or []) != {'VALID'}:
            notes.append('%s but not delivering (delivery_status %s)%s' % (base, ds_now, (': ' + ', '.join(why)) if why else ''))
    if base != r['status_11oct']:
        notes.append('STATUS CHANGED vs 11-Oct (was %s)' % r['status_11oct'])
    else:
        notes.append('effective status unchanged vs 11-Oct (%s)' % base)
    m_ds = re.search(r'snapchat delivery_status=([A-Z_|]+)', r.get('notes_11oct') or '')
    if m_ds:
        if set(m_ds.group(1).split('|')) == set(a.get('delivery_status') or []):
            notes.append('delivery_status unchanged vs 11-Oct')
        else:
            notes.append('delivery_status changed vs 11-Oct (was %s)' % canon_ds(m_ds.group(1).split('|')))
    m_rs = re.search(r'ad\.review_status=(\w+)', r.get('notes_11oct') or '')
    if m_rs and m_rs.group(1) != a.get('review_status'):
        notes.append('ad review_status changed vs 11-Oct: %s -> %s' % (m_rs.group(1), a.get('review_status')))
    if a.get('review_status_reasons'):
        notes.append('ad review reasons: ' + ' / '.join(a['review_status_reasons']))
    if a['creative_id'] != r['creative_id']:
        notes.append('AD CREATIVE CHANGED vs 11-Oct (was %s)' % r['creative_id'])
    else:
        notes.append('ad creative unchanged vs 11-Oct')
    cre = cr.get(a['creative_id'])
    url = None
    url_holder = None
    ref_keys = []
    m_crs = re.search(r'creative\.review_status=(\w+)', r.get('notes_11oct') or '')
    if cre is None:
        rec['found'] = False
        notes.append('creative %s not returned by GET /v1/adaccounts/{id}/creatives (deleted)' % a['creative_id'])
    elif slot == 'creative.web_view_properties.url':
        notes += creative_bits(cre, 'creative')
        if m_crs and m_crs.group(1) != cre.get('review_status'):
            notes.append('creative review_status changed vs 11-Oct: %s -> %s' % (m_crs.group(1), cre.get('review_status')))
        wv = cre.get('web_view_properties')
        if wv is None:
            notes.append('creative has no web_view_properties now (type %s)' % cre.get('type'))
        else:
            url = wv.get('url')
        url_holder = cre
        others = sorted(users[cre['id']] - {ad_id})
        if others:
            notes.append('creative shared with %d other ad(s): %s' % (len(others), ', '.join(others)))
        ref_keys = [cre['id'] + '||' + slot, ad_id + '||' + slot]
    else:
        m = COMP_RE.match(slot or '')
        if not m:
            notes.append('UNPARSED SLOT')
        else:
            idx, sub_named = int(m.group(1)), m.group(2)
            notes.append('composite creative %s type=%s review_status=%s updated_at=%s' % (cre['id'], cre.get('type'), cre.get('review_status'), cre.get('updated_at')))
            kids = (cre.get('composite_properties') or {}).get('creative_ids') or []
            if idx >= len(kids):
                notes.append('composite has no sub-creative at index %d now (%d subs); reading the sub-creative named in the slot' % (idx, len(kids)))
                sub = sub_named
            else:
                sub = kids[idx]
                if sub != sub_named:
                    notes.append('SUB-CREATIVE AT INDEX %d CHANGED vs 11-Oct: was %s, now %s' % (idx, sub_named, sub))
                else:
                    notes.append('sub-creative at creative_ids[%d] unchanged vs 11-Oct' % idx)
            sc = cr.get(sub)
            if sc is None:
                rec['found'] = False
                notes.append('sub-creative %s not returned by GET /v1/adaccounts/{id}/creatives (deleted)' % sub)
            else:
                url = (sc.get('web_view_properties') or {}).get('url')
                url_holder = sc
                notes += creative_bits(sc, 'URL read from sub-creative %s (composite creative_ids[%d])' % (sub, idx))
                others = sorted(users[sub] - {ad_id})
                if others:
                    notes.append('sub-creative shared with %d other ad(s): %s' % (len(others), ', '.join(others)))
                else:
                    notes.append('sub-creative used only by this ad')
            ref_keys = [cre['id'] + '||' + slot, ad_id + '||' + slot]
    rec['url'] = url
    p = prev.get((ad_id, slot))
    if p is not None:
        pn = p.get('note') or ''
        m_pa = re.search(r'ad\.review_status=(\w+)', pn)
        if m_pa and m_pa.group(1) != a.get('review_status'):
            notes.append('ad review_status changed since the %s: %s -> %s' % (PREV_LABEL, m_pa.group(1), a.get('review_status')))
        m_pc = re.search(r'(?:^|; )(?:creative|URL read from sub-creative \S+ \(composite creative_ids\[\d+\]\)) type=\S+ review_status=(\w+)', pn)
        if m_pc and url_holder is not None and m_pc.group(1) != url_holder.get('review_status'):
            notes.append('URL-holding creative review_status changed since the %s: %s -> %s' % (PREV_LABEL, m_pc.group(1), url_holder.get('review_status')))
        if p.get('status_now') is not None and p.get('status_now') != base:
            notes.append('effective status changed since the %s (was %s)' % (PREV_LABEL, p.get('status_now')))
        m_pd = re.search(r'(?:^|; )delivery_status=([A-Z_|]+)', pn)
        if m_pd and m_pd.group(1) != ds_now:
            notes.append('delivery_status changed since the %s (was %s)' % (PREV_LABEL, m_pd.group(1)))
        if p.get('creative_id_now') and p.get('creative_id_now') != a['creative_id']:
            notes.append('AD CREATIVE CHANGED since the %s (was %s)' % (PREV_LABEL, p.get('creative_id_now')))
        m_pu = re.search(r'ad\.updated_at=(\S+?)(?:;|$)', pn)
        if m_pu and m_pu.group(1) != a.get('updated_at'):
            notes.append('ad edited since the %s (ad.updated_at %s -> %s)' % (PREV_LABEL, m_pu.group(1), a.get('updated_at')))
        m_pcu = re.search(r'(?:^|; )(?:creative|URL read from sub-creative \S+ \(composite creative_ids\[\d+\]\)) type=\S+ review_status=\w+ updated_at=(\S+?)(?:;|$)', pn)
        if m_pcu and url_holder is not None and m_pcu.group(1) != url_holder.get('updated_at'):
            notes.append('URL-holding creative edited since the %s (updated_at %s -> %s)' % (PREV_LABEL, m_pcu.group(1), url_holder.get('updated_at')))
        if m_pu and m_pcu and m_pu.group(1) == a.get('updated_at') and url_holder is not None and m_pcu.group(1) == url_holder.get('updated_at'):
            notes.append('no edit to the ad or its URL-holding creative since the %s (updated_at unchanged)' % PREV_LABEL)
    else:
        notes.append('row not present in the %s output' % PREV_LABEL)
    if rec['found'] or url is not None:
        notes.append(url_diff(r['url_11oct'], url, '11-Oct'))
        if p is not None and (p.get('found') or p.get('url') is not None):
            d = url_diff(p.get('url'), url, PREV_LABEL)
            notes.append(d.replace('URL CHANGED vs ' + PREV_LABEL, 'URL changed since the ' + PREV_LABEL))
    if ref_keys:
        notes.append(apply_ref(ref_keys, url))
    notes.append('UTMs embedded in web_view_properties.url (Snapchat has no separate URL-tags field)')
    notes.append(READ_NOTE)
    rec['note'] = '; '.join(notes)
    out.append(rec)

with open(OUT, 'w') as f:
    for rec in out:
        f.write(json.dumps({k: rec[k] for k in ["platform", "account_id", "ad_id", "slot", "url", "status_now",
                                                "creative_id_now", "found", "note"]}, ensure_ascii=False) + '\n')

# Task 2 is skipped for this partial re-read (no new_file is written).

print('rows', len(out), 'found', sum(1 for x in out if x['found']), 'not_found', sum(1 for x in out if not x['found']),
      'url_changed_vs_11oct', sum(1 for x, r in zip(out, inp) if x['url'] != r['url_11oct']),
      'url_changed_vs_reread5', sum(1 for x in out if (x['ad_id'], x['slot']) in prev and prev[(x['ad_id'], x['slot'])].get('url') != x['url']),
      'rows_missing_in_reread5', sum(1 for x in out if (x['ad_id'], x['slot']) not in prev),
      'status_changed_vs_11oct', sum(1 for x, r in zip(out, inp) if x['status_now'] != r['status_11oct']),
      'status_changed_vs_reread5', sum(1 for x in out if (x['ad_id'], x['slot']) in prev and prev[(x['ad_id'], x['slot'])].get('status_now') != x['status_now']),
      'ads_edited_since_reread5', sum(1 for x in out if 'ad edited since' in x['note']),
      'creatives_edited_since_reread5', sum(1 for x in out if 'URL-holding creative edited since' in x['note']))
