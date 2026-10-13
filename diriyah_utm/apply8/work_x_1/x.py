# apply8 in_x_1 helper: parses this agent's own Whathead results from its transcript (read-only),
# checks slots, prepares the expected card body, and verifies dry-run / live / read-back.
# It never calls any API and never writes outside work_x_1/.
import json, sys, copy, re, os
from urllib.parse import urlsplit, parse_qsl

W = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply8/work_x_1'
IN = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply8/in_x_1.json'
EXCL = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/work/excl_platform_refused_v2.json'
T = '/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/wf_3e34ff06-5fe/agent-a4230d329096e7368.jsonl'
TOOL = 'mcp__Whathed_MCP__x_ads_native_action'
ACCT = '18ce55o46uh'


def load_tr():
    calls, results, order = {}, {}, []
    for line in open(T, encoding='utf-8'):
        try:
            e = json.loads(line)
        except Exception:
            continue
        msg = e.get('message') or {}
        content = msg.get('content')
        if not isinstance(content, list):
            continue
        for c in content:
            if not isinstance(c, dict):
                continue
            if c.get('type') == 'tool_use':
                if c['id'] not in calls:
                    order.append(c['id'])
                calls[c['id']] = (c.get('name'), c.get('input'))
            elif c.get('type') == 'tool_result':
                rc = c.get('content')
                if isinstance(rc, list):
                    txt = ''.join(x.get('text', '') for x in rc if isinstance(x, dict) and x.get('type') == 'text')
                elif isinstance(rc, str):
                    txt = rc
                else:
                    txt = json.dumps(rc)
                results[c['tool_use_id']] = txt
    return calls, results, order


def parse_result(txt):
    try:
        return json.loads(txt)
    except Exception:
        m = re.search(r'(/[^\s"\']+\.(?:json|txt))', txt)
        if m and os.path.exists(m.group(1)):
            raw = open(m.group(1), encoding='utf-8').read()
            d = json.loads(raw)
            if isinstance(d, list) and d and isinstance(d[0], dict) and 'text' in d[0]:
                return json.loads(''.join(x.get('text', '') for x in d))
            return d
        raise ValueError('cannot parse result: ' + txt[:300])


def x_calls(action=None, card_id=None, dry=None, after=None):
    calls, results, order = load_tr()
    out = []
    start = order.index(after) + 1 if after else 0
    for i in order[start:]:
        nm, inp = calls[i]
        if nm != TOOL or not isinstance(inp, dict):
            continue
        if action and inp.get('action') != action:
            continue
        pp = inp.get('path_params') or {}
        if card_id is not None and str(pp.get('card_id')) != str(card_id):
            continue
        if dry is not None:
            d = inp.get('dry_run')
            isdry = (d is None) or bool(d)  # writes default to dry-run
            if isdry != dry:
                continue
        out.append((i, inp, results.get(i)))
    return out


def units():
    return json.load(open(IN, encoding='utf-8'))


def eq(a, b):
    A, B = urlsplit(a), urlsplit(b)
    return (A.scheme, A.netloc, A.path, A.fragment) == (B.scheme, B.netloc, B.path, B.fragment) and \
        sorted(parse_qsl(A.query, keep_blank_values=True)) == sorted(parse_qsl(B.query, keep_blank_values=True))


def slot_get(card, slot):
    m = re.fullmatch(r'card\.components\[(\d+)\]\.destination\.url', slot)
    if m:
        return card['components'][int(m.group(1))]['destination']['url']
    m = re.fullmatch(r'card\.slides\[(\d+)\]\[(\d+)\]\.destination\.url', slot)
    if m:
        return card['slides'][int(m.group(1))][int(m.group(2))]['destination']['url']
    raise ValueError(slot)


