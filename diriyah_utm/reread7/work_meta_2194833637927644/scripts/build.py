"""Build the keyed 14-Oct re-read (one line per input row) and the new-ads file for Meta act_2194833637927644 ("Diriyah Co").
Inputs: data/details.json (current ad + current creative per ad, read 14-Oct via id-filtered GET act_/ads with every effective_status),
        data/inventory.json (every ad in the account, all statuses incl. ARCHIVED / DELETED, read 14-Oct),
        the 11-Oct input list, and the 13-Oct keyed re-read (reread5) for a "changed since 13-Oct" remark.
Usage: build.py IN_FILE PREV13_JSONL OUT_FILE NEW_FILE READ_AT_TEXT
"""
import json, re, sys
from collections import Counter, defaultdict
from urllib.parse import urlsplit, parse_qsl

IN_FILE, PREV13, OUT_FILE, NEW_FILE, READ_AT = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
ACCOUNT_ID, ACCOUNT_NAME = '2194833637927644', 'Diriyah Co'

rows = json.load(open(IN_FILE, encoding='utf-8'))
det = json.load(open('data/details.json', encoding='utf-8'))
inv = json.load(open('data/inventory.json', encoding='utf-8'))
prev13 = {}
for line in open(PREV13, encoding='utf-8'):
    x = json.loads(line)
    prev13[(x['ad_id'], x['slot'])] = x


def resolve(obj, path):
    cur = obj
    for tok in path.split('.'):
        m = re.fullmatch(r'([A-Za-z_]+)(?:\[(\d+)\])?', tok)
        if not m or not isinstance(cur, dict) or m.group(1) not in cur:
            return False, None
        cur = cur[m.group(1)]
        if m.group(2) is not None:
            i = int(m.group(2))
            if not isinstance(cur, list) or i >= len(cur):
                return False, None
            cur = cur[i]
    return True, cur


def with_tags(link, tags):
    """Meta appends creative.url_tags to the destination URL's query string (before any #fragment)."""
    if not tags or link is None:
        return link
    base, hashpart = (link.split('#', 1) + [None])[:2]
    joined = base + ('&' if '?' in base else '?') + tags
    return joined + ('#' + hashpart if hashpart is not None else '')


def param_diff(old, new):
    try:
        o, n = urlsplit(old), urlsplit(new)
    except Exception:
        return ''
    parts = []
    if (o.scheme, o.netloc, o.path) != (n.scheme, n.netloc, n.path):
        parts.append('base URL changed (%s%s -> %s%s)' % (o.netloc, o.path, n.netloc, n.path))
    od, nd = dict(parse_qsl(o.query, keep_blank_values=True)), dict(parse_qsl(n.query, keep_blank_values=True))
    ch = [k for k in nd if k in od and od[k] != nd[k]]
    add = [k for k in nd if k not in od]
    rem = [k for k in od if k not in nd]
    if ch:
        parts.append('changed: ' + ', '.join(ch))
    if add:
        parts.append('added: ' + ', '.join(add))
    if rem:
        parts.append('removed: ' + ', '.join(rem))
    if o.fragment != n.fragment:
        parts.append('fragment %r -> %r' % (o.fragment, n.fragment))
    return '; '.join(parts)


def readable_links(c):
    """Every link the current creative itself exposes (used only to describe existing-post creatives)."""
    out = []
    cta = c.get('call_to_action') or {}
    if (cta.get('value') or {}).get('link'):
        out.append('creative.call_to_action %s -> %s' % (cta.get('type'), cta['value']['link']))
    oss = c.get('object_story_spec') or {}
    ld = oss.get('link_data') or {}
    if ld.get('link'):
        out.append('object_story_spec.link_data.link -> %s' % ld['link'])
    vd = oss.get('video_data') or {}
    if ((vd.get('call_to_action') or {}).get('value') or {}).get('link'):
        out.append('object_story_spec.video_data CTA -> %s' % vd['call_to_action']['value']['link'])
    for i, lu in enumerate((c.get('asset_feed_spec') or {}).get('link_urls') or []):
        if lu.get('website_url'):
            out.append('asset_feed_spec.link_urls[%d] -> %s' % (i, lu['website_url']))
    return out


rows_per_ad = defaultdict(list)
for r in rows:
    rows_per_ad[r['ad_id']].append(r)

