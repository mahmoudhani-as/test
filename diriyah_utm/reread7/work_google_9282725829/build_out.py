"""Build reread7/out/google_9282725829.jsonl (one line per input row) and new_google_9282725829.jsonl
from the GAQL results that extract.py saved (verbatim) into <work>/res/*.json.
Usage: python3 -I build_out.py <diriyah_utm root> <work dir>
"""
import json, sys, glob, os, re, collections

ROOT, W = sys.argv[1], sys.argv[2]
ACC = '9282725829'
ACC_NAME = 'H&S - DGCL - Diriyah Gate'
ODIR = sys.argv[3] if len(sys.argv) > 3 else f'{ROOT}/reread7/out'
OUT = f'{ODIR}/google_{ACC}.jsonl'
NEW = f'{ODIR}/new_google_{ACC}.jsonl'

inp = json.load(open(f'{ROOT}/reread/in/google_{ACC}.json'))
live = [json.loads(l) for l in open(f'{ROOT}/live/google_{ACC}.jsonl')]
assert len(inp) == len(live) == 955
for a, b in zip(inp, live):
    assert a['ad_id'] == b['ad_id'] and a['slot'] == b['slot']
prev = [json.loads(l) for l in open(f'{ROOT}/reread5/out/google_{ACC}.jsonl')]   # 12-Oct read-back (== reread2)
assert len(prev) == len(inp)
for a, b in zip(inp, prev):
    assert a['ad_id'] == b['ad_id'] and a['slot'] == b['slot']

# ---------------- load verbatim GAQL results ----------------
res = []
for f in sorted(glob.glob(os.path.join(W, 'res', '*.json'))):
    o = json.load(open(f))
    q = o['query'] or ''
    if o['truncated'] or re.search(r'\bLIMIT\b', q):
        continue          # incomplete / probe calls are not used
    res.append((f, q, o['results']))

customer_suffix = None
camps = {}
ads = {}
assets = {}
ca_links = {}
aga_links = {}
names = {}
for f, q, rows in res:
    frm = re.search(r'\bFROM\s+(\w+)', q).group(1)
    if frm == 'customer':
        customer_suffix = rows[0]['customer'].get('finalUrlSuffix') or ''
    elif frm == 'campaign':
        for r in rows:
            c = r['campaign']
            camps[c['id']] = dict(status=c.get('status'), serving=c.get('servingStatus'), name=c.get('name'),
                                  suffix=c.get('finalUrlSuffix') or '')
    elif frm == 'ad_group_ad':
        for r in rows:
            aga = r['adGroupAd']; ad = aga['ad']
            if 'adGroup' in r and 'status' in r['adGroup']:
                rec = dict(ag=r['adGroup']['id'], ag_status=r['adGroup'].get('status'),
                           ag_suffix=r['adGroup'].get('finalUrlSuffix') or '',
                           camp=r['campaign']['id'], camp_status=r['campaign'].get('status'),
                           camp_suffix=r['campaign'].get('finalUrlSuffix') or '',
                           status=aga.get('status'), primary=aga.get('primaryStatus'),
                           urls=ad.get('finalUrls') or [], suffix=ad.get('finalUrlSuffix') or '')
                old = ads.get(ad['id'])
                assert old is None or old == rec, ('conflicting reads', ad['id'])
                ads[ad['id']] = rec
            if 'name' in r.get('campaign', {}) or 'name' in r.get('adGroup', {}):
                names[ad['id']] = dict(campaign_name=r.get('campaign', {}).get('name'),
                                       adset_name=r.get('adGroup', {}).get('name'),
                                       ad_name=ad.get('name'), ad_type=ad.get('type'))
    elif frm == 'asset':
        for r in rows:
            a = r['asset']
            assets[a['id']] = dict(urls=a.get('finalUrls') or [], suffix=a.get('finalUrlSuffix') or '')
    elif frm == 'campaign_asset':
        for r in rows:
            m = re.search(r'campaignAssets/(\d+)~(\d+)~(\w+)$', r['campaignAsset']['resourceName'])
            assert m.group(3) == 'SITELINK'
            ca_links[(m.group(1), m.group(2))] = r['campaignAsset']['status']
    elif frm == 'ad_group_asset':
        for r in rows:
            m = re.search(r'adGroupAssets/(\d+)~(\d+)~(\w+)$', r['adGroupAsset']['resourceName'])
            assert m.group(3) == 'SITELINK'
            aga_links[(m.group(1), m.group(2))] = r['adGroupAsset']['status']

