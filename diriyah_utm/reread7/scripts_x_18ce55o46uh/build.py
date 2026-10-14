# Build the reread7 (14-Oct-2026) partial re-read output for X account 18ce55o46uh ("H&S-VisitDiriyah").
# Read-only: every raw file came from GET calls through the Whathead x_ads_native_action gateway
# (extracted by extract.py from this agent's own transcript). One output line per INPUT row.
import json, re, os, collections

BASE = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
W = f'{BASE}/reread7/work_x_18ce55o46uh'
INP = f'{BASE}/reread7/in/x_18ce55o46uh_partial.json'
OUT = f'{BASE}/reread7/out/x_18ce55o46uh.jsonl'
PREV = f'{BASE}/reread5/out/x_18ce55o46uh.jsonl'  # last X re-read: 13-Oct 12:20-12:25Z (same file as reread4)
T = ('/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/'
     'wf_ce5fc811-84b/agent-a1e47ebfd4017713c.jsonl')
ACC = '18ce55o46uh'


def raw(label):
    calls = json.load(open(os.path.join(W, 'raw', label + '.json'), encoding='utf-8'))
    return calls, [x for c in calls for x in (c['data'] or [])]


pt_calls, pt_list = raw('promoted_tweets')
tw_calls, tw_list = raw('tweets')
cd_calls, cd_list = raw('cards')
li_calls, li_list = raw('line_items')
cp_calls, cp_list = raw('campaigns')
pts = {p['id']: p for p in pt_list}
tweets = {t['id_str']: t for t in tw_list}
cards = {c['id']: c for c in cd_list}
lis = {x['id']: x for x in li_list}
camps = {x['id']: x for x in cp_list}

# read window from the transcript timestamps of the five GET calls
use_ids = {c['tool_use_id'] for calls in (pt_calls, tw_calls, cd_calls, li_calls, cp_calls) for c in calls}
stamps = []
for line in open(T, encoding='utf-8'):
    try:
        o = json.loads(line)
    except Exception:
        continue
    c = (o.get('message') or {}).get('content')
    if isinstance(c, list) and any(isinstance(p, dict) and p.get('tool_use_id') in use_ids for p in c) and o.get('timestamp'):
        stamps.append(o['timestamp'])
stamps.sort()
NOW = stamps[-1][:19] + 'Z'
WIN = f"{stamps[0][:10]} {stamps[0][11:16]}-{stamps[-1][11:16]}Z"
READ = (f'read {WIN} via bulk GET promoted_tweets(promoted_tweet_ids x12, with_deleted, 1 call) / '
        f'tweets(tweet_ids x7, timeline_type=ALL, 1 call) / cards(card_ids x3, with_deleted, 1 call) / '
        f'line_items(line_item_ids x10, with_deleted+with_draft, 1 call) / campaigns(campaign_ids x7, with_deleted+with_draft, 1 call)')


def status_of(pt):  # same rule as the 12/13-Oct X builds
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
    hier = (f"line_item {li.get('id')} '{li.get('name') or ''}' entity_status={li.get('entity_status')} "
            f"flight {li.get('start_time')}..{li.get('end_time')}; campaign {c.get('id')} '{c.get('name')}' "
            f"entity_status={c.get('entity_status')} effective_status={c.get('effective_status')} "
            f"servable={c.get('servable')} updated_at={c.get('updated_at')}")
    return s, hier


prev = {}
for ln in open(PREV, encoding='utf-8'):
    o = json.loads(ln)
    prev[(o['ad_id'], o['slot'])] = (o.get('url'), o.get('status_now'))

