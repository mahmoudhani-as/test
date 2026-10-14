"""Build reread7/out/google_8324286739.jsonl (one line per input row, same order, ad_id + slot copied from the input)
and reread7/out/new_google_8324286739.jsonl (non-removed ads not in the input) from the GAQL results saved in ../raw/
(validated by grab.py / grab2.py from persisted MCP tool-result files, or copied byte for byte from this agent's
transcript by from_transcript.py for results shown inline; nothing transcribed by hand).
READ-ONLY: only GoogleAdsService.Search (GAQL) calls were made.
Usage: python3 -I build_out.py <diriyah_utm root dir> [--dry]"""
import json, sys, glob, os, re, collections

ROOT = sys.argv[1]
DRY = '--dry' in sys.argv
W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(W, 'raw')
ACC = '8324286739'
ACC_NAME = 'H&S - DGCL - Visit Diriyah'
INP = f'{ROOT}/reread/in/google_{ACC}.json'
LIVE = f'{ROOT}/live/google_{ACC}.jsonl'          # 11-Oct inventory, same row order: parent ids / names
PREV = f'{ROOT}/reread5/out/google_{ACC}.jsonl'   # latest earlier re-read (13-Oct ~12:05-12:34 UTC, = reread4/out)
OUT = f'{ROOT}/reread7/out/google_{ACC}.jsonl'
NEW = f'{ROOT}/reread7/out/new_google_{ACC}.jsonl'

inp = json.load(open(INP))
live = [json.loads(l) for l in open(LIVE)]
prev = [json.loads(l) for l in open(PREV)] if os.path.exists(PREV) else None
assert len(inp) == len(live) == 1556
for a, b in zip(inp, live):
    assert a['ad_id'] == b['ad_id'] and a['slot'] == b['slot']
if prev is not None:
    assert len(prev) == len(inp)
    for a, b in zip(inp, prev):
        assert a['ad_id'] == b['ad_id'] and a['slot'] == b['slot']


def load(prefix):
    out = []
    for f in sorted(glob.glob(os.path.join(RAW, prefix + '*.json'))):
        out.extend(json.load(open(f))['results'])
    return out


def merge(store, key, rec, what):
    if key in store and store[key] != rec:
        raise SystemExit(f'{what} {key} differs between reads:\n{store[key]}\n{rec}')
    store[key] = rec


# customer-level suffix
cust = load('customer')
assert len(cust) == 1 and cust[0]['customer']['id'] == ACC
CUSTOMER_SUFFIX = cust[0]['customer'].get('finalUrlSuffix') or ''

# ---------------- campaigns (all statuses) ----------------
camps = {}
for x in load('camps_p'):
    c = x['campaign']
    merge(camps, c['id'], dict(name=c.get('name'), status=c.get('status'), serving=c.get('servingStatus'),
                               primary=c.get('primaryStatus'), channel=c.get('advertisingChannelType'),
                               suffix=c.get('finalUrlSuffix') or ''), 'campaign')

# ---------------- ads (ad_group_ad, status != REMOVED, keyset pages with one-row overlap) ----------------
ads, adgroups, agnames = {}, {}, {}
for x in load('ads_'):
    c, g, aga = x['campaign'], x['adGroup'], x['adGroupAd']
    ad = aga['ad']
    assert c['id'] in camps, c
    assert (camps[c['id']]['status'], camps[c['id']]['suffix']) == (c.get('status'), c.get('finalUrlSuffix') or ''), (c, camps[c['id']])
    merge(adgroups, g['id'], dict(status=g.get('status'), suffix=g.get('finalUrlSuffix') or '', cid=c['id']), 'ad group')
    merge(agnames, g['id'], g.get('name'), 'ad group name')
    assert aga['resourceName'] == f"customers/{ACC}/adGroupAds/{g['id']}~{ad['id']}", aga['resourceName']
    assert aga.get('status') != 'REMOVED', aga
    merge(ads, ad['id'], dict(ag=g['id'], cid=c['id'], status=aga.get('status'), primary=aga.get('primaryStatus'),
                              type=ad.get('type'), name=ad.get('name'), urls=ad.get('finalUrls') or [],
                              suffix=ad.get('finalUrlSuffix') or ''), 'ad')
