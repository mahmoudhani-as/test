import json, re
from urllib.parse import urlsplit, parse_qsl
W = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/reread2/work_meta_1198625455580757'
IN = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/reread/in/meta_1198625455580757.json'
OUTD = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/reread2/out'
OUT = OUTD + '/meta_1198625455580757.jsonl'
NEW = OUTD + '/new_meta_1198625455580757.jsonl'
ACC = '1198625455580757'
store = json.load(open(W + '/data/ads_store.json'))
d = json.load(open(IN))

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
    if not tags:
        return link
    if link is None:
        return None
    sep = '&' if '?' in link else '?'
    if link.endswith('?') or link.endswith('&'):
        sep = ''
    return link + sep + tags.lstrip('?&')

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
    return parts

rows_out = []
for r in d:
    aid = r['ad_id']
    ad = store.get(aid)
    if ad is None:
        rows_out.append({'platform': 'meta', 'account_id': ACC, 'ad_id': aid, 'slot': r['slot'], 'url': None,
                         'status_now': 'NOT_FOUND', 'creative_id_now': None, 'found': False,
                         'note': 'ad not returned by act_%s/ads with all effective_status values incl. ARCHIVED/DELETED - treated as deleted' % ACC})
        continue
    cr = ad.get('creative', {}) or {}
    crid = cr.get('id')
    tags = cr.get('url_tags')
    ok, val = resolve(ad, r['slot'])
    notes = []
    if crid == r['creative_id']:
        notes.append('creative unchanged since 11-Oct (%s)' % crid)
    else:
        notes.append('creative CHANGED since 11-Oct: %s -> %s (new creative "%s")' % (r['creative_id'], crid, (cr.get('name') or '')[:110]))
    notes.append('ad updated_time %s' % ad.get('updated_time'))
    if not ok:
        url = None
        notes.append('slot path not present in current creative')
    else:
        url = join_tags(val, tags)
    notes.append('creative.url_tags %s' % (('= ' + tags) if tags else 'not set'))
    afs = cr.get('asset_feed_spec') or {}
    oss = cr.get('object_story_spec') or {}
    if 'asset_feed_spec.link_urls' in r['slot']:
        lus = afs.get('link_urls') or []
        lu = lus[0] if lus else {}
        du = lu.get('display_url')
        dtxt = 'display_url not set' if du is None else ('display_url empty' if du == '' else 'display_url=' + du)
        extra = sorted(set(lu) - {'adlabels', 'website_url', 'display_url'})
        notes.append('asset_feed_spec.optimization_type=%s; link_urls has %d entr%s; link_urls[0] used by %d placement asset label(s); %s; %s' % (
            afs.get('optimization_type'), len(lus), 'y' if len(lus) == 1 else 'ies', len(lu.get('adlabels') or []),
            ('other link_urls[0] keys: ' + ', '.join('%s=%s' % (k, lu[k]) for k in extra)) if extra else 'no per-link url_tags/deeplink_url', dtxt))
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
        if afs.get('optimization_type') == 'DEGREES_OF_FREEDOM' and not afs.get('link_urls'):
            notes.append('asset_feed_spec only carries optimization_type=DEGREES_OF_FREEDOM (no link_urls)')
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
        # (not expected: no new ads)
        f.write(json.dumps({'platform': 'meta', 'account_id': ACC, 'ad_id': a}) + '\n')
print('wrote', len(rows_out), 'rows;', len(new), 'new ads')
