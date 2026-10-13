"""Build reread3/out/google_8324286739.jsonl (one line per input row, same order, ad_id + slot copied from the input)
and reread3/out/new_google_8324286739.jsonl (non-removed ads not in the input) from the GAQL results saved in ../raw/
(validated by grab.py from persisted MCP tool-result files, or copied byte for byte from this agent's transcript by
from_transcript.py for results shown inline; nothing transcribed by hand).
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
PREV = f'{ROOT}/reread2/out/google_{ACC}.jsonl'   # 12-Oct re-read, same row order (comparison only)
OUT = f'{ROOT}/reread3/out/google_{ACC}.jsonl'
NEW = f'{ROOT}/reread3/out/new_google_{ACC}.jsonl'

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

# customer-level suffix: GAQL FROM customer returned no finalUrlSuffix (and no tracking template)
cust = json.loads(json.load(open(os.path.join(W, 'inline', 'customer.json')))[0]['text'])['data']['data']['data']['results']
assert len(cust) == 1 and cust[0]['customer']['id'] == ACC
CUSTOMER_SUFFIX = cust[0]['customer'].get('finalUrlSuffix') or ''


def load(prefix):
    out = []
    for f in sorted(glob.glob(os.path.join(RAW, prefix + '*.json'))):
        out.extend(json.load(open(f))['results'])
    return out


def merge(store, key, rec, what):
    if key in store and store[key] != rec:
        raise SystemExit(f'{what} {key} differs between reads:\n{store[key]}\n{rec}')
    store[key] = rec


# ---------------- campaigns (all statuses) ----------------
camps = {}
for x in load('camps_p'):
    c = x['campaign']
    merge(camps, c['id'], dict(name=c.get('name'), status=c.get('status'), serving=c.get('servingStatus'),
                               primary=c.get('primaryStatus'), channel=c.get('advertisingChannelType'),
                               suffix=c.get('finalUrlSuffix') or ''), 'campaign')

# ---------------- ads (ad_group_ad, status != REMOVED, keyset pages with one-row overlap) ----------------
ads, adgroups = {}, {}
for x in load('ads_p'):
    c, g, aga = x['campaign'], x['adGroup'], x['adGroupAd']
    ad = aga['ad']
    assert c['id'] in camps, c
    assert (camps[c['id']]['status'], camps[c['id']]['suffix']) == (c.get('status'), c.get('finalUrlSuffix') or ''), (c, camps[c['id']])
    merge(adgroups, g['id'], dict(status=g.get('status'), suffix=g.get('finalUrlSuffix') or '', cid=c['id']), 'ad group')
    assert aga['resourceName'] == f"customers/{ACC}/adGroupAds/{g['id']}~{ad['id']}", aga['resourceName']
    merge(ads, ad['id'], dict(ag=g['id'], cid=c['id'], status=aga.get('status'), primary=aga.get('primaryStatus'),
                              type=ad.get('type'), urls=ad.get('finalUrls') or [], suffix=ad.get('finalUrlSuffix') or ''), 'ad')

# ---------------- sitelink assets (asset.type = SITELINK, every asset) ----------------
assets = {}
for x in load('assets_p'):
    a = x['asset']
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
    assert m and m.group(1) == g['id'], x
    cm = re.fullmatch(r'customers/%s/campaigns/(\d+)' % ACC, g['campaign'])
    rec = dict(status=g.get('status'), suffix=g.get('finalUrlSuffix') or '', cid=cm.group(1))
    merge(adgroups, g['id'], rec, 'ad group')
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


def cmp_notes(url, i):
    r = inp[i]
    n = ['unchanged vs 11-Oct' if url == r['url_11oct'] else 'CHANGED vs 11-Oct']
    if prev is not None:
        n.append('same as 12-Oct re-read' if url == prev[i].get('url') else f"differs from 12-Oct re-read ({prev[i].get('url')})")
    return n


out, stats = [], collections.Counter()
for i, (r, l) in enumerate(zip(inp, live)):
    rec = {"platform": "google", "account_id": ACC, "ad_id": r['ad_id'], "slot": r['slot']}
    if r['slot'] == 'ad.final_urls[0]':
        a = ads.get(r['ad_id'])
        if a is None:
            raise SystemExit(f"ad {r['ad_id']} not in the != REMOVED read: read it by id (any status) before building")
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
            f"ad_group {a['ag']} (11-Oct name '{l['adset_name']}') status {g['status']}",
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
        assert ag is not None, parent
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
        link_note = f"{kind} link {link_rn} status REMOVED (unlinked since 11-Oct; the asset itself still exists)"
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
        notes.append(f"ad_group {parent} (11-Oct name '{l['adset_name']}') status {ag['status']}")
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
    rec.update(url=url, status_now=status_now, creative_id_now=aid, found=True, note='; '.join(notes))
    stats['sitelink_found'] += 1
    stats['sitelink_url_changed' if url != r['url_11oct'] else 'sitelink_url_same'] += 1
    out.append(rec)

assert len(out) == len(inp)
for o, r in zip(out, inp):
    assert o['ad_id'] == r['ad_id'] and o['slot'] == r['slot']
print('rows', len(out), dict(stats))
print('status_now', dict(collections.Counter(o['status_now'] for o in out)))
if prev is not None:
    print('url differs from 12-Oct re-read:', sum(1 for o, p in zip(out, prev) if o['url'] != p.get('url')))

# ---------------- TASK 2: non-removed ads not in the input ----------------
in_ads = set(r['ad_id'] for r in inp if r['slot'] == 'ad.final_urls[0]')
new_ids = sorted((x for x in ads if x not in in_ads), key=int)
print('non-removed ads read', len(ads), '| input ads', len(in_ads), '| input ads not read', len(in_ads - set(ads)),
      '| new ads', len(new_ids))
new_lines = []
for ad_id in new_ids:
    raise SystemExit(f'new ad {ad_id}: read its campaign / ad group / ad names before building the new-ads file')

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