# ads read by id with ANY status (input ads missing from the != REMOVED read), if that read was made
ads_any = {}
for x in load('adsany_'):
    c, g, aga = x['campaign'], x['adGroup'], x['adGroupAd']
    ad = aga['ad']
    merge(ads_any, ad['id'], dict(ag=g['id'], cid=c['id'], status=aga.get('status'), primary=aga.get('primaryStatus'),
                                  type=ad.get('type'), name=ad.get('name'), urls=ad.get('finalUrls') or [],
                                  suffix=ad.get('finalUrlSuffix') or ''), 'ad (any status)')
    merge(agnames, g['id'], g.get('name'), 'ad group name')
    if g['id'] not in adgroups:
        merge(adgroups, g['id'], dict(status=g.get('status'), suffix=g.get('finalUrlSuffix') or '', cid=c['id']), 'ad group')

# ---------------- extra ad groups (ad-group-level sitelink parents with no non-removed ad), if read ----------------
for x in load('adgroups_'):
    c, g = x['campaign'], x['adGroup']
    merge(adgroups, g['id'], dict(status=g.get('status'), suffix=g.get('finalUrlSuffix') or '', cid=c['id']), 'ad group')
    merge(agnames, g['id'], g.get('name'), 'ad group name')

# ---------------- sitelink assets (asset.type = SITELINK, every asset) ----------------
assets = {}
for x in load('assets_p'):
    a = x['asset']
    assert a.get('type') == 'SITELINK', a
    merge(assets, a['id'], dict(urls=a.get('finalUrls') or [], suffix=a.get('finalUrlSuffix') or '',
                                text=(a.get('sitelinkAsset') or {}).get('linkText'),
                                approval=(a.get('policySummary') or {}).get('approvalStatus')), 'asset')

# ---------------- sitelink links (every status) ----------------
ca_links, aga_links = {}, {}
for x in load('calinks_p'):
    ca = x['campaignAsset']
    m = re.fullmatch(r'customers/%s/campaignAssets/(\d+)~(\d+)~SITELINK' % ACC, ca['resourceName'])
    assert m and m.group(1) == x['campaign']['id'] and m.group(2) == x['asset']['id'], x
    merge(ca_links, ca['resourceName'], ca.get('status'), 'campaign_asset')
for x in load('agalinks_p'):
    ga, g = x['adGroupAsset'], x['adGroup']
    m = re.fullmatch(r'customers/%s/adGroupAssets/(\d+)~(\d+)~SITELINK' % ACC, ga['resourceName'])
    assert m and m.group(1) == g['id'] and m.group(2) == x['asset']['id'], x
    merge(aga_links, ga['resourceName'], ga.get('status'), 'ad_group_asset')


def add_suffix(url, suffix):
    """Same composition as the 11-Oct pull: base (before #) + ('&' if '?' in base else '?') + suffix (verbatim) + #fragment."""
    if not suffix or url is None:
        return url
    base, hash_, frag = url.partition('#')
    return base + ('&' if '?' in base else '?') + suffix + hash_ + frag


def eff_status(c_st, ag_st, own_st):
    """Same convention as the 11-Oct pull / earlier re-reads: the first non-ENABLED level wins."""
    if c_st and c_st != 'ENABLED':
        return 'CAMPAIGN_' + c_st
    if ag_st and ag_st != 'ENABLED':
        return 'AD_GROUP_' + ag_st
    if own_st and own_st != 'ENABLED':
        return own_st
    return 'ENABLED'


def dup_utm_note(url):
    """Flag a URL whose query string carries the same utm_* key more than once (e.g. final URL with its own UTMs + a suffix)."""
    if not url or '?' not in url:
        return None
    q = url.split('#', 1)[0].split('?', 1)[1]
    keys = [kv.split('=', 1)[0] for kv in q.split('&') if kv]
    d = sorted({k for k in keys if k.lower().startswith('utm_') and keys.count(k) > 1})
    return f"DUPLICATE utm keys in the effective URL ({', '.join(d)}): the final URL carries its own UTMs and the suffix appends a second set" if d else None


