"""Build reread2/out/google_8324286739.jsonl (one line per input row, same order) and
reread2/out/new_google_8324286739.jsonl from the GAQL results saved in ../raw/ (parsed straight
from the persisted MCP tool-result files by grab.py; nothing transcribed by hand).
Usage: python3 -I build_out.py <diriyah_utm root dir> [--dry]"""
import json, sys, glob, os, re, collections

ROOT = sys.argv[1]
DRY = '--dry' in sys.argv
W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(W, 'raw')
ACC = '8324286739'
ACC_NAME = 'H&S - DGCL - Visit Diriyah'
INP = f'{ROOT}/reread/in/google_{ACC}.json'
LIVE = f'{ROOT}/live/google_{ACC}.jsonl'
OUT = f'{ROOT}/reread2/out/google_{ACC}.jsonl'
NEW = f'{ROOT}/reread2/out/new_google_{ACC}.jsonl'
CUSTOMER_SUFFIX = ''   # customer.final_url_suffix not set (GAQL FROM customer, read 12-Oct)

inp = json.load(open(INP))
live = [json.loads(l) for l in open(LIVE)]
assert len(inp) == len(live)
for a, b in zip(inp, live):
    assert a['ad_id'] == b['ad_id'] and a['slot'] == b['slot']


def load(prefix):
    out = []
    for f in sorted(glob.glob(os.path.join(RAW, prefix + '*.json'))):
        out.extend(json.load(open(f))['results'])
    return out


def merge(store, key, rec, what):
    if key in store and store[key] != rec:
        raise SystemExit(f'{what} {key} differs between pages:\n{store[key]}\n{rec}')
    store[key] = rec


# ---------------- ads (ad_group_ad, status != REMOVED) ----------------
ads, camps, adgroups = {}, {}, {}
for x in load('ads_p'):
    c, g, aga = x['campaign'], x['adGroup'], x['adGroupAd']
    ad = aga['ad']
    merge(camps, c['id'], dict(status=c.get('status'), serving=c.get('servingStatus'), suffix=c.get('finalUrlSuffix') or ''), 'campaign')
    merge(adgroups, g['id'], dict(status=g.get('status'), suffix=g.get('finalUrlSuffix') or '', cid=c['id']), 'ad group')
    merge(ads, ad['id'], dict(ag=g['id'], cid=c['id'], status=aga.get('status'), primary=aga.get('primaryStatus'),
                              type=ad.get('type'), urls=ad.get('finalUrls') or [], suffix=ad.get('finalUrlSuffix') or ''), 'ad')

# ads of the input that the != REMOVED read did not return: read by id with any status
gone = {}
for x in load('adsgone_p'):
    aga = x['adGroupAd']
    gone[aga['ad']['id']] = dict(status=aga.get('status'), ag=x.get('adGroup', {}).get('id'),
                                 cid=x.get('campaign', {}).get('id'))

# ---------------- sitelink assets ----------------
assets = {}
for x in load('assets_p'):
    a = x['asset']
    merge(assets, a['id'], dict(urls=a.get('finalUrls') or [], suffix=a.get('finalUrlSuffix') or '',
                                text=(a.get('sitelinkAsset') or {}).get('linkText')), 'asset')

# ---------------- sitelink links (GAQL filtered to status != REMOVED) ----------------
ca_links, aga_links = {}, {}
for x in load('calinks_p'):
    ca = x['campaignAsset']
    m = re.fullmatch(r'customers/%s/campaignAssets/(\d+)~(\d+)~SITELINK' % ACC, ca['resourceName'])
    assert m, ca['resourceName']
    c = x['campaign']
    assert c['id'] == m.group(1) and x['asset']['id'] == m.group(2)
    # campaign.final_url_suffix was not selected here: compare status / serving status only
    if c['id'] in camps:
        assert (camps[c['id']]['status'], camps[c['id']]['serving']) == (c.get('status'), c.get('servingStatus')), c
    else:
        camps[c['id']] = dict(status=c.get('status'), serving=c.get('servingStatus'), suffix=None)
    merge(ca_links, (m.group(1), m.group(2)), ca.get('status'), 'campaign_asset')
