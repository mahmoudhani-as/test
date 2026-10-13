# apply9 in_x_1 helper (read-only): parses this agent's own Whathead results from its transcript,
# checks slots, prepares the expected card body, and checks dry-run / live / read-back.
# It never calls any API and writes only inside apply9/work_x_1/.
import json, sys, copy, re, os
from urllib.parse import urlsplit, parse_qsl

W = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply9/work_x_1'
IN = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply9/in_x_1.json'
EXCL = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/work/excl_platform_refused_v2.json'
T = '/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/wf_e037ea0c-022/agent-a09fca1f031f046ce.jsonl'
TOOL = 'mcp__Whathed_MCP__x_ads_native_action'


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


def pp_of(inp):
    pp = dict(inp.get('path_params') or {})
    if 'account_id' not in pp and inp.get('account_id'):
        pp['account_id'] = inp.get('account_id')
    return pp


def x_calls(action=None, card_id=None, dry=None, after=None, account=None):
    calls, results, order = load_tr()
    out = []
    start = order.index(after) + 1 if after else 0
    for i in order[start:]:
        nm, inp = calls[i]
        if nm != TOOL or not isinstance(inp, dict):
            continue
        if action and inp.get('action') != action:
            continue
        pp = pp_of(inp)
        if card_id is not None and str(pp.get('card_id')) != str(card_id):
            continue
        if account is not None and str(pp.get('account_id')) != str(account):
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


def req_of(res_txt):
    try:
        return parse_result(res_txt).get('meta', {}).get('requestId')
    except Exception:
        return None


cmd = sys.argv[1]

if cmd == 'share':
    # share <account_id>: uses the latest LIST_PROMOTED_TWEETS and LIST_TWEETS for that account
    acct = sys.argv[2]
    pts = [c for c in x_calls('LIST_PROMOTED_TWEETS', account=acct) if c[2] is not None]
    tws = [c for c in x_calls('LIST_TWEETS', account=acct) if c[2] is not None]
    ptid, _, ptres = pts[-1]
    twid, twinp, twres = tws[-1]
    P = parse_result(ptres)
    Tw = parse_result(twres)
    ptl = P['data']['data']['data']
    twl = Tw['data']['data']['data']
    asked = [str(x) for x in Tw['data']['data']['request']['params']['tweet_ids']]
    got = [t['id_str'] for t in twl]
    print('promoted tweets listed:', len(ptl), '| next_cursor:', P['data']['data'].get('next_cursor'),
          '| newest:', ptl[0]['created_at'], '| oldest in page:', ptl[-1]['created_at'], '| req', req_of(ptres))
    print('tweets asked:', len(asked), 'returned:', len(got), 'missing:', sorted(set(asked) - set(got)), '| req', req_of(twres))
    my = [u for u in units() if u['account_id'] == acct]
    mincard = min(int(u['unit']) for u in my)
    newer = sorted({p['tweet_id'] for p in ptl if int(p['tweet_id']) > mincard})
    print('distinct promoted tweet ids newer than the oldest card of this account:', len(newer), '| all read:', set(newer) <= set(got))
    # promoted tweets listed in the page must cover every promoted tweet that can use these cards:
    # the page is created_at-desc; a promoted tweet created before the card cannot reference a tweet created after it
    oldest_pt_created = ptl[-1]['created_at']
    print('oldest promoted-tweet created_at in page:', oldest_pt_created)
    card_tweets = {}
    for t in twl:
        cu = t.get('card_uri') or ''
        card_tweets.setdefault(cu.replace('card://', ''), []).append(t['id_str'])
    links = [t['id_str'] for t in twl if re.search(r'https?://|t\.co/', t.get('full_text') or '')]
    out = {}
    allok = True
    for u in my:
        cid = u['unit']
        tw = card_tweets.get(cid, [])
        prom = [(p['id'], p['deleted'], p['tweet_id'], p['line_item_id']) for p in ptl if p['tweet_id'] in tw]
        others = [p for p in prom if p[0] not in u['ad_ids']]
        ok = bool(tw) and not others and {p[0] for p in prom} == set(u['ad_ids'])
        allok &= ok
        out[cid] = {'tweets': tw, 'promoted': prom, 'others': others, 'ok': ok, 'text_links': [t for t in tw if t in links]}
        print(cid, 'tweets', tw, 'promoted', prom, 'others', others, 'OK' if ok else 'CHECK', 'TEXT-LINKS' if out[cid]['text_links'] else 'no-text-links')
    prev = {}
    if os.path.exists(f'{W}/share_check.json'):
        prev = json.load(open(f'{W}/share_check.json', encoding='utf-8'))
    prev[acct] = {'promoted_tool': ptid, 'promoted_req': req_of(ptres), 'tweets_tool': twid, 'tweets_req': req_of(twres), 'cards': out}
    json.dump(prev, open(f'{W}/share_check.json', 'w'), ensure_ascii=False, indent=1)
    print('ALL OK' if allok else 'NOT ALL OK')