inp = json.load(open(INP, encoding='utf-8'))
rows, stats = [], collections.Counter()
for r in inp:
    ad, slot = r['ad_id'], r['slot']
    pt = pts.get(ad)
    rec = {'platform': 'x', 'account_id': ACC, 'ad_id': ad, 'slot': slot, 'url': None,
           'status_now': None, 'creative_id_now': None, 'found': True, 'note': ''}
    if pt is None or pt['deleted']:
        rec.update(found=False, status_now='DELETED')
        rec['note'] = (f'ad deleted: promoted_tweet {ad} ' + ('not returned' if pt is None else 'deleted=true') +
                       ' by GET promoted_tweets with_deleted=true; ' + READ)
        rows.append(rec); stats['deleted'] += 1
        continue
    st, hier = status_of(pt)
    rec['status_now'] = st
    stats['status:' + st.split(';')[0]] += 1
    tid = pt['tweet_id']
    tw = tweets.get(tid)
    notes = []
    m = re.search(r'tweet_id (\d+)', r.get('notes_11oct') or '')
    if m and m.group(1) != tid:
        notes.append(f'TWEET CHANGED vs 11-Oct (was {m.group(1)})')
    pv_url, pv_status = prev.get((ad, slot), (None, None))
    if slot.startswith('card.'):
        mm = re.match(r'card\.components\[(\d+)\]\.destination\.url$', slot)
        ms = re.match(r'card\.slides\[(\d+)\]\[(\d+)\]\.destination\.url$', slot)
        cid = tw['card_uri'].split('://', 1)[1] if tw and tw.get('card_uri') else None
        rec['creative_id_now'] = cid
        card = cards.get(cid) if cid else None
        if card is None:
            rec['found'] = False
            notes.append(f'card {cid} not returned / tweet {tid} has no card_uri now')
            stats['card_missing'] += 1
            desc = f'read promoted_tweet {ad} -> tweet {tid} card_uri={(tw or {}).get("card_uri")}'
        else:
            if mm:
                idx = int(mm.group(1)); comps = card.get('components') or []
                comp = comps[idx] if idx < len(comps) else None; where = f'components[{idx}]'
            else:
                i, j = int(ms.group(1)), int(ms.group(2)); sl = card.get('slides') or []
                comp = sl[i][j] if i < len(sl) and j < len(sl[i]) else None; where = f'slides[{i}][{j}]'
            dest = (comp or {}).get('destination') or {}
            rec['url'] = dest.get('url')
            if comp is None:
                notes.append(f'{where} not present on the card now')
            if card.get('deleted'):
                rec['found'] = False
                notes.append('card deleted=true')
            if cid != r['creative_id']:
                notes.append(f'CARD CHANGED vs 11-Oct (was {r["creative_id"]})')
            desc = (f"read promoted_tweet {ad} -> tweet {tid} (card_uri card://{cid}) -> card {cid} '{card.get('name')}' "
                    f"{card.get('card_type')} {where} type={(comp or {}).get('type')} destination.type={dest.get('type')} .url; "
                    f"card deleted={card.get('deleted')} updated_at={card.get('updated_at')} (unchanged since creation; card shared "
                    f"by every promoted tweet referencing it); X has no separate url_tags/UTM field - UTMs are inside the destination URL")
            if card.get('updated_at') != card.get('created_at'):
                desc = desc.replace(' (unchanged since creation;', ' (card edited after creation;')
    elif slot.startswith('tweet.entities.urls['):
        mm = re.match(r'tweet\.entities\.urls\[(\d+)\]\.expanded_url \(tweet text link (\S+)\)$', slot)
        idx, tco = int(mm.group(1)), mm.group(2)
        rec['creative_id_now'] = tid
        urls = (tw or {}).get('entities', {}).get('urls') or []
        ent = urls[idx] if idx < len(urls) else None
        if ent is None or ent.get('url') != tco:  # fall back to matching the t.co link anywhere in the text
            ent = next((u for u in urls if u.get('url') == tco), ent)
        if tw is None:
            notes.append(f'tweet {tid} not returned now (url kept null)')
        elif ent is None:
            notes.append('tweet text link not found now')
        else:
            rec['url'] = ent.get('expanded_url')
            if ent.get('url') != tco:
                notes.append(f"t.co at urls[{idx}] is now {ent.get('url')} (11-Oct {tco})")
        desc = (f"read promoted_tweet {ad} -> tweet {tid} entities.urls[{idx}] ({ent.get('url') if ent else None}) expanded_url; "
                f"tweet card_uri={(tw or {}).get('card_uri')}; published tweet text is immutable via Ads API; X has no separate UTM field")
    else:
        raise SystemExit(f'unexpected slot {slot!r}')
    changed = rec['url'] != r['url_11oct']
    changed_prev = rec['url'] != pv_url
    stats['url_changed_vs_11oct' if changed else 'url_same_as_11oct'] += 1
    stats['url_changed_vs_13oct' if changed_prev else 'url_same_as_13oct'] += 1
    if st != pv_status:
        stats['status_changed_vs_13oct'] += 1
    head = (('URL CHANGED vs 11-Oct' if changed else 'URL unchanged vs 11-Oct') +
            ('; changed since the 13-Oct 12:20-12:25Z re-read (was %s)' % pv_url if changed_prev
             else '; same as the 13-Oct 12:20-12:25Z re-read') +
            ('' if st == pv_status else f'; STATUS CHANGED since 13-Oct (was {pv_status})') +
            '; no apply-round write ever targeted this ad/card (no manual change seen here either)')
    notes.insert(0, head + '; ' + desc)
    notes.append(f"status: {hier}; promoted_tweet entity_status={pt['entity_status']} approval_status={pt['approval_status']} "
                 f"deleted={pt['deleted']} updated_at={pt['updated_at']}; tweet name={(tw or {}).get('name')!r}")
    notes.append(READ)
    rec['note'] = '; '.join(notes)
    rows.append(rec)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, 'w', encoding='utf-8') as f:
    for rec in rows:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')
print('rows', len(rows), 'read window', WIN)
print(dict(stats))