assert customer_suffix is not None, 'customer not read'
print('loaded: campaigns', len(camps), 'ads', len(ads), 'assets', len(assets), 'ca_links', len(ca_links),
      'aga_links', len(aga_links), 'names', len(names), 'customer_suffix', repr(customer_suffix))

adgroups = {}
for a in ads.values():
    adgroups[a['ag']] = dict(status=a['ag_status'], suffix=a['ag_suffix'], campaign=a['camp'])


def add_suffix(url, suffix):
    if not suffix:
        return url
    base, hash_, frag = url.partition('#')
    sep = '&' if '?' in base else '?'
    return base + sep + suffix.lstrip('?&') + hash_ + frag


def eff_status(c_st, ag_st, own_st):
    if c_st and c_st != 'ENABLED':
        return 'CAMPAIGN_' + c_st
    if ag_st and ag_st != 'ENABLED':
        return 'AD_GROUP_' + ag_st
    if own_st and own_st != 'ENABLED':
        return own_st
    return 'ENABLED'


def cmp_note(url, r, p):
    s = 'unchanged vs 11-Oct' if url == r['url_11oct'] else 'CHANGED vs 11-Oct'
    pu = p.get('url')
    s += '; same as 12-Oct read-back' if url == pu else '; DIFFERS from 12-Oct read-back (was %s)' % pu
    return s