elif cmd == 'pre':
    # pre <idx>: uses the latest GET_CARD for the unit's card
    idx = int(sys.argv[2])
    u = units()[idx]
    cid = u['unit']
    lst = [c for c in x_calls('GET_CARD', cid, account=u['account_id']) if c[2] is not None]
    tid, inp, res = lst[-1]
    card, req = card_of(res)
    assert str(card['id']) == str(cid), (card['id'], cid)
    print('unit', idx, 'card', card['id'], card.get('card_type'), '| deleted', card.get('deleted'), '| name', json.dumps(card.get('name'), ensure_ascii=False),
          '| keys', sorted(card.keys()), '| experiment_signals' if 'experiment_signals' in card else '| no experiment_signals', '| GET req', req,
          '| updated_at', card.get('updated_at'))
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
        print('PAYLOAD', json.dumps(p, ensure_ascii=False))
        nonascii = sorted({ch for ch in json.dumps(p, ensure_ascii=False) if ord(ch) > 127 and not ('؀' <= ch <= 'ۿ')})
        print('non-Arabic non-ASCII chars in payload:', [hex(ord(c)) for c in nonascii])

elif cmd == 'dry':
    idx = int(sys.argv[2])
    u = units()[idx]
    cid = u['unit']
    lst = [c for c in x_calls('UPDATE_CARD', cid, dry=True, account=u['account_id']) if c[2] is not None]
    tid, inp, res = lst[-1]
    exp = json.load(open(f'{W}/payload_{idx}.json', encoding='utf-8'))
    sent = inp['payload'] if isinstance(inp['payload'], dict) else json.loads(inp['payload'])
    pp = pp_of(inp)
    print('dry tool', tid, '| dry_run flag:', inp.get('dry_run'), '| path_params:', pp)
    print('sent == expected:', sent == exp, '| sent json == expected json:', json.dumps(sent, ensure_ascii=False) == json.dumps(exp, ensure_ascii=False))
    if sent != exp:
        print('  SENT    ', json.dumps(sent, ensure_ascii=True)[:3000])
        print('  EXPECTED', json.dumps(exp, ensure_ascii=True)[:3000])
    d = parse_result(res)
    print('dry result success:', d.get('success'), '| req', d.get('meta', {}).get('requestId'))
    try:
        dd = d['data']
        print('gateway keys:', sorted(dd.keys()) if isinstance(dd, dict) else type(dd))
        print('gateway dry_run:', dd.get('dry_run'))
        reqd = dd.get('request') or {}
        echo = reqd.get('payload', reqd.get('body'))
        print('echoed method/endpoint:', reqd.get('method'), reqd.get('endpoint') or reqd.get('path') or reqd.get('url'))
        print('echoed body == expected:', echo == exp)
        if echo != exp:
            print('  ECHO', json.dumps(echo, ensure_ascii=True)[:3000])
    except Exception as ex:
        print('no echo parsed:', ex)
    print('raw result (first 1500):', res[:1500].replace('\n', ' '))
    pre = json.load(open(f'{W}/pre_{idx}.json', encoding='utf-8'))
    before = pre['card_before']
    b2 = build_payload(before, [])
    diffs = [k for k in set(b2) | set(sent) if b2.get(k) != sent.get(k)]
    after_cmp = copy.deepcopy(before)
    for ch in u['changes']:
        if pre['status'][ch['slot']]['st'] == 'WRITE':
            slot_set(after_cmp, ch['slot'], ch['new'])
    print('top-level keys that differ from card-as-read:', diffs)
    print('payload equals card-as-read except the listed URL(s):', build_payload(after_cmp, []) == sent)
    print('account/card in path:', pp.get('account_id') == u['account_id'], str(pp.get('card_id')) == str(cid))

elif cmd == 'verify':
    idx = int(sys.argv[2])
    u = units()[idx]
    cid = u['unit']
    lives = [c for c in x_calls('UPDATE_CARD', cid, dry=False, account=u['account_id']) if c[2] is not None]
    wtid, winp, wres = lives[-1]
    exp = json.load(open(f'{W}/payload_{idx}.json', encoding='utf-8'))
    sent = winp['payload'] if isinstance(winp['payload'], dict) else json.loads(winp['payload'])
    print('live tool', wtid, '| dry_run:', winp.get('dry_run'), '| idem:', winp.get('idempotency_key'), '| sent == expected:', sent == exp,
          '| live attempts for this card:', len(lives))
    print('live raw result (first 1500):', wres[:1500].replace('\n', ' '))
    gets = [c for c in x_calls('GET_CARD', cid, after=wtid, account=u['account_id']) if c[2] is not None]
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
                print('  DIFF', k, json.dumps(a.get(k), ensure_ascii=False)[:600], '=>', json.dumps(b.get(k), ensure_ascii=False)[:600])
    lines = []
    for ch in u['changes']:
        st = pre['status'][ch['slot']]['st']
        cur = pre['status'][ch['slot']]['cur']
        al = slot_get(after, ch['slot'])
        res = ('Fixed' if al == ch['new'] else 'Failed') if st == 'WRITE' else st
        print(' ', ch['slot'], st, '->', res, '| after==new exact:', al == ch['new'])
        print('   after_live:', al)
        lines.append({'slot': ch['slot'], 'before': cur, 'after_expected': ch['new'], 'after_live': al, 'result': res})
    json.dump({'after': after, 'get_req': req, 'write_tool': wtid, 'write_req': req_of(wres), 'readback_tool': gtid,
               'non_url_unchanged': same_rest, 'lines': lines},
              open(f'{W}/post_{idx}.json', 'w'), ensure_ascii=False)