def prev_link_status(i):
    if prev is None:
        return None
    m = re.search(r'link customers/\d+/(?:campaignAssets|adGroupAssets)/\S+~SITELINK (?:status (\w+)|not returned)', prev[i].get('note') or '')
    if not m:
        return None
    return m.group(1) or 'MISSING'


def cmp_notes(url, i):
    r = inp[i]
    n = ['unchanged vs 11-Oct' if url == r['url_11oct'] else 'CHANGED vs 11-Oct']
    if prev is not None:
        n.append('same as 13-Oct re-read' if url == prev[i].get('url')
                 else f"CHANGED SINCE 13-Oct re-read (was {prev[i].get('url')})")
    return n


missing_ads = []
out, stats = [], collections.Counter()
for i, (r, l) in enumerate(zip(inp, live)):
    rec = {"platform": "google", "account_id": ACC, "ad_id": r['ad_id'], "slot": r['slot']}
    if r['slot'] == 'ad.final_urls[0]':
        a = ads.get(r['ad_id'])
        if a is None:
            b = ads_any.get(r['ad_id'])
            if b is None:
                missing_ads.append(r['ad_id'])
                rec.update(url=None, status_now='NOT_FOUND', creative_id_now=None, found=False,
                           note=f"ad {r['ad_id']} not returned by GAQL ad_group_ad reads (status != REMOVED, nor by id with any status): ad no longer exists; 11-Oct url was {r['url_11oct']}")
                stats['ad_gone'] += 1
                out.append(rec)
                continue
            assert b['status'] == 'REMOVED', b
            rec.update(url=None, status_now='REMOVED', creative_id_now=None, found=False,
                       note=f"ad_group_ad status REMOVED (ad deleted since 11-Oct; read by id with any status); its last final_urls[0] was {b['urls'][0] if b['urls'] else None}; 11-Oct url was {r['url_11oct']}")
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
        notes = cmp_notes(url, i) + [
            f"final_urls[0] + effective final_url_suffix ({src})" + (f": {sfx}" if sfx else ''),
            f"campaign {a['cid']} '{c['name']}' status/serving_status {c['status']}/{c['serving']}",
            f"ad_group {a['ag']} '{agnames.get(a['ag'])}' status {g['status']}",
            f"ad_status={a['status']}; primary_status={a['primary']}; type={a['type']}",
            "Google has no separate creative id (11-Oct creative_id null)"]
        if a['ag'] != l['adset_id']:
            notes.append(f"AD GROUP CHANGED: now {a['ag']} (11-Oct {l['adset_id']})")
        if a['cid'] != l['campaign_id']:
            notes.append(f"CAMPAIGN CHANGED: now {a['cid']} (11-Oct {l['campaign_id']})")
        if (sfx or None) != (r['url_tags_11oct'] or None):
            notes.append(f"suffix changed since 11-Oct (was {r['url_tags_11oct'] or 'none'})")
        if len(a['urls']) > 1:
            notes.append(f"ad now has {len(a['urls'])} final_urls: {a['urls'][1:]}")
        if url0 is None:
            notes.append('ad has no final_urls now')
        if status_now != r['status_11oct']:
            notes.append(f"status changed since 11-Oct (was {r['status_11oct']})")
        if prev is not None and status_now != prev[i].get('status_now'):
            notes.append(f"status changed since 13-Oct re-read (was {prev[i].get('status_now')})")
        dn = dup_utm_note(url)
        if dn:
            notes.append(dn)
            stats['dup_utm_keys'] += 1
        rec.update(url=url, status_now=status_now, creative_id_now=None, found=True, note='; '.join(notes))
        stats['ad_found'] += 1
        stats['ad_url_changed_vs_11oct' if url != r['url_11oct'] else 'ad_url_same_as_11oct'] += 1
        out.append(rec)
        continue

    m = re.fullmatch(r'sitelink asset (\d+) final_urls\[(\d+)\] \((campaign_asset|ad_group_asset)\)', r['slot'])
    assert m and m.group(1) == r['ad_id'], r['slot']
    aid, idx, kind = m.group(1), int(m.group(2)), m.group(3)
    pm = re.search(r'customers/%s/(campaignAssets|adGroupAssets)/(\d+)~(\d+)~SITELINK' % ACC, r['notes_11oct'])
    assert pm and pm.group(3) == aid and (pm.group(1) == 'campaignAssets') == (kind == 'campaign_asset'), r
    link_rn, parent = pm.group(0), pm.group(2)
    a = assets.get(aid)
    if a is None:
        rec.update(url=None, status_now='REMOVED', creative_id_now=aid, found=False,
                   note=f"sitelink asset {aid} not returned by GAQL FROM asset WHERE asset.type = SITELINK (asset no longer exists); 11-Oct url was {r['url_11oct']}")
        stats['asset_gone'] += 1
        out.append(rec)
        continue
    if kind == 'campaign_asset':
        assert parent == l['campaign_id']
        cid, ag, lst = parent, None, ca_links.get(link_rn)
    else:
        assert parent == l['adset_id']
        ag = adgroups.get(parent)
        if ag is None:
            raise SystemExit(f'ad group {parent} (parent of {link_rn}) not read: read it (adgroups_*) before building')
        cid = ag['cid']
        assert cid == l['campaign_id'], (parent, cid, l['campaign_id'])
        lst = aga_links.get(link_rn)
    c = camps.get(cid)
    assert c is not None, cid
    # effective suffix for a sitelink: asset > ad group (ad-group-level link) > campaign > customer
    if a['suffix']:
        sfx, src = a['suffix'], 'asset.final_url_suffix'
    elif ag and ag['suffix']:
        sfx, src = ag['suffix'], 'ad_group.final_url_suffix'
    elif c['suffix']:
        sfx, src = c['suffix'], 'campaign.final_url_suffix'
    elif CUSTOMER_SUFFIX:
        sfx, src = CUSTOMER_SUFFIX, 'customer.final_url_suffix'
    else:
        sfx, src = '', 'none set at asset/ad group/campaign/customer'
    base = a['urls'][idx] if idx < len(a['urls']) else None
    url = add_suffix(base, sfx)
    if lst is None:
        link_note = f"{kind} link {link_rn} not returned by the SITELINK link read (link no longer exists)"
        status_now = 'REMOVED'
        stats['link_missing'] += 1
    elif lst == 'REMOVED':
        link_note = f"{kind} link {link_rn} status REMOVED (unlinked; the asset itself still exists)"
        status_now = 'REMOVED'
        stats['link_removed'] += 1
    else:
        link_note = f"{kind} link {link_rn} status {lst}"
        status_now = eff_status(c['status'], ag['status'] if ag else None, lst)
    n_links = sum(1 for k, v in ca_links.items() if k.split('~')[1] == aid and v != 'REMOVED') + \
        sum(1 for k, v in aga_links.items() if k.split('~')[1] == aid and v != 'REMOVED')
    notes = cmp_notes(url, i) + [
        f"SITELINK asset (not an ad): asset.final_urls[{idx}] + effective suffix ({src})" + (f": {sfx}" if sfx else ''),
        link_note,
        f"campaign {cid} '{c['name']}' status/serving_status {c['status']}/{c['serving']}"]
    if kind == 'ad_group_asset':
        notes.append(f"ad_group {parent} '{agnames.get(parent) or l['adset_name']}' status {ag['status']}")
    notes.append(f"asset approval_status={a['approval'] or 'not reported'}; link_text '{a['text']}'")
    notes.append(f"asset now has {n_links} non-removed SITELINK link(s) in this account (one asset URL serves all of them)")
    if a['text'] is not None and r['ad_name'] is not None and a['text'] != r['ad_name']:
        notes.append(f"link text changed since 11-Oct (was '{r['ad_name']}')")
    if len(a['urls']) > 1:
        notes.append(f"asset now has {len(a['urls'])} final_urls")
    if base is None:
        notes.append(f'asset has no final_urls[{idx}] now')
    if status_now != r['status_11oct']:
        notes.append(f"status changed since 11-Oct (was {r['status_11oct']})")
    if prev is not None and status_now != prev[i].get('status_now'):
        notes.append(f"status changed since 13-Oct re-read (was {prev[i].get('status_now')})")
    pls = prev_link_status(i)
    if pls is not None and pls != (lst or 'MISSING'):
        notes.append(f"link status changed since 13-Oct re-read (was {pls})")
        stats['link_status_changed_since_13oct'] += 1
    dn = dup_utm_note(url)
    if dn:
        notes.append(dn)
        stats['dup_utm_keys'] += 1
    stats['link_' + str(lst)] += 1
    rec.update(url=url, status_now=status_now, creative_id_now=aid, found=True, note='; '.join(notes))
    stats['sitelink_found'] += 1
    stats['sitelink_url_changed_vs_11oct' if url != r['url_11oct'] else 'sitelink_url_same_as_11oct'] += 1
    out.append(rec)

