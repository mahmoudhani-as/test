"""Build reread2/out/google_8324286739.jsonl (one line per input row) and
new_google_8324286739.jsonl from the GAQL reads transcribed into this work dir.
Usage: python3 -I build_out.py <diriyah_utm root dir>"""
import json, sys, glob, os, collections

ROOT = sys.argv[1]
W = os.path.dirname(os.path.abspath(__file__))
ACC = '8324286739'
ACC_NAME = 'H&S - DGCL - Visit Diriyah'
INP = f'{ROOT}/reread/in/google_{ACC}.json'
OUT = f'{ROOT}/reread2/out/google_{ACC}.jsonl'
NEW = f'{ROOT}/reread2/out/new_google_{ACC}.jsonl'

inp = json.load(open(INP))


def rows(pattern):
    for f in sorted(glob.glob(os.path.join(W, pattern))):
        for line in open(f, encoding='utf-8'):
            line = line.rstrip('\n')
            if line.strip() and not line.startswith('#'):
                yield line


def join_suffix(base, suffix):
    if not suffix:
        return base
    if base is None:
        return None
    return base + ('&' if '?' in base else '?') + suffix


# ---------------- transcribed reads ----------------
camps = {}
for line in rows('campaigns.txt'):
    cid, st, serving, chan, suf = line.split('|')
    camps[cid] = dict(status=st, serving=serving, channel=chan, suffix=suf)

ads = {}
for line in rows('ads_r*.txt'):
    # ad_id|ad_group_id|campaign_id|ad_status|adgroup_status|approval|primary|ad_suffix|adgroup_suffix|url0|extra_urls
    p = line.split('|')
    assert len(p) == 11, (len(p), line)
    ad, ag, cid, st, agst, appr, prim, suf, agsuf, url, extra = p
    assert ad not in ads, ('dup ad', ad)
    ads[ad] = dict(ag=ag, cid=cid, status=st, ag_status=agst, approval=appr, primary=prim,
                   suffix=suf, ag_suffix=agsuf, url=url or None, extra=extra)

adgroups = {}
for line in rows('adgroups*.txt'):
    ag, cid, st, suf = line.split('|')
    adgroups[ag] = dict(cid=cid, status=st, suffix=suf)
# ad groups seen through the ad reads also count
for a in ads.values():
    adgroups.setdefault(a['ag'], dict(cid=a['cid'], status=a['ag_status'], suffix=a['ag_suffix']))

removed_ads = {}
for line in rows('removed_ads.txt'):
    ad, st = line.split('|')
    removed_ads[ad] = st

assets = {}
for line in rows('assets_r*.txt'):
    # asset_id|asset_suffix|url0|extra_urls
    aid, suf, url, extra = line.split('|')
    assert aid not in assets, ('dup asset', aid)
    assets[aid] = dict(suffix=suf, url=url or None, extra=extra)

asset_appr = {}
for line in rows('asset_approval.txt'):
    aid, appr = line.split('|')
    asset_appr[aid] = appr

link_exc = {}   # ('campaignAssets'|'adGroupAssets', parent_id, asset_id) -> status (non-ENABLED links)
for line in rows('links_exc.txt'):
    kind, parent, aid, st = line.split('|')
    link_exc[(kind, parent, aid)] = st

new_ads = []
for line in rows('new_ads.txt'):
    new_ads.append(json.loads(line))

CUSTOMER_SUFFIX = ''  # customer.final_url_suffix not set (read 12-Oct)


def camp_status_label(cid):
    c = camps.get(cid)
    if c is None:
        return None, 'campaign %s not in campaign read' % cid
    return c, None


def hier_status(c, agst, adst):
    """effective status using the same convention as the 11-Oct pull"""
    if c['status'] == 'REMOVED':
        return 'CAMPAIGN_REMOVED'
    if c['status'] == 'PAUSED':
        return 'CAMPAIGN_PAUSED'
    if agst == 'REMOVED':
        return 'ADGROUP_REMOVED'
    if agst == 'PAUSED':
        return 'ADGROUP_PAUSED'
    if adst == 'PAUSED':
        return 'AD_PAUSED'
    if c['serving'] == 'ENDED':
        return 'CAMPAIGN_ENDED'
    return 'ENABLED'