out = []
stats = Counter()
for r in rows:
    aid, slot = r['ad_id'], r['slot']
    a = det.get(aid)
    if a is None or a.get('effective_status') == 'DELETED':
        out.append({'platform': 'meta', 'account_id': ACCOUNT_ID, 'ad_id': aid, 'slot': slot, 'url': None,
                    'status_now': (a or {}).get('effective_status') or (inv.get(aid) or {}).get('effective_status') or 'DELETED',
                    'creative_id_now': ((a or {}).get('creative') or {}).get('id'),
                    'found': False,
                    'note': 'ad no longer exists (deleted / not returned by GET act_%s/ads with every effective_status incl. ARCHIVED and DELETED); %s'
                            % (ACCOUNT_ID, READ_AT)})
        stats['not_found'] += 1
        continue
    c = a.get('creative') or {}
    cid_now = c.get('id')
    es, cs = a.get('effective_status'), a.get('configured_status')
    p13 = prev13.get((aid, slot)) or {}
    parts = []
    if cid_now == r['creative_id']:
        parts.append('creative unchanged since 11-Oct (%s)' % cid_now)
    else:
        parts.append('creative changed since 11-Oct (%s -> %s)' % (r['creative_id'], cid_now))
    if p13.get('creative_id_now') and p13['creative_id_now'] != cid_now:
        parts.append('creative changed since the 13-Oct re-read (%s -> %s; ad updated_time %s)' % (p13['creative_id_now'], cid_now, a.get('updated_time')))
    tags = c.get('url_tags')
    if slot.startswith('existing post'):
        url = None
        osid = c.get('object_story_id') or c.get('effective_object_story_id')
        links = readable_links(c)
        cta = c.get('call_to_action')
        cta_txt = ('creative.call_to_action type %s has no link value' % cta.get('type')) if (cta and not (cta.get('value') or {}).get('link')) else (
            'creative.call_to_action not present' if not cta else None)
        if c.get('object_story_id'):
            desc = 'still a boosted existing page post (object_story_id %s, object_type %s)' % (osid, c.get('object_type'))
        else:
            desc = ('still runs on existing post effective_object_story_id %s (creative has no object_story_id; object_story_spec holds only %s, '
                    'no link_data / video_data CTA link; object_type %s)') % (
                osid, ', '.join(sorted((c.get('object_story_spec') or {}).keys())) or 'nothing', c.get('object_type'))
        if c.get('source_instagram_media_id'):
            desc += ', source_instagram_media_id %s' % c['source_instagram_media_id']
        parts.append(desc)
        if links:
            parts.append('links now readable on the creative: ' + ' | '.join(links))
        else:
            parts.append('no link readable on the creative (no object_story_spec link / asset_feed_spec link_urls)')
        if cta_txt:
            parts.append(cta_txt)
        parts.append('creative.url_tags %s' % ('set: ' + tags if tags else 'not set'))
        parts.append('url kept null as on 11-Oct (the link lives on the existing post)')
        stats['existing_post_null'] += 1
    else:
        ok, link = resolve(a, slot)
        if not ok or not link:
            url = None
            alt = readable_links(c)
            parts.append('slot path %s not present on the current creative; url null%s'
                         % (slot, ('; links on the current creative: ' + ' | '.join(alt)) if alt else ''))
            stats['slot_missing'] += 1
        else:
            url = with_tags(link, tags)
            parts.append(('creative.url_tags "%s" appended to the stored link' % tags) if tags else 'creative.url_tags not set')
            if slot.startswith('creative.asset_feed_spec.link_urls['):
                lus = (c.get('asset_feed_spec') or {}).get('link_urls') or []
                n_then = sum(1 for x in rows_per_ad[aid] if x['slot'].startswith('creative.asset_feed_spec.link_urls['))
                parts.append('asset_feed_spec has %d link_urls now (%d on 11-Oct)' % (len(lus), n_then))
                i = int(re.search(r'link_urls\[(\d+)\]', slot).group(1))
                if i < len(lus) and lus[i].get('url_tags'):
                    parts.append('NOTE link_urls[%d].url_tags also set: %s' % (i, lus[i]['url_tags']))
            elif slot.startswith('creative.object_story_spec.link_data.child_attachments['):
                n_now = len(((c.get('object_story_spec') or {}).get('link_data') or {}).get('child_attachments') or [])
                n_then = sum(1 for x in rows_per_ad[aid] if x['slot'].startswith('creative.object_story_spec.link_data.child_attachments['))
                parts.append('carousel has %d child_attachments now (%d on 11-Oct)' % (n_now, n_then))
            elif slot == 'creative.call_to_action.value.link' and c.get('source_instagram_media_id'):
                parts.append('boosted Instagram post source_instagram_media_id %s' % c['source_instagram_media_id'])
            if url == r['url_11oct']:
                parts.append('URL unchanged vs 11-Oct')
                stats['url_same_11oct'] += 1
            else:
                d = param_diff(r['url_11oct'] or '', url or '')
                parts.append('URL changed vs 11-Oct' + (' (%s)' % d if d else ''))
                stats['url_changed_11oct'] += 1
            if (aid, slot) in prev13:
                if p13.get('url') == url:
                    parts.append('same URL as the 13-Oct re-read')
                    stats['url_same_13oct'] += 1
                else:
                    d = param_diff(p13.get('url') or '', url or '')
                    parts.append('URL changed since the 13-Oct re-read' + (' (%s)' % d if d else ''))
                    stats['url_changed_13oct'] += 1
    st = ('status unchanged (%s)' % es) if es == r['status_11oct'] else ('status 11-Oct %s -> now %s' % (r['status_11oct'], es))
    if cs and cs != es:
        st += ' (configured_status %s)' % cs
    parts.append(st)
    parts.append('ad updated_time %s' % a.get('updated_time'))
    parts.append(READ_AT)
    out.append({'platform': 'meta', 'account_id': ACCOUNT_ID, 'ad_id': aid, 'slot': slot, 'url': url,
                'status_now': es, 'creative_id_now': cid_now, 'found': True, 'note': '; '.join(parts)})
    stats['found'] += 1
    stats['creative_changed_11oct' if cid_now != r['creative_id'] else 'creative_same_11oct'] += 1