for x in load('agalinks_p'):
    ga = x['adGroupAsset']
    m = re.fullmatch(r'customers/%s/adGroupAssets/(\d+)~(\d+)~SITELINK' % ACC, ga['resourceName'])
    assert m, ga['resourceName']
    g = x['adGroup']
    assert g['id'] == m.group(1)
    # campaign not selected here: ad groups already seen in the ad read keep their campaign id
    if g['id'] in adgroups:
        assert (adgroups[g['id']]['status'], adgroups[g['id']]['suffix']) == (g.get('status'), g.get('finalUrlSuffix') or ''), g
    else:
        adgroups[g['id']] = dict(status=g.get('status'), suffix=g.get('finalUrlSuffix') or '', cid=None)
    merge(aga_links, (m.group(1), m.group(2)), ga.get('status'), 'ad_group_asset')

# extra campaign / ad group reads (names for new ads, parents not seen elsewhere)
names_c, names_g, names_ad = {}, {}, {}
for x in load('camps_p'):
    c = x['campaign']
    names_c[c['id']] = c.get('name')
    merge(camps, c['id'], dict(status=c.get('status'), serving=c.get('servingStatus'), suffix=c.get('finalUrlSuffix') or ''), 'campaign')
for x in load('newads_p'):
    aga = x['adGroupAd']
    names_ad[aga['ad']['id']] = aga['ad'].get('name')
    names_g[x['adGroup']['id']] = x['adGroup'].get('name')
    names_c[x['campaign']['id']] = x['campaign'].get('name')


def add_suffix(url, suffix):
    if not suffix or url is None:
        return url
    base, hash_, frag = url.partition('#')
    sep = '&' if '?' in base else '?'
    return base + sep + suffix.lstrip('?&') + hash_ + frag


def eff_status(c_st, ag_st, own_st):
    """Same convention as the 11-Oct pull / sibling re-reads: first non-ENABLED level wins."""
    if c_st and c_st != 'ENABLED':
        return 'CAMPAIGN_' + c_st
    if ag_st and ag_st != 'ENABLED':
        return 'AD_GROUP_' + ag_st
    if own_st and own_st != 'ENABLED':
        return own_st
    return 'ENABLED'


def cmp_note(url, r):
    return 'unchanged vs 11-Oct' if url == r['url_11oct'] else 'CHANGED vs 11-Oct'


