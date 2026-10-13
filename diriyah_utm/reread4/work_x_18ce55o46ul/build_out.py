import json, re, sys, datetime, collections

W = sys.argv[1]
IN = sys.argv[2]
OUT = sys.argv[3]
NEWOUT = sys.argv[4]
ACCOUNT_ID = '18ce55o46ul'
ACCOUNT_NAME = 'H&S-DiriyahCo'

inp = json.load(open(IN, encoding='utf-8'))
pts_l = json.load(open(W + '/promoted_tweets.json', encoding='utf-8'))
pts = {p['id']: p for p in pts_l}
li = {x['id']: x for x in json.load(open(W + '/line_items.json', encoding='utf-8'))}
cp = {x['id']: x for x in json.load(open(W + '/campaigns.json', encoding='utf-8'))}
tw = json.load(open(W + '/tweets.json', encoding='utf-8'))
cards = json.load(open(W + '/cards.json', encoding='utf-8'))
NOW = datetime.datetime.now(datetime.timezone.utc)
READ_AT = NOW.strftime('%d-%b-%Y %H:%M UTC')
NS = 'ACTIVE_NOT_SERVABLE (campaign servable=false, e.g. ended flight/budget)'
UNREADABLE = ('card still not readable on 13-Oct re-read: LIST_CARDS (card_ids, include_legacy_cards=true, '
              'with_deleted=true), LIST_CARDS (card_uris) and LIST_CARDS_ALL (card_uris) all returned an empty '
              'data array - card is not owned by this ads account (boosted organic post)')


def status(pt):
    """Same derivation as the 11-Oct pull."""
    l = li[pt['line_item_id']]
    c = cp[l['campaign_id']]
    if pt['deleted']:
        return 'DELETED'
    if c['deleted']:
        return 'CAMPAIGN_DELETED'
    if l['deleted']:
        return 'LINE_ITEM_DELETED'
    if pt['entity_status'] != 'ACTIVE':
        return 'AD_' + pt['entity_status']
    if c['entity_status'] != 'ACTIVE':
        return 'CAMPAIGN_' + c['entity_status']
    if l['entity_status'] != 'ACTIVE':
        return 'LINE_ITEM_' + l['entity_status']
    if not c['servable']:
        return NS
    return 'ACTIVE'


def parse_time(s):
    return datetime.datetime.fromisoformat(s.replace('Z', '+00:00')) if s else None


def get_path(obj, path):
    toks = re.findall(r'[A-Za-z_]+|\[\d+\]', path)
    cur = obj
    for t in toks:
        if t.startswith('['):
            i = int(t[1:-1])
            if not isinstance(cur, list) or i >= len(cur):
                return None, 'index %s out of range' % t
            cur = cur[i]
        else:
            if not isinstance(cur, dict) or t not in cur:
                return None, 'key %s missing' % t
            cur = cur[t]
    return cur, None


def card_dests(card):
    out = []
    for i, comp in enumerate(card.get('components') or []):
        if isinstance(comp, dict) and isinstance(comp.get('destination'), dict) and comp['destination'].get('url'):
            out.append(('card.components[%d].destination.url' % i, comp['destination']['url']))
    for i, sl in enumerate(card.get('slides') or []):
        for j, comp in enumerate(sl or []):
            if isinstance(comp, dict) and isinstance(comp.get('destination'), dict) and comp['destination'].get('url'):
                out.append(('card.slides[%d][%d].destination.url' % (i, j), comp['destination']['url']))
    return out


def ctx(pt):
    l = li[pt['line_item_id']]
    c = cp[l['campaign_id']]
    reasons = ','.join(c.get('reasons_not_servable') or []) or '-'
    return ('promoted_tweet %s -> tweet %s (line_item %s entity_status=%s, campaign %s entity_status=%s '
            'effective_status=%s servable=%s reasons_not_servable=%s); approval_status=%s' % (
                pt['id'], pt['tweet_id'], l['id'], l['entity_status'], c['id'], c['entity_status'],
                c.get('effective_status'), c.get('servable'), reasons, pt['approval_status']))