with open(OUT_FILE, 'w', encoding='utf-8') as f:
    for o in out:
        f.write(json.dumps(o, ensure_ascii=False) + '\n')

# ---- Task 2: ads not in the input (skip DELETED) ----
input_ids = set(rows_per_ad)
new_rows = []
for aid, a in sorted(det.items(), key=lambda kv: (kv[1].get('created_time', ''), kv[0])):
    if aid in input_ids or a.get('effective_status') == 'DELETED':
        continue
    c = a.get('creative') or {}
    tags = c.get('url_tags')
    slots = []
    for i, lu in enumerate((c.get('asset_feed_spec') or {}).get('link_urls') or []):
        if lu.get('website_url'):
            slots.append(('creative.asset_feed_spec.link_urls[%d].website_url' % i, lu['website_url']))
    oss = c.get('object_story_spec') or {}
    ld = oss.get('link_data') or {}
    if ld.get('link'):
        slots.append(('creative.object_story_spec.link_data.link', ld['link']))
    if ((ld.get('call_to_action') or {}).get('value') or {}).get('link'):
        slots.append(('creative.object_story_spec.link_data.call_to_action.value.link', ld['call_to_action']['value']['link']))
    for i, ch in enumerate(ld.get('child_attachments') or []):
        if ch.get('link'):
            slots.append(('creative.object_story_spec.link_data.child_attachments[%d].link' % i, ch['link']))
    vd = oss.get('video_data') or {}
    if ((vd.get('call_to_action') or {}).get('value') or {}).get('link'):
        slots.append(('creative.object_story_spec.video_data.call_to_action.value.link', vd['call_to_action']['value']['link']))
    td = oss.get('template_data') or {}
    if td.get('link'):
        slots.append(('creative.object_story_spec.template_data.link', td['link']))
    if not slots and ((c.get('call_to_action') or {}).get('value') or {}).get('link'):
        slots.append(('creative.call_to_action.value.link', c['call_to_action']['value']['link']))
    if not slots:
        slots.append(('existing post CTA (unreadable)', None))
    for s, link in slots:
        new_rows.append({'platform': 'meta', 'account_id': ACCOUNT_ID, 'account_name': ACCOUNT_NAME,
                         'campaign_name': (a.get('campaign') or {}).get('name'), 'adset_name': (a.get('adset') or {}).get('name'),
                         'ad_id': aid, 'ad_name': a.get('name'), 'effective_status': a.get('effective_status'),
                         'slot': s, 'url': with_tags(link, tags)})

# every non-deleted ad in the inventory must be either an input ad or a listed new ad
non_deleted = {k for k, v in inv.items() if v.get('effective_status') != 'DELETED'}
unlisted = sorted(non_deleted - input_ids - {x['ad_id'] for x in new_rows})
assert not unlisted, unlisted
missing_names = [x['ad_id'] for x in new_rows if not x['campaign_name'] or not x['adset_name']]
assert not missing_names, missing_names

with open(NEW_FILE, 'w', encoding='utf-8') as f:
    for o in new_rows:
        f.write(json.dumps(o, ensure_ascii=False) + '\n')

print(json.dumps({'rows': len(out), 'stats': stats, 'new_rows': len(new_rows), 'new_ads': len({x["ad_id"] for x in new_rows}),
                  'new_status': Counter(x['effective_status'] for x in {y['ad_id']: y for y in new_rows}.values()),
                  'deleted_skipped': sorted(k for k, v in inv.items() if v.get('effective_status') == 'DELETED' and k not in input_ids)},
                 default=dict))