out, stats = [], collections.Counter()
for r, l in zip(inp, live):
    rec = {"platform": "google", "account_id": ACC, "ad_id": r['ad_id'], "slot": r['slot']}
    if r['slot'] == 'ad.final_urls[0]':
        a = ads.get(r['ad_id'])
        if a is None:
            g = gone.get(r['ad_id'])
            if g is None:
                raise SystemExit(f"ad {r['ad_id']} neither in the != REMOVED read nor in the by-id read")
            st = g['status']
            if st != 'REMOVED':
                raise SystemExit(f"ad {r['ad_id']} status {st} but missing from the != REMOVED read - paging gap?")
            rec.update(url=None, status_now='REMOVED', creative_id_now=None, found=False,
                       note=f"ad_group_ad status REMOVED (ad deleted since the 11-Oct pull); 11-Oct url was {r['url_11oct']}")
            stats['ad_removed'] += 1
            out.append(rec)
            continue
        c, g = camps[a['cid']], adgroups[a['ag']]
        if a['suffix']:
            sfx, src = a['suffix'], 'ad.final_url_suffix'
        elif g['suffix']:
            sfx, src = g['suffix'], 'ad_group.final_url_suffix'
        elif c['suffix']:
            sfx, src = c['suffix'], 'campaign.final_url_suffix'
        elif CUSTOMER_SUFFIX:
            sfx, src = CUSTOMER_SUFFIX, 'customer.final_url_suffix'
        else:
            sfx, src = '', 'none set at ad/ad group/campaign/customer'
        url0 = a['urls'][0] if a['urls'] else None
        url = add_suffix(url0, sfx)
        status_now = eff_status(c['status'], g['status'], a['status'])
        notes = [cmp_note(url, r), f"final_urls[0] + effective final_url_suffix ({src})",
                 f"campaign {a['cid']} (11-Oct name '{l['campaign_name']}') now status/serving_status {c['status']}/{c['serving']}",
                 f"ad_group {a['ag']} (11-Oct name '{l['adset_name']}') now status {g['status']}",
                 f"ad_status={a['status']}; primary_status={a['primary']}; type={a['type']}",
                 "Google has no separate creative id (11-Oct creative_id null)"]
        if a['ag'] != l['adset_id']:
            notes.append(f"AD GROUP CHANGED: now {a['ag']} (11-Oct {l['adset_id']})")
        if a['cid'] != l['campaign_id']:
            notes.append(f"CAMPAIGN CHANGED: now {a['cid']} (11-Oct {l['campaign_id']})")
        if len(a['urls']) > 1:
            notes.append(f"ad now has {len(a['urls'])} final_urls: {a['urls'][1:]}")
        if url0 is None:
            notes.append('ad has no final_urls now')
        if status_now != r['status_11oct']:
            notes.append(f"status changed since 11-Oct (was {r['status_11oct']})")
        rec.update(url=url, status_now=status_now, creative_id_now=None, found=True, note='; '.join(notes))
        stats['ad_found'] += 1
        stats['ad_url_changed' if url != r['url_11oct'] else 'ad_url_same'] += 1
        out.append(rec)
        continue

    m = re.fullmatch(r'sitelink asset (\d+) final_urls\[(\d+)\] \((campaign_asset|ad_group_asset)\)', r['slot'])
    assert m and m.group(1) == r['ad_id'], r['slot']
    aid, idx, kind = m.group(1), int(m.group(2)), m.group(3)
    pm = re.search(r'customers/%s/(campaignAssets|adGroupAssets)/(\d+)~(\d+)~SITELINK' % ACC, r['notes_11oct'])
    assert pm and pm.group(3) == aid and (pm.group(1) == 'campaignAssets') == (kind == 'campaign_asset'), r
    parent = pm.group(2)
    a = assets.get(aid)
    if a is None:
        rec.update(url=None, status_now='REMOVED', creative_id_now=None, found=False,
                   note=f"sitelink asset {aid} not returned by GAQL FROM asset (asset no longer exists); 11-Oct url was {r['url_11oct']}")
        stats['asset_gone'] += 1
        out.append(rec)
        continue
    if kind == 'campaign_asset':
        assert parent == l['campaign_id']
        cid, ag, lst = parent, None, ca_links.get((parent, aid))
    else:
        assert parent == l['adset_id']
        ag = adgroups.get(parent)
        cid = (ag or {}).get('cid') or l['campaign_id']   # ad groups with no non-removed ad: campaign from the 11-Oct pull
        if ag and ag.get('cid'):
            assert ag['cid'] == l['campaign_id'], (parent, ag['cid'], l['campaign_id'])
        lst = aga_links.get((parent, aid))
    c = camps.get(cid)
    # effective suffix for a sitelink: asset > ad group (ad-group-level link) > campaign > customer
    if a['suffix']:
        sfx, src = a['suffix'], 'asset.final_url_suffix'
    elif ag and ag['suffix']:
        sfx, src = ag['suffix'], 'ad_group.final_url_suffix'
    elif c and c['suffix']:
        sfx, src = c['suffix'], 'campaign.final_url_suffix'
    elif CUSTOMER_SUFFIX:
        sfx, src = CUSTOMER_SUFFIX, 'customer.final_url_suffix'
    else:
        sfx, src = '', 'none set at asset/ad group/campaign/customer'
    base = a['urls'][idx] if idx < len(a['urls']) else None
    url = add_suffix(base, sfx)
    link_id = f"{parent}~{aid}~SITELINK"
    if lst is None:
        link_note = f"{kind} link {link_id} not among the non-removed SITELINK {kind} links (removed / unlinked since 11-Oct)"
        status_now = 'REMOVED'
        stats['link_missing'] += 1
    elif lst == 'REMOVED':
        link_note = f"{kind} link {link_id} status REMOVED (unlinked since 11-Oct; asset itself still exists)"
        status_now = 'REMOVED'
        stats['link_removed'] += 1
    else:
        link_note = f"{kind} link {link_id} status {lst}"
        status_now = eff_status(c['status'] if c else None, ag['status'] if ag else None, lst)
    n_links = sum(1 for k, v in ca_links.items() if k[1] == aid and v != 'REMOVED') + \
        sum(1 for k, v in aga_links.items() if k[1] == aid and v != 'REMOVED')
    notes = [cmp_note(url, r), f"SITELINK asset (not an ad): asset.final_urls[{idx}] + effective suffix ({src})", link_note,
             f"campaign {cid} (11-Oct name '{l['campaign_name']}') now status/serving_status {c['status']}/{c['serving']}" if c else f"campaign {cid} not read"]
    if kind == 'ad_group_asset':
        notes.append(f"ad_group {parent} (11-Oct name '{l['adset_name']}') now status {ag['status'] if ag else 'not read'}")
    notes.append(f"asset now has {n_links} non-removed SITELINK link(s) in this account (one asset URL serves all of them)")
    if a['text'] is not None and r['ad_name'] is not None and a['text'] != r['ad_name']:
        notes.append(f"link text now '{a['text']}' (11-Oct '{r['ad_name']}')")
    if len(a['urls']) > 1:
        notes.append(f"asset now has {len(a['urls'])} final_urls")
    if base is None:
        notes.append(f'asset has no final_urls[{idx}] now')
    if status_now != r['status_11oct']:
        notes.append(f"status changed since 11-Oct (was {r['status_11oct']})")
    rec.update(url=url, status_now=status_now, creative_id_now=aid, found=True, note='; '.join(notes))
    stats['sitelink_found'] += 1
    stats['sitelink_url_changed' if url != r['url_11oct'] else 'sitelink_url_same'] += 1
    out.append(rec)

