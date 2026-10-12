"""Build reread2/out/google_9282725829.jsonl (one line per input row) and new_google_9282725829.jsonl
from the GAQL reads transcribed into this work dir.
Usage: python3 -I build_out.py <root diriyah_utm dir>"""
import json, sys, glob, os, re, collections

ROOT = sys.argv[1]
W = os.path.dirname(os.path.abspath(__file__))
ACC = '9282725829'
ACC_NAME = 'H&S - DGCL - Diriyah Gate'
ODIR = sys.argv[2] if len(sys.argv) > 2 else f'{ROOT}/reread2/out'
OUT = f'{ODIR}/google_{ACC}.jsonl'
NEW = f'{ODIR}/new_google_{ACC}.jsonl'

inp = json.load(open(f'{ROOT}/reread/in/google_{ACC}.json'))
live = [json.loads(l) for l in open(f'{ROOT}/live/google_{ACC}.jsonl')]
assert len(inp) == len(live)
for a, b in zip(inp, live):
    assert a['ad_id'] == b['ad_id'] and a['slot'] == b['slot']
interim = json.load(open(f'{ROOT}/work/live_interim.json'))


def rows(pattern):
    for f in sorted(glob.glob(os.path.join(W, pattern))):
        for line in open(f):
            line = line.rstrip('\n')
            if line.strip():
                yield line


# ---- transcribed reads ----
ads = {}          # ad_id -> dict
for line in rows('ads_p*.txt'):
    ad, ag, st, ps, suf, url = line.split('|', 5)
    assert ad not in ads, ad
    ads[ad] = dict(ag=ag, status=st, primary=ps, suffix=suf, url=url)
camps = {}
for line in rows('campaigns.txt'):
    c, s, ss = line.split('|')
    camps[c] = dict(status=s, serving=ss)
adgroups = {}
for line in rows('adgroups_p*.txt'):
    ag, st, suf, cid = line.split('|')
    adgroups[ag] = dict(status=st, suffix=suf, campaign=cid)
assets = {}
for line in rows('assets_p*.txt'):
    aid, suf, n, url = line.split('|', 3)
    assets[aid] = dict(suffix=suf, n=int(n), url=url)
ca_links = {}     # (campaign_id, asset_id) -> status
for line in rows('links_ca_p*.txt'):
    cid, aid, st = line.split('|')
    ca_links[(cid, aid)] = st
aga_links = {}    # (ad_group_id, asset_id) -> status
for line in rows('links_aga_p*.txt'):
    ag, aid, st = line.split('|')
    aga_links[(ag, aid)] = st
CUSTOMER_SUFFIX = ''   # customer.final_url_suffix is empty (read 12-Oct)
removed_ads = {}
if os.path.exists(os.path.join(W, 'removed_ads.txt')):
    for line in rows('removed_ads.txt'):
        ad, st = line.split('|')[:2]
        removed_ads[ad] = st


def add_suffix(url, suffix):
    if not suffix:
        return url
    base, hash_, frag = url.partition('#')
    sep = '&' if '?' in base else '?'
    return base + sep + suffix.lstrip('?&') + (hash_ + frag)


def eff_status(c_st, ag_st, own_st):
    if c_st and c_st != 'ENABLED':
        return 'CAMPAIGN_' + c_st
    if ag_st and ag_st != 'ENABLED':
        return 'AD_GROUP_' + ag_st
    if own_st and own_st != 'ENABLED':
        return own_st
    return 'ENABLED'


def cmp_note(url, r):
    k = f"google|{r['ad_id']}|{r['slot']}"
    li = (interim.get(k) or {}).get('url')
    if url == r['url_11oct']:
        s = 'unchanged vs 11-Oct'
    else:
        s = 'CHANGED vs 11-Oct'
    if li is not None:
        s += '; same as 12-Oct read-back (live_interim)' if url == li else '; DIFFERS from 12-Oct read-back (live_interim)'
    return s