out = []
stats = collections.Counter()
for r in inp:
    slot = r['slot']
    o = {'platform': 'google', 'account_id': ACC, 'ad_id': r['ad_id'], 'slot': slot}
    if slot.startswith('sitelink asset '):
        aid = r['ad_id']
        kind = 'campaignAssets' if slot.endswith('(campaign_asset)') else 'adGroupAssets'
        assert slot == f'sitelink asset {aid} final_urls[0] ({"campaign_asset" if kind == "campaignAssets" else "ad_group_asset"})'
        import re
        m = re.search(r'customers/%s/%s/(\d+)~(\d+)~SITELINK' % (ACC, kind), r['notes_11oct'])
        assert m and m.group(2) == aid, r
        parent = m.group(1)
        a = assets.get(aid)
        if a is None:
            o.update(url=None, status_now='DELETED', creative_id_now=None, found=False,
                     note='sitelink asset %s not returned by asset read (asset no longer exists)' % aid)
            stats['asset_missing'] += 1
            out.append(o)
            continue
        link_st = link_exc.get((kind, parent, aid), 'ENABLED')
        if kind == 'campaignAssets':
            cid = parent
            ag = None
            agst = None
            agsuf = ''
        else:
            ag = adgroups.get(parent)
            assert ag is not None, ('ad group not read', parent)
            cid = ag['cid']
            agst = ag['status']
            agsuf = ag['suffix']
        c = camps[cid]
        # effective suffix for a sitelink: asset > (ad group, for ad-group-level link) > campaign > customer
        if a['suffix']:
            suf, lvl = a['suffix'], 'asset'
        elif agsuf:
            suf, lvl = agsuf, 'ad group'
        elif c['suffix']:
            suf, lvl = c['suffix'], 'campaign'
        elif CUSTOMER_SUFFIX:
            suf, lvl = CUSTOMER_SUFFIX, 'account'
        else:
            suf, lvl = '', 'none'
        url = join_suffix(a['url'], suf)
        if link_st == 'REMOVED':
            st = 'LINK_REMOVED'
        else:
            st = hier_status(c, agst or 'ENABLED', 'ENABLED')
            if st == 'ENABLED' and link_st != 'ENABLED':
                st = 'LINK_' + link_st
        notes = ['SITELINK asset (not an ad)',
                 'placement %s customers/%s/%s/%s~%s~SITELINK' % ('campaign' if kind == 'campaignAssets' else 'ad group', ACC, kind, parent, aid),
                 'link_status=%s' % link_st]
        if kind == 'adGroupAssets':
            notes.append('adgroup_status=%s' % agst)
        notes.append('campaign %s status=%s serving_status=%s' % (cid, c['status'], c['serving']))
        if aid in asset_appr:
            notes.append('asset approval_status=%s' % asset_appr[aid])
        notes.append('effective suffix level=%s' % lvl)
        if a['extra']:
            notes.append('other urls: %s' % a['extra'])
        notes.append('URL %s vs 11-Oct' % ('unchanged' if url == r['url_11oct'] else 'CHANGED'))
        o.update(url=url, status_now=st, creative_id_now=aid, found=True, note='; '.join(notes))
        stats['sitelink_ok'] += 1
        stats['sitelink_changed' if url != r['url_11oct'] else 'sitelink_same'] += 1
        out.append(o)
        continue

    assert slot == 'ad.final_urls[0]', slot
    ad = r['ad_id']
    a = ads.get(ad)
    if a is None:
        st = removed_ads.get(ad)
        if st is None:
            raise SystemExit('ad %s neither in ads read nor in removed read' % ad)
        o.update(url=None, status_now=st, creative_id_now=None, found=False,
                 note='ad %s status=%s in ad_group_ad (deleted since 11-Oct pull); no current URL' % (ad, st))
        stats['ad_removed'] += 1
        out.append(o)
        continue
    c = camps[a['cid']]
    if a['suffix']:
        suf, lvl = a['suffix'], 'ad'
    elif a['ag_suffix']:
        suf, lvl = a['ag_suffix'], 'ad group'
    elif c['suffix']:
        suf, lvl = c['suffix'], 'campaign'
    elif CUSTOMER_SUFFIX:
        suf, lvl = CUSTOMER_SUFFIX, 'account'
    else:
        suf, lvl = '', 'none'
    url = join_suffix(a['url'], suf)
    st = hier_status(c, a['ag_status'], a['status'])
    notes = ['ad_status=%s' % a['status'], 'adgroup_status=%s' % a['ag_status'],
             'campaign_status=%s (serving_status=%s)' % (c['status'], c['serving']),
             'approval_status=%s' % a['approval'], 'primary_status=%s' % a['primary'],
             'ad group %s, campaign %s' % (a['ag'], a['cid']),
             'effective suffix level=%s' % lvl]
    if a['extra']:
        notes.append('other urls: %s' % a['extra'])
    notes.append('URL %s vs 11-Oct' % ('unchanged' if url == r['url_11oct'] else 'CHANGED'))
    o.update(url=url, status_now=st, creative_id_now=None, found=True, note='; '.join(notes))
    stats['ad_ok'] += 1
    stats['ad_changed' if url != r['url_11oct'] else 'ad_same'] += 1
    out.append(o)

assert len(out) == len(inp)
with open(OUT, 'w', encoding='utf-8') as f:
    for o in out:
        f.write(json.dumps(o, ensure_ascii=False) + '\n')

with open(NEW, 'w', encoding='utf-8') as f:
    for n in new_ads:
        f.write(json.dumps(n, ensure_ascii=False) + '\n')

print(dict(stats))
print('rows', len(out), 'new rows', len(new_ads))
