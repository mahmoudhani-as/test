# Build reread3 output for X account 18ce55o46uh from the bulk reads saved in this folder (13-Oct-2026 ~09:58-10:02 UTC).
import json, re, os, collections, glob

W = os.path.dirname(os.path.abspath(__file__))
BASE = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
INP = f'{BASE}/reread/in/x_18ce55o46uh.json'
OUT = f'{BASE}/reread3/out/x_18ce55o46uh.jsonl'
NEW = f'{BASE}/reread3/out/new_x_18ce55o46uh.jsonl'
ACC = '18ce55o46uh'
ACC_NAME = 'H&S-VisitDiriyah'
NOW = '2026-10-13T10:00:00Z'
READ = ('read 2026-10-13 ~09:58-10:02Z via bulk GET promoted_tweets(with_deleted, 5 pages, 411 total) / '
        'line_items(line_item_ids; draft vzc9n by id) / campaigns(campaign_ids; draft o4w3m by id) / '
        'tweets(tweet_ids, 2 calls) / cards(card_ids, 5 calls)')


def L(name):
    return json.load(open(os.path.join(W, name)))


inp = json.load(open(INP))
pts = {p['id']: p for p in L('promoted_tweets.json')}
lis = L('line_items_by_id.json')
camps = L('campaigns.json')
tweets = L('tweets.json')
cards = L('cards.json')
UNREADABLE = {'1826872445891948916', '1839354381835370531', '1839354560529543565', '1839354776414499233',
              '1839354947194015853', '1839355112525066254', '1839355280859242662'}


def status_of(pt):
    li = lis.get(pt['line_item_id']) or {}
    c = camps.get(li.get('campaign_id')) or {}
    reasons = c.get('reasons_not_servable') or []
    serving = (not pt['deleted'] and pt['entity_status'] == 'ACTIVE' and pt['approval_status'] == 'ACCEPTED'
               and li.get('entity_status') == 'ACTIVE' and not li.get('deleted') and c.get('servable') is True
               and (not li.get('end_time') or li['end_time'] > NOW))
    head = 'DELETED' if pt['deleted'] else ('SERVING' if serving else 'NOT_SERVING')
    s = (f"{head}; approval={pt['approval_status']}; ad={pt['entity_status']}; "
         f"line_item={li.get('entity_status')}; campaign={c.get('effective_status') or c.get('entity_status')}")
    if reasons:
        s += '; not_servable=' + ','.join(reasons)
    hier = (f"line_item {li.get('id')} '{li.get('name')}' entity_status={li.get('entity_status')} "
            f"flight {li.get('start_time')}..{li.get('end_time')}; campaign {c.get('id')} '{c.get('name')}' "
            f"entity_status={c.get('entity_status')} effective_status={c.get('effective_status')} "
            f"servable={c.get('servable')}")
    return s, hier


# local apply-round records (context only): (ad_id, slot) -> [(file, after_expected, after_live, result)]
applied = {}
for fpath in sorted(set(glob.glob(f'{BASE}/apply*/out_x_*.jsonl') + glob.glob(f'{BASE}/apply*/**/out_x*.jsonl', recursive=True))):
    for ln in open(fpath):
        try:
            o = json.loads(ln)
        except Exception:
            continue
        if str(o.get('account_id')) != ACC:
            continue
        for a in o.get('ad_ids') or []:
            applied.setdefault((a, o.get('slot')), []).append(
                (os.path.relpath(fpath, BASE), o.get('after_expected'), o.get('after_live'), o.get('result')))

# 12-Oct night re-read (reread2) for "changed since" context
prev = {}
for ln in open(f'{BASE}/reread2/out/x_18ce55o46uh.jsonl'):
    o = json.loads(ln)
    prev[(o['ad_id'], o['slot'])] = o.get('url')


def apply_ctx(ad, slot, url):
    e = applied.get((ad, slot))
    if not e:
        return None
    hit = [x for x in e if url is not None and url == x[1]]
    if hit:
        return f'current URL equals the target of local apply record {hit[-1][0]} (result={hit[-1][3]})'
    return ('current URL is NOT the target of the local apply record(s) (' +
            ','.join(f'{x[0]} result={x[3]}' + (' - still the pre-write value it recorded' if url is not None and url == x[2] else '') for x in e) + ')')