def slot_set(obj, slot, val):
    m = re.fullmatch(r'card\.components\[(\d+)\]\.destination\.url', slot)
    if m:
        obj['components'][int(m.group(1))]['destination']['url'] = val
        return
    m = re.fullmatch(r'card\.slides\[(\d+)\]\[(\d+)\]\.destination\.url', slot)
    if m:
        obj['slides'][int(m.group(1))][int(m.group(2))]['destination']['url'] = val
        return
    raise ValueError(slot)


READONLY_COMP = {'media_metadata'}


def strip(comp):
    return {k: v for k, v in comp.items() if k not in READONLY_COMP}


def build_payload(card, changes):
    p = {'name': card['name']}
    if card.get('components') is not None:
        p['components'] = [strip(copy.deepcopy(c)) for c in card['components']]
    if card.get('slides') is not None:
        p['slides'] = [[strip(copy.deepcopy(c)) for c in s] for s in card['slides']]
    if 'experiment_signals' in card:
        p['experiment_signals'] = copy.deepcopy(card['experiment_signals'])
    for ch in changes:
        slot_set(p, ch['slot'], ch['new'])
    return p


def comparable(card):
    c = copy.deepcopy(card)
    c.pop('updated_at', None)

    def blank(comp):
        if isinstance(comp, dict) and isinstance(comp.get('destination'), dict) and 'url' in comp['destination']:
            comp['destination']['url'] = '<URL>'
    for comp in c.get('components') or []:
        blank(comp)
    for s in c.get('slides') or []:
        for comp in s:
            blank(comp)
    return c


def card_of(res_txt):
    d = parse_result(res_txt)
    if not (isinstance(d, dict) and d.get('success') is True):
        raise RuntimeError('GET failed: ' + res_txt[:600])
    inner = d['data']
    card = inner['data']['data'] if isinstance(inner.get('data'), dict) and 'data' in inner['data'] else inner['data']
    return card, d.get('meta', {}).get('requestId')


def excluded(u, ch):
    for e in json.load(open(EXCL, encoding='utf-8')):
        if str(e.get('platform', '')).lower() in ('x', 'twitter'):
            ids = {e.get('ad_id'), e.get('unit'), e.get('card_id')}
            if (set(u['ad_ids']) | {u['unit']}) & ids and e.get('slot') in (None, ch['slot']):
                return True
    return False


cmd = sys.argv[1]

if cmd == 'share':
    calls, results, order = load_tr()
    pts, tws = None, None
    for i in order:
        nm, inp = calls[i]
        if nm != TOOL or not isinstance(inp, dict) or i not in results:
            continue
        if inp.get('action') == 'LIST_PROMOTED_TWEETS' and 'id' in (inp.get('result_fields') or []):
            pts = (i, parse_result(results[i]))
        if inp.get('action') == 'LIST_TWEETS':
            tws = (i, parse_result(results[i]))
    ptl = pts[1]['data']['data']['data']
    twl = tws[1]['data']['data']['data']
    asked = (tws[1]['data']['data']['request']['params']['tweet_ids'])
    got = [t['id_str'] for t in twl]
    print('promoted tweets listed:', len(ptl), 'newest:', ptl[0]['created_at'], ptl[0]['id'], '| oldest in page:', ptl[-1]['created_at'])
    print('tweets asked:', len(asked), 'returned:', len(got), 'missing:', sorted(set(asked) - set(got)))
    card_tweets = {}
    for t in twl:
        cu = t.get('card_uri') or ''
        card_tweets.setdefault(cu.replace('card://', ''), []).append(t['id_str'])
    links = [t['id_str'] for t in twl if re.search(r'https?://|t\.co/', t.get('full_text') or '')]
    out = {}
    allok = True
    mincard = min(int(u['unit']) for u in units())
    # every promoted tweet whose tweet id is newer than the oldest card must be among the tweets read
    newer = sorted({p['tweet_id'] for p in ptl if int(p['tweet_id']) > mincard})
    print('promoted tweets\' tweets newer than oldest card:', len(newer), 'all read:', set(newer) <= set(got))
    for u in units():
        cid = u['unit']
        tw = card_tweets.get(cid, [])
        prom = [(p['id'], p['deleted'], p['tweet_id']) for p in ptl if p['tweet_id'] in tw]
        others = [p for p in prom if p[0] not in u['ad_ids']]
        ok = bool(tw) and not others and {p[0] for p in prom} == set(u['ad_ids'])
        allok &= ok
        out[cid] = {'tweets': tw, 'promoted': prom, 'others': others, 'ok': ok, 'text_links': [t for t in tw if t in links]}
        print(cid, 'tweets', tw, 'promoted', prom, 'others', others, 'OK' if ok else 'CHECK', 'links' if out[cid]['text_links'] else '')
    json.dump({'promoted_tool': pts[0], 'tweets_tool': tws[0], 'cards': out}, open(f'{W}/share_check.json', 'w'), ensure_ascii=False, indent=1)
    print('ALL OK' if allok else 'NOT ALL OK')