if missing_ads:
    print('INPUT ADS NOT IN THE != REMOVED READ (read them by id with any status -> raw/adsany_*.json):', missing_ads)
assert len(out) == len(inp)
for o, r in zip(out, inp):
    assert o['ad_id'] == r['ad_id'] and o['slot'] == r['slot']
print('rows', len(out), dict(stats))
print('status_now', dict(collections.Counter(o['status_now'] for o in out)))
print('found', dict(collections.Counter(o['found'] for o in out)))
if prev is not None:
    diffs = [(o, p) for o, p in zip(out, prev) if o['url'] != p.get('url') or o['status_now'] != p.get('status_now')]
    print('url or status differs from the 13-Oct re-read:', len(diffs))
    for o, p in diffs[:60]:
        print('  ', o['ad_id'], o['slot'], '|', p.get('status_now'), '->', o['status_now'], '|', p.get('url'), '->', o['url'])

# ---------------- TASK 2: non-removed ads not in the input ----------------
in_ads = set(r['ad_id'] for r in inp if r['slot'] == 'ad.final_urls[0]')
new_ids = sorted((x for x in ads if x not in in_ads), key=int)
print('non-removed ads read', len(ads), '| input ads', len(in_ads), '| input ads not in != REMOVED read', len(in_ads - set(ads)),
      '| new ads', len(new_ids))
