import json, re
from urllib.parse import urlsplit, parse_qsl
B = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
W = B + '/reread3/work_meta_1198625455580757'
IN = B + '/reread/in/meta_1198625455580757.json'
PREV12 = B + '/reread2/out/meta_1198625455580757.jsonl'
OUTD = B + '/reread3/out'
OUT = OUTD + '/meta_1198625455580757.jsonl'
NEW = OUTD + '/new_meta_1198625455580757.jsonl'
ACC = '1198625455580757'
ACC_NAME = 'Diriyah Company - Visit Diriyah  Billed to MS KSA'
store = json.load(open(W + '/data/ads_store.json'))
d = json.load(open(IN))
prev12 = {}
for line in open(PREV12, encoding='utf-8'):
    o = json.loads(line)
    prev12[(o['ad_id'], o['slot'])] = o

def resolve(obj, path):
    cur = obj
    for part in path.split('.'):
        m = re.fullmatch(r'(\w+)(?:\[(\d+)\])?', part)
        if not m:
            return False, None
        k, i = m.group(1), m.group(2)
        if not isinstance(cur, dict) or k not in cur:
            return False, None
        cur = cur[k]
        if i is not None:
            if not isinstance(cur, list) or int(i) >= len(cur):
                return False, None
            cur = cur[int(i)]
    return True, cur

def join_tags(link, tags):
    if not tags or link is None:
        return link
    tags = tags.lstrip('?&')
    if link.endswith('?') or link.endswith('&'):
        return link + tags
    return link + ('&' if '?' in link else '?') + tags

def qdiff(old, new):
    if old is None or new is None:
        return None
    so, sn = urlsplit(old), urlsplit(new)
    parts = []
    if (so.scheme, so.netloc, so.path) != (sn.scheme, sn.netloc, sn.path):
        parts.append('base %s%s -> %s%s' % (so.netloc, so.path, sn.netloc, sn.path))
    po, pn = dict(parse_qsl(so.query, keep_blank_values=True)), dict(parse_qsl(sn.query, keep_blank_values=True))
    for k in list(dict.fromkeys(list(po) + list(pn))):
        if po.get(k) != pn.get(k):
            parts.append('%s: %s -> %s' % (k, po.get(k, '(absent)'), pn.get(k, '(absent)')))
    if not parts and old != new:
        parts.append('query string differs in order/encoding only')
    return parts

