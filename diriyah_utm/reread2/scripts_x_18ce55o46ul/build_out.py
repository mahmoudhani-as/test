import json, re, sys, datetime, collections
W = sys.argv[1]
OUT = sys.argv[2]
NEWOUT = sys.argv[3]
inp = json.load(open(W + '/../../reread/in/x_18ce55o46ul.json'))
pts_l = json.load(open(W + '/promoted_tweets.json'))
pts = {p['id']: p for p in pts_l}
li = {x['id']: x for x in json.load(open(W + '/line_items.json'))}
cp = {x['id']: x for x in json.load(open(W + '/campaigns.json'))}
tw = json.load(open(W + '/tweets.json'))
cards = json.load(open(W + '/cards.json'))
NOW = datetime.datetime.now(datetime.timezone.utc)
NS = 'ACTIVE_NOT_SERVABLE (campaign servable=false, e.g. ended flight/budget)'
UNREADABLE_CHECK = ('LIST_CARDS (card_ids and card_uris, include_legacy_cards=true, with_deleted=true) and '
                    'LIST_CARDS_ALL (card_uris) returned an empty data array on 12-Oct ~22:30 UTC')

def status(pt):
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
    for k, v in (('CAMPAIGN', c['entity_status']), ('LINE_ITEM', l['entity_status'])):
        if v != 'ACTIVE':
            return k + '_' + v
    if not c['servable']:
        return NS
    return 'ACTIVE'

def parse_time(s):
    return datetime.datetime.fromisoformat(s.replace('Z', '+00:00')) if s else None

def get_path(obj, path):
    # path like components[1].destination.url or slides[2][1].destination.url
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