assert len(out) == len(inp)
for o, r in zip(out, inp):
    assert o['ad_id'] == r['ad_id'] and o['slot'] == r['slot']
print('rows', len(out), dict(stats))

# ---------------- TASK 2: ads not in the input (non-removed) ----------------
in_ads = set(r['ad_id'] for r in inp if r['slot'] == 'ad.final_urls[0]')
new_lines = []
for ad_id in sorted(ads, key=int):
    if ad_id in in_ads:
        continue
    a = ads[ad_id]
    c, g = camps[a['cid']], adgroups[a['ag']]
    st = eff_status(c['status'], g['status'], a['status'])
    sfx = a['suffix'] or g['suffix'] or c['suffix'] or CUSTOMER_SUFFIX
    base = {"platform": "google", "account_id": ACC, "account_name": ACC_NAME,
            "campaign_name": names_c.get(a['cid']), "adset_name": names_g.get(a['ag']),
            "ad_id": ad_id, "ad_name": names_ad.get(ad_id), "effective_status": st}
    if not a['urls']:
        new_lines.append(dict(base, slot='ad.final_urls[0]', url=None))
    for i, u in enumerate(a['urls']):
        new_lines.append(dict(base, slot=f"ad.final_urls[{i}]", url=add_suffix(u, sfx)))
missing_names = [x['ad_id'] for x in new_lines if x['campaign_name'] is None or x['adset_name'] is None]
print('new ads', len(set(x['ad_id'] for x in new_lines)), 'new lines', len(new_lines), 'missing names for', missing_names)

if DRY:
    print('dry run: nothing written')
    sys.exit(0)
with open(OUT, 'w', encoding='utf-8') as f:
    for rec in out:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')
with open(NEW, 'w', encoding='utf-8') as f:
    for rec in new_lines:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')
print('wrote', OUT, 'and', NEW)