out = []
stats = collections.Counter()
for r, l in zip(inp, live):
    rec = {"platform": "google", "account_id": ACC, "ad_id": r['ad_id'], "slot": r['slot']}
    cid = l['campaign_id']
    c = camps.get(cid)
    if r['slot'] == 'ad.final_urls[0]':
        ad = ads.get(r['ad_id'])
        if ad is None:
            st = removed_ads.get(r['ad_id'])
            rec.update(url=None, status_now='REMOVED' if st == 'REMOVED' else None, creative_id_now=None, found=False,
                       note=('ad_group_ad status REMOVED (deleted since 11-Oct)' if st == 'REMOVED'
                             else 'ad not returned by GAQL ad_group_ad (deleted since 11-Oct)'))
            stats['ad_gone'] += 1
            out.append(rec); continue
        ag = adgroups.get(ad['ag'])
        cid_now = ag['campaign'] if ag else cid
        c = camps.get(cid_now)
        sfx, src = '', 'none set at ad/ad group/campaign/customer'
        if ad['suffix']:
            sfx, src = ad['suffix'], 'ad.final_url_suffix'
        elif ag and ag['suffix']:
            sfx, src = ag['suffix'], 'ad_group.final_url_suffix'
        elif c and c.get('suffix'):
            sfx, src = c['suffix'], 'campaign.final_url_suffix'
        elif CUSTOMER_SUFFIX:
            sfx, src = CUSTOMER_SUFFIX, 'customer.final_url_suffix'
        url = add_suffix(ad['url'], sfx)
        status_now = eff_status(c['status'] if c else None, ag['status'] if ag else None, ad['status'])
        notes = [cmp_note(url, r), f"final_urls[0] + effective final_url_suffix ({src})",
                 f"campaign={l['campaign_name']} [{c['status']}/{c['serving']}]" if c else f"campaign {cid_now} status not read",
                 f"ad_group={l['adset_name']} [{ag['status'] if ag else '?'}]",
                 f"ad_status={ad['status']}; primary_status={ad['primary']}",
                 "Google has no separate creative id (11-Oct creative_id null)"]
        if ad['ag'] != l['adset_id']:
            notes.append(f"AD GROUP CHANGED: now {ad['ag']} (11-Oct {l['adset_id']})")
        if status_now != r['status_11oct']:
            notes.append(f"status changed since 11-Oct (was {r['status_11oct']})")
        rec.update(url=url, status_now=status_now, creative_id_now=None, found=True, note='; '.join(notes))
        stats['ad_ok'] += 1
    else:
        m = re.match(r'sitelink asset (\d+) final_urls\[(\d+)\] \((campaign_asset|ad_group_asset)\)$', r['slot'])
        assert m and m.group(1) == r['ad_id'], r['slot']
        idx, kind = int(m.group(2)), m.group(3)
        a = assets.get(r['ad_id'])
        if a is None:
            rec.update(url=None, status_now=None, creative_id_now=None, found=False,
                       note='sitelink asset not returned by GAQL asset query (deleted)')
            stats['asset_gone'] += 1
            out.append(rec); continue
        assert idx == 0 or idx < a['n']
        url = add_suffix(a['url'], a['suffix'])
        sfx_src = 'asset.final_url_suffix' if a['suffix'] else 'none'
        if kind == 'campaign_asset':
            key = (cid, r['ad_id'])
            lst = ca_links.get(key)
            ag = None
            link_id = f"{cid}~{r['ad_id']}~SITELINK"
        else:
            key = (l['adset_id'], r['ad_id'])
            lst = aga_links.get(key)
            ag = adgroups.get(l['adset_id'])
            link_id = f"{l['adset_id']}~{r['ad_id']}~SITELINK"
        if lst is None:
            lst = 'REMOVED'
            link_note = f"{kind} link {link_id} not among non-removed SITELINK links now (link removed since 11-Oct)"
            stats['link_gone'] += 1
        else:
            link_note = f"row mapped to {kind} link {link_id} (link status {lst})"
        if lst == 'REMOVED':
            status_now = 'REMOVED'
        else:
            status_now = eff_status(c['status'] if c else None, ag['status'] if ag else None, lst)
        n_links = sum(1 for k in ca_links if k[1] == r['ad_id']) + sum(1 for k in aga_links if k[1] == r['ad_id'])
        notes = [cmp_note(url, r), f"asset.final_urls[{idx}] + asset.final_url_suffix ({sfx_src})", link_note,
                 f"campaign={l['campaign_name']} [{c['status']}/{c['serving']}]" if c else f"campaign {cid} status not read"]
        if kind == 'ad_group_asset':
            notes.append(f"ad_group={l['adset_name']} [{ag['status'] if ag else '?'}]")
        notes.append(f"asset has {n_links} non-removed SITELINK link(s) among the 11-Oct placements re-read (one asset URL serves all of them)")
        if a['n'] > 1:
            notes.append(f"asset now has {a['n']} final_urls")
        if status_now != r['status_11oct']:
            notes.append(f"status changed since 11-Oct (was {r['status_11oct']})")
        rec.update(url=url, status_now=status_now, creative_id_now=None, found=True, note='; '.join(notes))
        stats['sitelink_ok'] += 1
    out.append(rec)

with open(OUT, 'w') as f:
    for rec in out:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')
print('wrote', OUT, len(out), dict(stats))

# ---- TASK 2: ads not in the input ----
in_ads = set(r['ad_id'] for r in inp if r['slot'] == 'ad.final_urls[0]')
newinfo = {}
p = os.path.join(W, 'new_ads_info.json')
if os.path.exists(p):
    newinfo = json.load(open(p))
new_lines = []
for ad_id, ad in sorted(ads.items()):
    if ad_id in in_ads:
        continue
    info = newinfo.get(ad_id, {})
    ag = adgroups.get(ad['ag'])
    c = camps.get(info.get('campaign_id') or (ag or {}).get('campaign'))
    st = eff_status(c['status'] if c else None, (ag or {}).get('status') or info.get('ad_group_status'), ad['status'])
    urls = info.get('final_urls') or [ad['url']]
    sfx = ad['suffix'] or (ag or {}).get('suffix') or ''
    for i, u in enumerate(urls):
        new_lines.append({"platform": "google", "account_id": ACC, "account_name": ACC_NAME,
                          "campaign_name": info.get('campaign_name'), "adset_name": info.get('ad_group_name'),
                          "ad_id": ad_id, "ad_name": info.get('ad_name'), "effective_status": st,
                          "slot": f"ad.final_urls[{i}]", "url": add_suffix(u, sfx)})
with open(NEW, 'w') as f:
    for rec in new_lines:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')
print('wrote', NEW, len(new_lines), 'lines for', len(set(x['ad_id'] for x in new_lines)), 'new ads')