rows = []
for r in inp:
    aid = r['ad_id']
    slot = r['slot']
    pt = pts.get(aid)
    o = {'platform': 'x', 'account_id': '18ce55o46ul', 'ad_id': aid, 'slot': slot}
    if pt is None:
        o.update(url=None, status_now='NOT_FOUND', creative_id_now=None, found=False,
                 note='promoted_tweet %s not returned by LIST_PROMOTED_TWEETS (with_deleted=true): ad no longer exists' % aid)
        rows.append(o); continue
    l = li[pt['line_item_id']]
    c = cp[l['campaign_id']]
    st = status(pt)
    tid = pt['tweet_id']
    o['creative_id_now'] = tid
    o['status_now'] = st
    base = 'promoted_tweet %s -> tweet %s (line_item %s, campaign %s); approval_status=%s' % (aid, tid, l['id'], c['id'], pt['approval_status'])
    notes = [base]
    if pt['deleted'] or c['deleted'] or l['deleted']:
        o.update(url=None, found=False)
        notes.append('ad is deleted (promoted_tweet deleted=%s, line_item deleted=%s, campaign deleted=%s)' % (pt['deleted'], l['deleted'], c['deleted']))
        o['note'] = '; '.join(notes); rows.append(o); continue
    if st == 'ACTIVE':
        et = parse_time(l.get('end_time'))
        if et and et < NOW:
            notes.append('NB: line item end_time %s has passed, so this ad is not delivering although campaign (servable=true), line item and ad are ACTIVE (status derived the same way as 11-Oct)' % l['end_time'])
    t = tw.get(tid)
    if t is None:
        o.update(url=None, found=False)
        notes.append('tweet %s not returned by LIST_TWEETS (tweet_type=PUBLISHED, timeline_type=ALL): post deleted' % tid)
        o['note'] = '; '.join(notes); rows.append(o); continue
    cu = t.get('card_uri')
    if slot is None:
        o['url'] = None
        o['found'] = True
        urls = t.get('entities', {}).get('urls') or []
        if cu or urls:
            notes.append('NB: tweet now has card_uri=%s, %d url entities (11-Oct: no URL slot)' % (cu, len(urls)))
        else:
            notes.append('no website card and no link in tweet text (no URL slot), same as 11-Oct')
        o['note'] = '; '.join(notes); rows.append(o); continue
    if slot.startswith('tweet.'):
        val, err = get_path(t, slot[len('tweet.'):])
        o['url'] = val
        o['found'] = True
        ent, _ = get_path(t, slot[len('tweet.'):].rsplit('.', 1)[0])
        tco = ent.get('url') if isinstance(ent, dict) else None
        notes.append('link in tweet text (t.co=%s)' % tco if tco else 'tweet text link')
        if cu:
            notes.append('tweet card_uri=%s' % cu)
        if err:
            notes.append('slot not found in tweet entities now: %s' % err)
        if r['url_11oct'] is None:
            # 11-Oct url was null (long-form post): keep null, report what the API returns now
            o['url'] = None
            if val and re.match(r'https?://(x|twitter)\.com/i/web/status/', val):
                notes.append("long-form post: API still returns only the truncated 'show more' link (%s); destination inside the full post not readable; url kept null as on 11-Oct" % val)
            else:
                notes.append('expanded_url now=%s; url kept null as on 11-Oct (11-Oct base_url=%s)' % (val, r.get('base_url_11oct')))
            o['note'] = '; '.join(notes); rows.append(o); continue
        if val and re.match(r'https?://(bit\.ly|x\.com/i/web/status)', val):
            if 'bit.ly' in val:
                notes.append('bit.ly short link; redirect target not resolved (read-only API pull)')
            else:
                notes.append('expanded_url is the truncated-tweet link (x.com/i/web/status), not a landing page')
        notes.append('URL unchanged vs 11-Oct' if val == r['url_11oct'] else 'URL CHANGED vs 11-Oct')
        o['note'] = '; '.join(notes); rows.append(o); continue
    if slot.startswith('card.'):
        o['found'] = True
        if not cu or not cu.startswith('card://'):
            o['url'] = None
            notes.append('tweet has no readable card now (card_uri=%s)' % cu)
            o['note'] = '; '.join(notes); rows.append(o); continue
        cid = cu[len('card://'):]
        notes.append('card_uri=%s' % cu)
        card = cards.get(cid)
        m = re.match(r'card\.destination\.url \(card_uri=(card://\d+)\)', slot)
        if card is None:
            o['url'] = None
            if m and m.group(1) != cu:
                notes.append('NB: slot card_uri %s differs from tweet card_uri' % m.group(1))
            if r['url_11oct'] is None:
                notes.append('card still not readable on re-read: ' + UNREADABLE_CHECK + ' - card is not owned by this ads account (boosted organic post); url kept null as on 11-Oct')
            else:
                notes.append('card not readable on re-read: ' + UNREADABLE_CHECK)
            o['note'] = '; '.join(notes); rows.append(o); continue
        notes.append('card_type=%s' % card.get('card_type'))
        notes.append('card deleted=%s' % json.dumps(card.get('deleted')))
        if m:
            # 11-Oct unreadable card now readable: report the first destination url
            dests = []
            for k in ('components',):
                for i, comp in enumerate(card.get(k) or []):
                    if isinstance(comp, dict) and comp.get('destination', {}).get('url'):
                        dests.append(('components[%d].destination.url' % i, comp['destination']['url']))
            for i, sl in enumerate(card.get('slides') or []):
                for j, comp in enumerate(sl):
                    if isinstance(comp, dict) and comp.get('destination', {}).get('url'):
                        dests.append(('slides[%d][%d].destination.url' % (i, j), comp['destination']['url']))
            o['url'] = dests[0][1] if dests else None
            notes.append('card readable now (was unreadable on 11-Oct); destinations: %s' % '; '.join('%s=%s' % d for d in dests))
            o['note'] = '; '.join(notes); rows.append(o); continue
        val, err = get_path(card, slot[len('card.'):])
        o['url'] = val
        if r['url_11oct'] is None:
            o['url'] = None
            notes.append('url was null on 11-Oct; card slot now reads %s; url kept null as on 11-Oct' % val)
            o['note'] = '; '.join(notes); rows.append(o); continue
        if err:
            notes.append('slot not found in card now: %s' % err)
        if card.get('deleted'):
            notes.append('NB: card is deleted')
        if val is not None:
            notes.append('URL unchanged vs 11-Oct' if val == r['url_11oct'] else 'URL CHANGED vs 11-Oct')
        o['note'] = '; '.join(notes); rows.append(o); continue
    o['url'] = None
    o['found'] = True
    notes.append('unrecognised slot format')
    o['note'] = '; '.join(notes); rows.append(o)

key_order = ['platform', 'account_id', 'ad_id', 'slot', 'url', 'status_now', 'creative_id_now', 'found', 'note']
with open(OUT, 'w', encoding='utf-8') as f:
    for o in rows:
        f.write(json.dumps({k: o.get(k) for k in key_order}, ensure_ascii=False) + '\n')

# Task 2: ads not in input, not deleted (ad, line item, campaign)
in_ads = set(r['ad_id'] for r in inp)
new = []
for p in pts_l:
    if p['id'] in in_ads:
        continue
    l = li.get(p['line_item_id']); c = cp.get(l['campaign_id']) if l else None
    if p['deleted'] or (l and l['deleted']) or (c and c['deleted']):
        continue
    new.append(p)
if new:
    # new ads need their tweets/cards read before they can be written in the Task 2 format
    print('NEW ADS FOUND (not written):', json.dumps(new))
    sys.exit(2)
open(NEWOUT, 'w', encoding='utf-8').close()
print('rows', len(rows), 'new', len(new))
