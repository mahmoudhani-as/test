import json, re, sys, datetime

# usage: python3 -I build_out.py <work_dir> <input.json> <out.jsonl> <prev_13oct.jsonl>
W, IN, OUT, PREV = sys.argv[1:5]
ACCOUNT_ID = '18ce55o46ul'

inp = json.load(open(IN, encoding='utf-8'))
pts = {p['id']: p for p in json.load(open(W + '/promoted_tweets.json', encoding='utf-8'))}
li = {x['id']: x for x in json.load(open(W + '/line_items.json', encoding='utf-8'))}
cp = {x['id']: x for x in json.load(open(W + '/campaigns.json', encoding='utf-8'))}
tw = json.load(open(W + '/tweets.json', encoding='utf-8'))
cards = json.load(open(W + '/cards.json', encoding='utf-8'))
prev = {}
for line in open(PREV, encoding='utf-8'):
    if line.strip():
        o = json.loads(line)
        prev[(o['ad_id'], o['slot'])] = o
NOW = datetime.datetime.now(datetime.timezone.utc)
READ_AT = NOW.strftime('%d-%b-%Y %H:%M UTC')
NS = 'ACTIVE_NOT_SERVABLE (campaign servable=false, e.g. ended flight/budget)'


def status(pt):
    """Same derivation as the 11-Oct pull (and the 13-Oct re-read)."""
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


def ctx(pt):
    l = li[pt['line_item_id']]
    c = cp[l['campaign_id']]
    reasons = ','.join(c.get('reasons_not_servable') or []) or '-'
    return ('promoted_tweet %s -> tweet %s (line_item %s entity_status=%s, campaign %s entity_status=%s '
            'effective_status=%s servable=%s reasons_not_servable=%s); approval_status=%s' % (
                pt['id'], pt['tweet_id'], l['id'], l['entity_status'], c['id'], c['entity_status'],
                c.get('effective_status'), c.get('servable'), reasons, pt['approval_status']))


def vs13(o, aid, slot):
    p = prev.get((aid, slot))
    if p is None:
        return 'no 13-Oct re-read row for this ad/slot'
    diffs = []
    if p.get('url') != o.get('url'):
        diffs.append('URL changed (13-Oct: %s)' % p.get('url'))
    if p.get('status_now') != o.get('status_now'):
        diffs.append('status changed (13-Oct: %s)' % p.get('status_now'))
    if str(p.get('creative_id_now')) != str(o.get('creative_id_now')):
        diffs.append('tweet id changed (13-Oct: %s)' % p.get('creative_id_now'))
    return ('vs 13-Oct 12:33 UTC re-read: ' + '; '.join(diffs)) if diffs else 'no change vs 13-Oct 12:33 UTC re-read'


rows = []
for r in inp:
    aid = r['ad_id']
    slot = r['slot']
    o = {'platform': 'x', 'account_id': ACCOUNT_ID, 'ad_id': aid, 'slot': slot}
    pt = pts.get(aid)
    if pt is None:
        o.update(url=None, status_now='NOT_FOUND', creative_id_now=None, found=False,
                 note='read %s; promoted_tweet %s not returned by LIST_PROMOTED_TWEETS (promoted_tweet_ids, '
                      'with_deleted=true): ad no longer exists' % (READ_AT, aid))
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
        notes.append('STATUS CHANGED vs 11-Oct (%s -> %s; campaign updated_at %s, line_item updated_at %s)' % (
            r['status_11oct'], st, c.get('updated_at'), l.get('updated_at')))
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
    if slot.startswith('tweet.'):
        o['found'] = True
        val, err = get_path(t, slot[len('tweet.'):])
        ent, _ = get_path(t, slot[len('tweet.'):].rsplit('.', 1)[0])
        tco = ent.get('url') if isinstance(ent, dict) else None
        notes.append('boosted organic post (nullcast=%s); link in tweet text (t.co=%s)' % (
            str(t.get('nullcast')).lower(), tco))
        if cu:
            notes.append('tweet card_uri=%s%s' % (cu, ' (website card deleted, no card destination)' if cu.startswith('tombstone') else ''))
        if err:
            notes.append('slot not found in tweet entities now: %s' % err)
        if r['url_11oct'] is None:
            o['url'] = None
            notes.append('expanded_url now=%s; url kept null as on 11-Oct' % val)
        else:
            o['url'] = val
            if val and 'bit.ly' in val:
                notes.append('bit.ly short link; redirect target not resolved (read-only API pull)')
            if val is not None:
                notes.append('URL unchanged vs 11-Oct' if val == r['url_11oct'] else 'URL CHANGED vs 11-Oct (was %s)' % r['url_11oct'])
    elif slot.startswith('card.'):
        o['found'] = True
        if not cu or not cu.startswith('card://'):
            o['url'] = None
            notes.append('tweet has no readable card now (card_uri=%s)' % cu)
        else:
            cid = cu[len('card://'):]
            notes.append('card_uri=%s' % cu)
            m = re.search(r'card_uri=(card://\d+)', r.get('notes_11oct') or '')
            if m and m.group(1) != cu:
                notes.append('NB: tweet card_uri changed vs 11-Oct (%s)' % m.group(1))
            card = cards.get(cid)
            if card is None:
                o['url'] = None
                notes.append('card %s not returned by LIST_CARDS (card_ids, include_legacy_cards=true, with_deleted=true)' % cid)
            else:
                notes.append('card_type=%s; card updated_at %s' % (card.get('card_type'), card.get('updated_at')))
                if card.get('deleted'):
                    notes.append('NB: card is deleted')
                val, err = get_path(card, slot[len('card.'):])
                if r['url_11oct'] is None:
                    o['url'] = None
                    notes.append('url was null on 11-Oct; card slot now reads %s; url kept null as on 11-Oct' % val)
                else:
                    o['url'] = val
                    if err:
                        notes.append('slot not found in card now: %s' % err)
                    if val is not None:
                        notes.append('URL unchanged vs 11-Oct' if val == r['url_11oct'] else 'URL CHANGED vs 11-Oct (was %s)' % r['url_11oct'])
    else:
        o['url'] = None
        o['found'] = True
        notes.append('unrecognised slot format')
    notes.append(vs13(o, aid, slot))
    o['note'] = '; '.join(notes)
    rows.append(o)

key_order = ['platform', 'account_id', 'ad_id', 'slot', 'url', 'status_now', 'creative_id_now', 'found', 'note']
with open(OUT, 'w', encoding='utf-8') as f:
    for o in rows:
        f.write(json.dumps({k: o.get(k) for k in key_order}, ensure_ascii=False) + '\n')
print('rows written', len(rows))