rows = []
stats = collections.Counter()
for r in inp:
    ad = r['ad_id']
    slot = r['slot']
    pt = pts.get(ad)
    rec = {'platform': 'x', 'account_id': ACC, 'ad_id': ad, 'slot': slot, 'url': None,
           'status_now': None, 'creative_id_now': None, 'found': True, 'note': ''}
    if pt is None or pt['deleted']:
        rec['found'] = False
        rec['status_now'] = 'DELETED'
        rec['note'] = (f'ad deleted: promoted_tweet {ad} ' + ('not returned' if pt is None else 'deleted=true') +
                       ' in GET promoted_tweets with_deleted=true; ' + READ)
        rows.append(rec); stats['deleted'] += 1
        continue
    st, hier = status_of(pt)
    rec['status_now'] = st
    tid = pt['tweet_id']
    tw = tweets.get(tid)
    notes = []
    m = re.search(r'tweet_id (\d+)', r.get('notes_11oct') or '')
    if m and m.group(1) != tid:
        notes.append(f'TWEET CHANGED vs 11-Oct (was {m.group(1)})')
    if slot and slot.startswith('card.'):
        mm = re.match(r'card\.components\[(\d+)\]\.destination\.url$', slot)
        ms = re.match(r'card\.slides\[(\d+)\]\[(\d+)\]\.destination\.url$', slot)
        cid = tw['card_uri'].split('://', 1)[1] if tw and tw.get('card_uri') else None
        rec['creative_id_now'] = cid
        card = cards.get(cid) if cid else None
        if card is None:
            rec['found'] = False
            notes.append(f'card {cid} not readable / tweet has no card now')
            stats['card_missing'] += 1
        else:
            if mm:
                idx = int(mm.group(1))
                comps = card.get('components') or []
                comp = comps[idx] if idx < len(comps) else None
                where = f'components[{idx}]'
            else:
                i, j = int(ms.group(1)), int(ms.group(2))
                sl = card.get('slides') or []
                comp = sl[i][j] if i < len(sl) and j < len(sl[i]) else None
                where = f'slides[{i}][{j}]'
            dest = (comp or {}).get('destination') or {}
            rec['url'] = dest.get('url')
            if card.get('deleted'):
                rec['found'] = False
                notes.append('card deleted')
            if cid != r['creative_id']:
                notes.append(f'CARD CHANGED vs 11-Oct (was {r["creative_id"]})')
            changed = rec['url'] != r['url_11oct']
            changed12 = rec['url'] != prev.get((ad, slot))
            stats['card_changed_vs_11oct' if changed else 'card_same_as_11oct'] += 1
            stats['card_changed_vs_12oct_night' if changed12 else 'card_same_as_12oct_night'] += 1
            ctx = apply_ctx(ad, slot, rec['url'])
            if ctx:
                notes.insert(0, ctx)
            notes.insert(0, ('URL CHANGED vs 11-Oct' if changed else 'URL unchanged vs 11-Oct') +
                         ('; changed since the 12-Oct ~22:25Z re-read' if changed12 else '; same as the 12-Oct ~22:25Z re-read') +
                         f"; read promoted_tweet {ad} -> tweet {tid} (card_uri card://{cid}) -> card {cid} "
                         f"'{card.get('name')}' {card.get('card_type')} {where} type={(comp or {}).get('type')} "
                         f"destination.type={dest.get('type')} .url; card deleted={card.get('deleted')} "
                         f"(card shared by every promoted tweet referencing it); "
                         f"X has no separate url_tags/UTM field - UTMs are inside the destination URL")
    elif slot and slot.startswith('tweet.entities.urls['):
        mm = re.match(r'tweet\.entities\.urls\[(\d+)\]\.expanded_url \(tweet text link (\S+)\)$', slot)
        idx, tco = int(mm.group(1)), mm.group(2)
        rec['creative_id_now'] = tid
        urls = (tw or {}).get('entities', {}).get('urls') or []
        ent = urls[idx] if idx < len(urls) else None
        if tw is None:
            notes.append(f'tweet {tid} not returned now')
        elif ent is None:
            notes.append('tweet text link not found now')
        else:
            rec['url'] = ent.get('expanded_url')
            if ent.get('url') != tco:
                notes.append(f"t.co at urls[{idx}] is now {ent.get('url')} (11-Oct {tco})")
        changed = rec['url'] != r['url_11oct']
        stats['text_changed' if changed else 'text_same'] += 1
        ctx = apply_ctx(ad, slot, rec['url'])
        if ctx:
            notes.insert(0, ctx)
        notes.insert(0, ('URL CHANGED vs 11-Oct' if changed else 'URL unchanged vs 11-Oct') +
                     f"; read promoted_tweet {ad} -> tweet {tid} entities.urls[{idx}] ({ent.get('url') if ent else None}) "
                     f"expanded_url; tweet card_uri={(tw or {}).get('card_uri')}; "
                     f"published tweet text is immutable via Ads API; X has no separate UTM field")
    else:
        rec['creative_id_now'] = tid
        if tid in UNREADABLE or tw is None:
            stats['null_unreadable'] += 1
            notes.append(f"url kept null as on 11-Oct: tweet {tid} still not returned by GET accounts/{ACC}/tweets "
                         f"(tweet_type=PUBLISHED, timeline_type=ALL, tweet_ids=...) and GET tweet_previews returns empty data[] "
                         f"(re-checked 13-Oct); the promoted_tweet itself still exists (deleted=false)")
        else:
            urls = tw.get('entities', {}).get('urls') or []
            stats['null_mediaonly'] += 1
            notes.append(f"url null as on 11-Oct: tweet {tid} still has no card_uri ({tw.get('card_uri')}) and "
                         f"{len(urls)} URLs in text (media-only promoted tweet, no landing page slot)")
    tname = (tw or {}).get('name')
    notes.append(f"status: {hier}; promoted_tweet entity_status={pt['entity_status']} approval_status={pt['approval_status']} "
                 f"deleted={pt['deleted']} updated_at={pt['updated_at']}; tweet name={tname!r}")
    notes.append(READ)
    rec['note'] = '; '.join(notes)
    rows.append(rec)

with open(OUT, 'w') as f:
    for rec in rows:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')

# Task 2: ads not in input (live = not deleted)
in_ids = {r['ad_id'] for r in inp}
new = [p for p in pts.values() if not p['deleted'] and p['id'] not in in_ids]
# all 411 promoted tweets (incl. deleted) were listed; the 63 scheduled promoted tweets (with_deleted) are all deleted, newest created 2026-01-02
assert not new, new
open(NEW, 'w').close()
print('rows', len(rows), dict(stats), 'new', len(new))