rows = []
for r in inp:
    aid = r['ad_id']
    slot = r['slot']
    o = {'platform': 'x', 'account_id': ACCOUNT_ID, 'ad_id': aid, 'slot': slot}
    pt = pts.get(aid)
    if pt is None:
        o.update(url=None, status_now='NOT_FOUND', creative_id_now=None, found=False,
                 note='promoted_tweet %s not returned by LIST_PROMOTED_TWEETS (with_deleted=true): ad no longer exists' % aid)
        rows.append(o)
        continue
    l = li[pt['line_item_id']]
    c = cp[l['campaign_id']]
    st = status(pt)
    tid = pt['tweet_id']
    o['creative_id_now'] = tid
    o['status_now'] = st
    notes = ['read ' + READ_AT, ctx(pt)]
    if st != r['status_11oct']:
        notes.append('STATUS CHANGED vs 11-Oct (%s -> %s; campaign updated_at %s)' % (r['status_11oct'], st, c.get('updated_at')))
    if str(r['creative_id']) != str(tid):
        notes.append('NB: tweet id differs from 11-Oct creative_id %s' % r['creative_id'])
    if pt['deleted'] or c['deleted'] or l['deleted']:
        o.update(url=None, found=False)
        notes.append('ad is deleted (promoted_tweet deleted=%s, line_item deleted=%s, campaign deleted=%s)' % (
            pt['deleted'], l['deleted'], c['deleted']))
        o['note'] = '; '.join(notes)
        rows.append(o)
        continue
    if st == 'ACTIVE':
        et = parse_time(l.get('end_time'))
        if et and et < NOW:
            notes.append('NB: line item end_time %s has passed, so this ad is not delivering although campaign '
                         '(servable=true), line item and ad are ACTIVE (status derived the same way as 11-Oct)' % l['end_time'])
    t = tw.get(tid)
    if t is None:
        o.update(url=None, found=False)
        notes.append('tweet %s not returned by LIST_TWEETS (tweet_ids, tweet_type=PUBLISHED, timeline_type=ALL): post deleted' % tid)
        o['note'] = '; '.join(notes)
        rows.append(o)
        continue
    cu = t.get('card_uri')
    urls = (t.get('entities') or {}).get('urls') or []
    if slot is None:
        o['url'] = None
        o['found'] = True
        if cu or urls:
            notes.append('NB: tweet now has card_uri=%s and %d url entities (11-Oct: no URL slot)' % (cu, len(urls)))
        else:
            notes.append('no website card and no link in tweet text (no URL slot), same as 11-Oct')
        o['note'] = '; '.join(notes)
        rows.append(o)
        continue
    if slot.startswith('tweet.'):
        o['found'] = True
        val, err = get_path(t, slot[len('tweet.'):])
        ent, _ = get_path(t, slot[len('tweet.'):].rsplit('.', 1)[0])
        tco = ent.get('url') if isinstance(ent, dict) else None
        notes.append('link in tweet text (t.co=%s)' % tco)
        if cu:
            notes.append('tweet card_uri=%s%s' % (cu, ' (website card deleted, no card destination)' if cu.startswith('tombstone') else ''))
        if err:
            notes.append('slot not found in tweet entities now: %s' % err)
        if r['url_11oct'] is None:
            o['url'] = None
            if val and re.match(r'https?://(x|twitter)\.com/i/web/status/', val):
                notes.append("long-form post: API still returns only the truncated 'show more' link (%s); the "
                             "destination inside the full post text is not readable via the Ads API; url kept null as on 11-Oct" % val)
            else:
                notes.append('expanded_url now=%s; url kept null as on 11-Oct' % val)
            o['note'] = '; '.join(notes)
            rows.append(o)
            continue
        o['url'] = val
        if val and 'bit.ly' in val:
            notes.append('bit.ly short link; redirect target not resolved (read-only API pull)')
        if val is not None:
            notes.append('URL unchanged vs 11-Oct' if val == r['url_11oct'] else 'URL CHANGED vs 11-Oct')
        o['note'] = '; '.join(notes)
        rows.append(o)
        continue
    if slot.startswith('card.'):
        o['found'] = True
        if not cu or not cu.startswith('card://'):
            o['url'] = None
            notes.append('tweet has no readable card now (card_uri=%s)' % cu)
            o['note'] = '; '.join(notes)
            rows.append(o)
            continue
        cid = cu[len('card://'):]
        notes.append('card_uri=%s' % cu)
        card = cards.get(cid)
        m = re.match(r'card\.destination\.url \(card_uri=(card://\d+)\)', slot)
        if card is None:
            o['url'] = None
            if m and m.group(1) != cu:
                notes.append('NB: slot card_uri %s differs from tweet card_uri' % m.group(1))
            notes.append(UNREADABLE + ('; url kept null as on 11-Oct' if r['url_11oct'] is None else ''))
            o['note'] = '; '.join(notes)
            rows.append(o)
            continue
        notes.append('card_type=%s' % card.get('card_type'))
        if card.get('deleted'):
            notes.append('NB: card is deleted')
        if m:
            dests = card_dests(card)
            o['url'] = None
            notes.append('card readable now (was unreadable on 11-Oct); destinations: %s; url kept null as on 11-Oct'
                         % '; '.join('%s=%s' % d for d in dests))
            o['note'] = '; '.join(notes)
            rows.append(o)
            continue
        val, err = get_path(card, slot[len('card.'):])
        if r['url_11oct'] is None:
            o['url'] = None
            notes.append('url was null on 11-Oct; card slot now reads %s; url kept null as on 11-Oct' % val)
            o['note'] = '; '.join(notes)
            rows.append(o)
            continue
        o['url'] = val
        if err:
            notes.append('slot not found in card now: %s' % err)
        if val is not None:
            notes.append('URL unchanged vs 11-Oct' if val == r['url_11oct'] else 'URL CHANGED vs 11-Oct')
        o['note'] = '; '.join(notes)
        rows.append(o)
        continue
    o['url'] = None
    o['found'] = True
    notes.append('unrecognised slot format')
    o['note'] = '; '.join(notes)
    rows.append(o)