elif cmd == 'pre':
    # pre <idx>: uses the latest GET_CARD for the unit's card
    idx = int(sys.argv[2])
    u = units()[idx]
    cid = u['unit']
    lst = [c for c in x_calls('GET_CARD', cid) if c[2] is not None]
    tid, inp, res = lst[-1]
    card, req = card_of(res)
    assert str(card['id']) == str(cid), (card['id'], cid)
    print('unit', idx, 'card', card['id'], card.get('card_type'), '| deleted', card.get('deleted'), '| name', json.dumps(card.get('name'), ensure_ascii=False),
          '| keys', sorted(card.keys()), '| experiment_signals' if 'experiment_signals' in card else '| no experiment_signals', '| GET req', req)
    status, towrite = {}, []
    for ch in u['changes']:
        cur = slot_get(card, ch['slot'])
        if excluded(u, ch):
            st = 'EXCLUDED'
        elif cur == ch['new'] or eq(cur, ch['new']):
            st = 'AlreadyFixed'
        elif cur == ch['now'] or cur in ch['alt_now'] or eq(cur, ch['now']) or any(eq(cur, a) for a in ch['alt_now']):
            st = 'WRITE'
            towrite.append(ch)
        else:
            st = 'Skipped'
        status[ch['slot']] = {'cur': cur, 'st': st, 'cur_eq_now_exact': cur == ch['now'], 'cur_eq_new_exact': cur == ch['new']}
        print(' ', ch['slot'], st, '| cur==now exact:', cur == ch['now'], '| cur==new exact:', cur == ch['new'])
        print('   cur:', cur)
    if card.get('deleted'):
        print('  CARD DELETED')
    json.dump({'card_before': card, 'status': status, 'get_tool': tid, 'get_req': req}, open(f'{W}/pre_{idx}.json', 'w'), ensure_ascii=False)
    if towrite and not card.get('deleted'):
        p = build_payload(card, towrite)
        json.dump(p, open(f'{W}/payload_{idx}.json', 'w'), ensure_ascii=False)
        print('PAYLOAD_ASCII', json.dumps(p, ensure_ascii=True))
        nonascii = sorted({ch for ch in json.dumps(p, ensure_ascii=False) if ord(ch) > 127 and not ('؀' <= ch <= 'ۿ')})
        print('non-Arabic non-ASCII chars in payload:', [hex(ord(c)) for c in nonascii])

