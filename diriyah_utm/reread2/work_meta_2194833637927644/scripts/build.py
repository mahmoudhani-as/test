"""Build the keyed re-read output (one line per input row) and the new-ads file for Meta act_2194833637927644.
Inputs: data/details.json (current ad + creative per input ad), data/new_ads.json (ads not in the input),
        data/final_check.json (post-read consistency check), the 11-Oct input list.
"""
import json, re, sys
from collections import Counter, defaultdict

IN_FILE, OUT_FILE, NEW_FILE = sys.argv[1], sys.argv[2], sys.argv[3]
ACCOUNT_ID, ACCOUNT_NAME = '2194833637927644', 'Diriyah Co'
READ_AT = 'read 2026-10-12 23:18-23:21 UTC (GET act_2194833637927644/ads, ids filter, all statuses incl. ARCHIVED/DELETED; re-checked 23:21 UTC: no ad changed after the read)'

rows = json.load(open(IN_FILE, encoding='utf-8'))
det = json.load(open('data/details.json', encoding='utf-8'))
new_ads = json.load(open('data/new_ads.json', encoding='utf-8'))
final = json.load(open('data/final_check.json', encoding='utf-8'))


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
                    'status_now': (a or {}).get('effective_status', 'DELETED'), 'creative_id_now': (a or {}).get('creative', {}).get('id'),
                    'found': False, 'note': 'ad no longer exists (deleted / not returned by GET act_%s/ads with all statuses incl. DELETED); %s' % (ACCOUNT_ID, READ_AT)})
        stats['not_found'] += 1
        continue
    c = a.get('creative') or {}
    cid_now = c.get('id')
    es, cs = a.get('effective_status'), a.get('configured_status')
    parts = []
    if cid_now == r['creative_id']:
        parts.append('creative unchanged since 11-Oct (%s)' % cid_now)
    else:
        parts.append('creative changed since 11-Oct (%s -> %s; ad updated_time %s)' % (r['creative_id'], cid_now, a.get('updated_time')))
    tags = c.get('url_tags')
    if slot.startswith('existing post'):
        url = None
        osid = c.get('object_story_id') or c.get('effective_object_story_id')
        cta = c.get('call_to_action')
        if cta and (cta.get('value') or {}).get('link'):
            cta_txt = 'creative.call_to_action %s -> %s (now readable on the creative)' % (cta.get('type'), cta['value']['link'])
        elif cta:
            cta_txt = 'creative.call_to_action type %s has no link value' % cta.get('type')
        else:
            cta_txt = 'creative.call_to_action not present'
        has_spec_link = bool((c.get('object_story_spec') or {}).get('link_data') or (c.get('object_story_spec') or {}).get('video_data') or (c.get('asset_feed_spec') or {}).get('link_urls'))
        parts.append('still a boosted existing page post (object_story_id %s, object_type %s); %s; %s; creative.url_tags %s; url kept null as on 11-Oct (link lives on the post, not readable via ad/creative fields)'
                     % (osid, c.get('object_type'), 'no object_story_spec/asset_feed_spec link on the creative' if not has_spec_link else 'creative now carries an object_story_spec/asset_feed_spec link', cta_txt, 'set: ' + tags if tags else 'not set'))
        stats['existing_post_null'] += 1
    else:
        ok, link = resolve(a, slot)
        if not ok:
            url = None
            parts.append('slot path %s not present on the current creative; url null' % slot)
            stats['slot_missing'] += 1
        else:
            url = with_tags(link, tags)
            if tags:
                parts.append('creative.url_tags "%s" appended to the stored link' % tags)
            else:
                parts.append('creative.url_tags not set')
            if slot.startswith('creative.asset_feed_spec.link_urls['):
                n_now = len((c.get('asset_feed_spec') or {}).get('link_urls') or [])
                n_then = sum(1 for x in rows_per_ad[aid] if x['slot'].startswith('creative.asset_feed_spec.link_urls['))
                parts.append('asset_feed_spec has %d link_urls now (%d on 11-Oct)' % (n_now, n_then))
            elif slot.startswith('creative.object_story_spec.link_data.child_attachments['):
                n_now = len(((c.get('object_story_spec') or {}).get('link_data') or {}).get('child_attachments') or [])
                n_then = sum(1 for x in rows_per_ad[aid] if x['slot'].startswith('creative.object_story_spec.link_data.child_attachments['))
                parts.append('carousel has %d child_attachments now (%d on 11-Oct)' % (n_now, n_then))
            elif slot == 'creative.call_to_action.value.link' and c.get('source_instagram_media_id'):
                parts.append('boosted Instagram post source_instagram_media_id %s' % c['source_instagram_media_id'])
            if url == r['url_11oct']:
                parts.append('URL unchanged vs 11-Oct')
                stats['url_same'] += 1
            else:
                parts.append('URL changed vs 11-Oct')
                stats['url_changed'] += 1
    st = 'status unchanged (%s)' % es if es == r['status_11oct'] else 'status 11-Oct %s -> now %s' % (r['status_11oct'], es)
    if cs and cs != es:
        st += ' (configured_status %s)' % cs
    parts.append(st)
    parts.append(READ_AT)
    out.append({'platform': 'meta', 'account_id': ACCOUNT_ID, 'ad_id': aid, 'slot': slot, 'url': url,
                'status_now': es, 'creative_id_now': cid_now, 'found': True, 'note': '; '.join(parts)})
    stats['found'] += 1
    stats['creative_changed' if cid_now != r['creative_id'] else 'creative_same'] += 1

with open(OUT_FILE, 'w', encoding='utf-8') as f:
    for o in out:
        f.write(json.dumps(o, ensure_ascii=False) + '\n')

# ---- Task 2: ads not in the input (skip DELETED) ----
input_ids = set(rows_per_ad)
new_rows = []
for aid, a in sorted(new_ads.items(), key=lambda kv: (kv[1].get('created_time', ''), kv[0])):
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

# every non-deleted ad in the final inventory must be either an input ad or a listed new ad
non_deleted = {k for k, v in final.items() if v.get('effective_status') != 'DELETED'}
unlisted = sorted(non_deleted - input_ids - {x['ad_id'] for x in new_rows})
assert not unlisted, unlisted

with open(NEW_FILE, 'w', encoding='utf-8') as f:
    for o in new_rows:
        f.write(json.dumps(o, ensure_ascii=False) + '\n')

print(json.dumps({'rows': len(out), 'stats': stats, 'new_rows': len(new_rows), 'new_ads': len({x["ad_id"] for x in new_rows})}, default=dict))