key_order = ['platform', 'account_id', 'ad_id', 'slot', 'url', 'status_now', 'creative_id_now', 'found', 'note']
with open(OUT, 'w', encoding='utf-8') as f:
    for o in rows:
        f.write(json.dumps({k: o.get(k) for k in key_order}, ensure_ascii=False) + '\n')

# ---- Task 2: ads not in the input, not deleted (ad, line item, campaign) ----
in_ads = set(r['ad_id'] for r in inp)
new_rows = []
skipped_deleted = []
for p in sorted(pts_l, key=lambda x: (x['created_at'], x['id'])):
    if p['id'] in in_ads:
        continue
    l = li.get(p['line_item_id'])
    c = cp.get(l['campaign_id']) if l else None
    if p['deleted'] or (l and l['deleted']) or (c and c['deleted']):
        if p['created_at'] >= '2026-10-11':
            skipped_deleted.append(p['id'])
        continue
    t = tw.get(p['tweet_id'])
    base = {'platform': 'x', 'account_id': ACCOUNT_ID, 'account_name': ACCOUNT_NAME,
            'campaign_name': c['name'] if c else None, 'adset_name': l['name'] if l else None,
            'ad_id': p['id'], 'ad_name': (t or {}).get('name'), 'effective_status': status(p)}
    slots = []
    if t is not None:
        cu = t.get('card_uri') or ''
        if cu.startswith('card://'):
            card = cards.get(cu[7:])
            if card is None:
                slots.append(('card.destination.url (card_uri=%s)' % cu, None))
            else:
                slots.extend(card_dests(card))
        for i, u in enumerate((t.get('entities') or {}).get('urls') or []):
            ex = u.get('expanded_url')
            if ex and re.match(r'https?://(x|twitter)\.com/i/web/status/', ex):
                ex = None
            slots.append(('tweet.entities.urls[%d].expanded_url' % i, ex))
    if not slots:
        slots.append((None, None))
    for s, u in slots:
        row = dict(base)
        row['slot'] = s
        row['url'] = u
        new_rows.append(row)
new_keys = ['platform', 'account_id', 'account_name', 'campaign_name', 'adset_name', 'ad_id', 'ad_name',
            'effective_status', 'slot', 'url']
with open(NEWOUT, 'w', encoding='utf-8') as f:
    for o in new_rows:
        f.write(json.dumps({k: o.get(k) for k in new_keys}, ensure_ascii=False) + '\n')
print('rows', len(rows), 'new rows', len(new_rows), 'new ads', len(set(r['ad_id'] for r in new_rows)),
      'skipped deleted (created since 11-Oct)', skipped_deleted)