elif cmd == 'dry':
    idx = int(sys.argv[2])
    u = units()[idx]
    cid = u['unit']
    lst = [c for c in x_calls('UPDATE_CARD', cid, dry=True) if c[2] is not None]
    tid, inp, res = lst[-1]
    exp = json.load(open(f'{W}/payload_{idx}.json', encoding='utf-8'))
    sent = inp['payload'] if isinstance(inp['payload'], dict) else json.loads(inp['payload'])
    pp = inp.get('path_params') or {}
    print('dry tool', tid, '| dry_run flag:', inp.get('dry_run'), '| path_params:', pp)
    print('sent == expected:', sent == exp)
    if sent != exp:
        print('  SENT    ', json.dumps(sent, ensure_ascii=True)[:3000])
        print('  EXPECTED', json.dumps(exp, ensure_ascii=True)[:3000])
    d = parse_result(res)
    try:
        echo = d['data']['request']['payload']
        print('gateway dry_run:', d['data'].get('dry_run'), '| echoed body == expected:', echo == exp, '| echoed card_id:', d['data']['request'].get('card_id'))
    except Exception as ex:
        print('no echo parsed:', ex)
    print('raw result (first 600):', res[:600].replace('\n', ' '))
    pre = json.load(open(f'{W}/pre_{idx}.json', encoding='utf-8'))
    before = pre['card_before']
    # what would change vs the card as read (only URL expected)
    b2 = build_payload(before, [])
    diffs = []
    for k in set(b2) | set(sent):
        if b2.get(k) != sent.get(k):
            diffs.append(k)
    after_cmp = copy.deepcopy(before)
    for ch in u['changes']:
        if pre['status'][ch['slot']]['st'] == 'WRITE':
            slot_set(after_cmp, ch['slot'], ch['new'])
    print('top-level keys that differ from card-as-read:', diffs)
    print('payload equals card-as-read except the listed URL(s):', build_payload(after_cmp, []) == sent)
    print('account/card in path:', pp.get('account_id') == ACCT, str(pp.get('card_id')) == str(cid))

elif cmd == 'verify':
    # verify <idx>: finds the latest live UPDATE_CARD for the card and the GET_CARD after it
    idx = int(sys.argv[2])
    u = units()[idx]
    cid = u['unit']
    lives = [c for c in x_calls('UPDATE_CARD', cid, dry=False) if c[2] is not None]
    wtid, winp, wres = lives[-1]
    exp = json.load(open(f'{W}/payload_{idx}.json', encoding='utf-8'))
    sent = winp['payload'] if isinstance(winp['payload'], dict) else json.loads(winp['payload'])
    print('live tool', wtid, '| dry_run:', winp.get('dry_run'), '| idem:', winp.get('idempotency_key'), '| sent == expected:', sent == exp)
    print('live raw result (first 1200):', wres[:1200].replace('\n', ' '))
    gets = [c for c in x_calls('GET_CARD', cid, after=wtid) if c[2] is not None]
    assert gets, 'no read-back GET_CARD after the live write'
    gtid, ginp, gres = gets[-1]
    after, req = card_of(gres)
    pre = json.load(open(f'{W}/pre_{idx}.json', encoding='utf-8'))
    before = pre['card_before']
    same_rest = comparable(before) == comparable(after)
    print('read-back tool', gtid, 'req', req, '| non-URL fields unchanged:', same_rest, '| updated_at', before.get('updated_at'), '->', after.get('updated_at'))
    if not same_rest:
        a, b = comparable(before), comparable(after)
        for k in set(a) | set(b):
            if a.get(k) != b.get(k):
                print('  DIFF', k, json.dumps(a.get(k), ensure_ascii=False)[:400], '=>', json.dumps(b.get(k), ensure_ascii=False)[:400])
    lines = []
    for ch in u['changes']:
        st = pre['status'][ch['slot']]['st']
        cur = pre['status'][ch['slot']]['cur']
        al = slot_get(after, ch['slot'])
        res = ('Fixed' if al == ch['new'] else 'Failed') if st == 'WRITE' else st
        print(' ', ch['slot'], st, '->', res, '| after==new exact:', al == ch['new'])
        print('   after_live:', al)
        lines.append({'slot': ch['slot'], 'before': cur, 'after_expected': ch['new'], 'after_live': al, 'result': res})
    json.dump({'after': after, 'get_req': req, 'write_tool': wtid, 'readback_tool': gtid, 'non_url_unchanged': same_rest, 'lines': lines},
              open(f'{W}/post_{idx}.json', 'w'), ensure_ascii=False)