rows_out = []
for r in d:
    aid = r['ad_id']
    ad = store.get(aid)
    if ad is None or ad.get('effective_status') == 'DELETED':
        rows_out.append({'platform': 'meta', 'account_id': ACC, 'ad_id': aid, 'slot': r['slot'], 'url': None,
                         'status_now': (ad or {}).get('effective_status') or 'NOT_FOUND',
                         'creative_id_now': ((ad or {}).get('creative') or {}).get('id'), 'found': False,
                         'note': 'ad deleted: not returned by act_%s/ads with effective_status IN [all values incl. ARCHIVED, DELETED]' % ACC if ad is None
                                 else 'ad effective_status DELETED'})
        continue
    cr = ad.get('creative', {}) or {}
    crid = cr.get('id')
    tags = cr.get('url_tags')
    ok, val = resolve(ad, r['slot'])
    notes = []
    if crid == r['creative_id']:
        notes.append('creative unchanged since 11-Oct (%s)' % crid)
    else:
        notes.append('creative CHANGED since 11-Oct: %s -> %s (current creative "%s")' % (r['creative_id'], crid, (cr.get('name') or '')[:120]))
    p12 = prev12.get((aid, r['slot']))
    if p12 is not None:
        if p12.get('creative_id_now') != crid:
            notes.append('creative also changed since the 12-Oct re-read (%s -> %s)' % (p12.get('creative_id_now'), crid))
    notes.append('ad updated_time %s' % ad.get('updated_time'))
    per_link_tags = None
    if not ok:
        url = None
        notes.append('slot path not present in current creative')
    elif val is not None and not isinstance(val, str):
        url = None
        notes.append('slot value is not a string: %r' % (val,))
    else:
        url = val
        if 'asset_feed_spec.link_urls' in r['slot']:
            m = re.match(r'creative\.asset_feed_spec\.link_urls\[(\d+)\]', r['slot'])
            lu = (cr.get('asset_feed_spec') or {}).get('link_urls')[int(m.group(1))]
            per_link_tags = lu.get('url_tags')
            if per_link_tags:
                url = join_tags(url, per_link_tags)
        url = join_tags(url, tags)
    notes.append('creative.url_tags %s' % (('= ' + tags) if tags else 'not set'))
    afs = cr.get('asset_feed_spec') or {}
    oss = cr.get('object_story_spec') or {}
    if 'asset_feed_spec.link_urls' in r['slot']:
        lus = afs.get('link_urls') or []
        lu = lus[0] if lus else {}
        extra = sorted(set(lu) - {'adlabels', 'website_url', 'display_url', 'url_tags'})
        notes.append('asset_feed_spec.optimization_type=%s; link_urls has %d entr%s; link_urls[0] used by %d placement asset label(s); %s%s' % (
            afs.get('optimization_type'), len(lus), 'y' if len(lus) == 1 else 'ies', len(lu.get('adlabels') or []),
            ('link_urls[0].url_tags = %s (appended)' % per_link_tags) if per_link_tags else 'no per-link url_tags',
            ('; other link_urls[0] keys: ' + ', '.join('%s=%s' % (k, lu[k]) for k in extra)) if extra else '; no deeplink_url'))
    ld = oss.get('link_data') or {}
    if 'child_attachments' in r['slot']:
        ch = ld.get('child_attachments') or []
        links = set(c.get('link') for c in ch) | ({ld.get('link')} if ld.get('link') else set())
        notes.append('carousel link_data with %d child_attachments; %s' % (
            len(ch), 'all child links + link_data.link identical' if len(links) == 1 else '%d distinct URLs across link_data.link + child links' % len(links)))
    elif r['slot'] == 'creative.object_story_spec.link_data.link':
        ch = ld.get('child_attachments') or []
        if ch:
            links = set(c.get('link') for c in ch) | {ld.get('link')}
            notes.append('carousel link_data with %d child_attachments; %s' % (
                len(ch), 'all child links + link_data.link identical' if len(links) == 1 else '%d distinct URLs across link_data.link + child links' % len(links)))
        else:
            notes.append('single-link link_data')
        if afs.get('optimization_type') and not afs.get('link_urls'):
            notes.append('asset_feed_spec only carries optimization_type=%s (no link_urls)' % afs.get('optimization_type'))
    if 'video_data' in r['slot']:
        top = ((cr.get('call_to_action') or {}).get('value') or {}).get('link')
        if top is not None:
            notes.append('creative.call_to_action.value.link %s' % ('identical to slot value' if top == val else 'DIFFERS: ' + top))
    if r['status_11oct'] != ad.get('effective_status'):
        notes.append('effective_status 11-Oct %s -> now %s' % (r['status_11oct'], ad.get('effective_status')))
    else:
        notes.append('effective_status unchanged (%s)' % ad.get('effective_status'))
    if ad.get('status') != ad.get('effective_status'):
        notes.append('ad configured status %s' % ad.get('status'))
    if cr.get('effective_object_story_id'):
        notes.append('effective_object_story_id=%s' % cr['effective_object_story_id'])
    diff = qdiff(r['url_11oct'], url)
    if diff is None:
        notes.append('url null')
    elif not diff:
        notes.append('URL identical to 11-Oct')
    else:
        notes.append('URL changed vs 11-Oct: ' + '; '.join(diff))
    if p12 is not None:
        if p12.get('url') == url:
            notes.append('URL identical to the 12-Oct re-read')
        elif p12.get('url') == r['url_11oct']:
            notes.append('URL changed since the 12-Oct re-read (the 12-Oct re-read still had the 11-Oct URL; change made on 13-Oct)')
        else:
            dd = qdiff(p12.get('url'), url)
            notes.append('URL changed since the 12-Oct re-read: ' + ('; '.join(dd) if dd else 'null <-> value'))
    rows_out.append({'platform': 'meta', 'account_id': ACC, 'ad_id': aid, 'slot': r['slot'], 'url': url,
                     'status_now': ad.get('effective_status'), 'creative_id_now': crid, 'found': True,
                     'note': '; '.join(notes)})

with open(OUT, 'w', encoding='utf-8') as f:
    for o in rows_out:
        f.write(json.dumps(o, ensure_ascii=False) + '\n')

inids = set(r['ad_id'] for r in d)
new = [a for a in store if a not in inids and store[a].get('effective_status') != 'DELETED']
with open(NEW, 'w', encoding='utf-8') as f:
    for a in new:
        ad = store[a]
        f.write(json.dumps({'platform': 'meta', 'account_id': ACC, 'account_name': ACC_NAME,
                            'campaign_name': (ad.get('campaign') or {}).get('name'), 'adset_name': (ad.get('adset') or {}).get('name'),
                            'ad_id': a, 'ad_name': ad.get('name'), 'effective_status': ad.get('effective_status'),
                            'slot': None, 'url': None}, ensure_ascii=False) + '\n')
print('wrote', len(rows_out), 'rows;', len(new), 'new ads')