out = []
stats = collections.Counter()
for r, l, p in zip(inp, live, prev):
    rec = {"platform": "google", "account_id": ACC, "ad_id": r['ad_id'], "slot": r['slot']}
    if r['slot'] == 'ad.final_urls[0]':
        ad = ads.get(r['ad_id'])
        if ad is None:
            rec.update(url=None, status_now='REMOVED', creative_id_now=None, found=False,
                       note='ad not returned by GAQL ad_group_ad WHERE ad_group_ad.status != REMOVED (removed/deleted since 11-Oct)')
            stats['ad_gone'] += 1
            out.append(rec)
            continue
        c = camps.get(ad['camp'], {})
        sfx, src = '', 'none set at ad/ad group/campaign/customer'
        if ad['suffix']:
            sfx, src = ad['suffix'], 'ad.final_url_suffix'
        elif ad['ag_suffix']:
            sfx, src = ad['ag_suffix'], 'ad_group.final_url_suffix'
        elif ad['camp_suffix']:
            sfx, src = ad['camp_suffix'], 'campaign.final_url_suffix'
        elif customer_suffix:
            sfx, src = customer_suffix, 'customer.final_url_suffix'
        url = add_suffix(ad['urls'][0], sfx) if ad['urls'] else None
        status_now = eff_status(ad['camp_status'], ad['ag_status'], ad['status'])
        notes = [cmp_note(url, r, p), f"final_urls[0] + effective final_url_suffix ({src})",
                 f"campaign={c.get('name') or l['campaign_name']} [{ad['camp_status']}/{c.get('serving')}]",
                 f"ad_group={l['adset_name']} [{ad['ag_status']}]",
                 f"ad_status={ad['status']}; primary_status={ad['primary']}",
                 "Google has no separate creative id (11-Oct creative_id null)"]
        if len(ad['urls']) > 1:
            notes.append(f"ad now has {len(ad['urls'])} final_urls")
        if ad['ag'] != l['adset_id']:
            notes.append(f"AD GROUP CHANGED: now {ad['ag']} (11-Oct {l['adset_id']})")
        if status_now != r['status_11oct']:
            notes.append(f"status changed since 11-Oct (was {r['status_11oct']})")
        if status_now != p.get('status_now'):
            notes.append(f"status changed since 12-Oct read-back (was {p.get('status_now')})")
        rec.update(url=url, status_now=status_now, creative_id_now=None, found=True, note='; '.join(notes))
        stats['ad_ok'] += 1
    else:
        m = re.match(r'sitelink asset (\d+) final_urls\[(\d+)\] \((campaign_asset|ad_group_asset)\)$', r['slot'])
        assert m and m.group(1) == r['ad_id'], r['slot']
        idx, kind = int(m.group(2)), m.group(3)
        a = assets.get(r['ad_id'])
        if a is None:
            rec.update(url=None, status_now='REMOVED', creative_id_now=None, found=False,
                       note='sitelink asset not returned by GAQL asset query (asset deleted)')
            stats['asset_gone'] += 1
            out.append(rec)
            continue
        cid = l['campaign_id']
        c = camps.get(cid, {})
        ag = adgroups.get(l['adset_id']) if kind == 'ad_group_asset' else None
        sfx, src = '', 'none set at asset/ad group/campaign/customer'
        if a['suffix']:
            sfx, src = a['suffix'], 'asset.final_url_suffix'
        elif ag and ag['suffix']:
            sfx, src = ag['suffix'], 'ad_group.final_url_suffix'
        elif c.get('suffix'):
            sfx, src = c['suffix'], 'campaign.final_url_suffix'
        elif customer_suffix:
            sfx, src = customer_suffix, 'customer.final_url_suffix'
        url = add_suffix(a['urls'][idx], sfx) if idx < len(a['urls']) else None
        if kind == 'campaign_asset':
            lst = ca_links.get((cid, r['ad_id']))
            link_id = f"{cid}~{r['ad_id']}~SITELINK"
        else:
            lst = aga_links.get((l['adset_id'], r['ad_id']))
            link_id = f"{l['adset_id']}~{r['ad_id']}~SITELINK"
        if lst is None:
            status_now = 'REMOVED'
            link_note = f"{kind} link {link_id} not among non-removed SITELINK links now (link removed since 11-Oct; asset itself still exists)"
            stats['link_gone'] += 1
        else:
            status_now = eff_status(c.get('status'), ag['status'] if ag else None, lst)
            link_note = f"row mapped to {kind} link {link_id} (link status {lst})"
        n_links = sum(1 for k in ca_links if k[1] == r['ad_id']) + sum(1 for k in aga_links if k[1] == r['ad_id'])
        notes = [cmp_note(url, r, p), f"asset.final_urls[{idx}] + effective final_url_suffix ({src})", link_note,
                 f"campaign={c.get('name') or l['campaign_name']} [{c.get('status')}/{c.get('serving')}]"]
        if kind == 'ad_group_asset':
            notes.append(f"ad_group={l['adset_name']} [{ag['status'] if ag else '?'}]")
        notes.append(f"asset has {n_links} non-removed SITELINK link(s) among the 11-Oct placements re-read (one asset URL serves all of them)")
        if len(a['urls']) > 1:
            notes.append(f"asset now has {len(a['urls'])} final_urls")
        if status_now != r['status_11oct']:
            notes.append(f"status changed since 11-Oct (was {r['status_11oct']})")
        if status_now != p.get('status_now'):
            notes.append(f"status changed since 12-Oct read-back (was {p.get('status_now')})")
        rec.update(url=url, status_now=status_now, creative_id_now=None, found=True, note='; '.join(notes))
        stats['sitelink_ok'] += 1
    out.append(rec)

os.makedirs(ODIR, exist_ok=True)
with open(OUT, 'w') as f:
    for rec in out:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')
print('wrote', OUT, len(out), dict(stats))

# ---------------- TASK 2: ads not in the input ----------------
in_ads = set(r['ad_id'] for r in inp if r['slot'] == 'ad.final_urls[0]')
new_lines = []
for ad_id, ad in sorted(ads.items()):
    if ad_id in in_ads:
        continue
    nm = names.get(ad_id, {})
    c = camps.get(ad['camp'], {})
    sfx = ad['suffix'] or ad['ag_suffix'] or ad['camp_suffix'] or customer_suffix
    st = eff_status(ad['camp_status'], ad['ag_status'], ad['status'])
    for i, u in enumerate(ad['urls']):
        new_lines.append({"platform": "google", "account_id": ACC, "account_name": ACC_NAME,
                          "campaign_name": nm.get('campaign_name') or c.get('name'),
                          "adset_name": nm.get('adset_name'), "ad_id": ad_id, "ad_name": nm.get('ad_name'),
                          "effective_status": st, "slot": f"ad.final_urls[{i}]", "url": add_suffix(u, sfx)})
with open(NEW, 'w') as f:
    for rec in new_lines:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')
print('wrote', NEW, len(new_lines), 'lines for', len(set(x['ad_id'] for x in new_lines)), 'new ads')