new_lines = []
for ad_id in new_ids:
    a = ads[ad_id]
    c, g = camps[a['cid']], adgroups[a['ag']]
    if a['suffix']:
        sfx = a['suffix']
    elif g['suffix']:
        sfx = g['suffix']
    elif c['suffix']:
        sfx = c['suffix']
    else:
        sfx = CUSTOMER_SUFFIX
    urls = a['urls'] or [None]
    for k, u in enumerate(urls):
        new_lines.append({"platform": "google", "account_id": ACC, "account_name": ACC_NAME,
                          "campaign_name": c['name'], "adset_name": agnames.get(a['ag']),
                          "ad_id": ad_id, "ad_name": a['name'],
                          "effective_status": eff_status(c['status'], g['status'], a['status']),
                          "slot": f"ad.final_urls[{k}]", "url": add_suffix(u, sfx)})
print('new-ad lines', len(new_lines))
for x in new_lines:
    print('  NEW', json.dumps(x, ensure_ascii=False))

if DRY:
    print('dry run: nothing written')
    sys.exit(0)
for p in (OUT, NEW):
    if os.path.exists(p):
        raise SystemExit(f'{p} exists already: not overwritten')
with open(OUT, 'w', encoding='utf-8') as f:
    for rec in out:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')
with open(NEW, 'w', encoding='utf-8') as f:
    for rec in new_lines:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')
print('wrote', OUT, 'and', NEW)
