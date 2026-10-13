# Helper for apply7/in_x_1.json card updates. Reads this agent's own MCP results from its transcript
# (exact API text, no retyping), evaluates slots, builds PUT payloads, checks previews, writes result lines.
import json, sys, copy, re
from urllib.parse import urlsplit, parse_qsl
W = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply7/x1_work'
sys.path.insert(0, W)
from tr import by_reqid
IN = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply7/in_x_1.json'
OUT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply7/out_x_1.jsonl'
EXCL = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/work/excl_platform_refused_v2.json'
ACCT = '18ce55o46ul'
KEYS = ["platform", "account_id", "unit_type", "unit", "ad_ids", "ad_names", "slot", "before", "after_expected",
        "after_live", "result", "new_entity_ids", "detail"]


def units():
    return json.load(open(IN, encoding='utf-8'))


def share():
    return json.load(open(W + '/share.json', encoding='utf-8'))


def eq(a, b):
    A = urlsplit(a); B = urlsplit(b)
    return (A.scheme, A.netloc, A.path, A.fragment) == (B.scheme, B.netloc, B.path, B.fragment) and \
        sorted(parse_qsl(A.query, keep_blank_values=True)) == sorted(parse_qsl(B.query, keep_blank_values=True))


def slot_path(slot):
    m = re.fullmatch(r'card\.components\[(\d+)\]\.destination\.url', slot)
    if m:
        return ('components', int(m.group(1)))
    m = re.fullmatch(r'card\.slides\[(\d+)\]\[(\d+)\]\.destination\.url', slot)
    if m:
        return ('slides', int(m.group(1)), int(m.group(2)))
    raise ValueError(slot)


def slot_get(card, slot):
    p = slot_path(slot)
    if p[0] == 'components':
        return card['components'][p[1]]['destination']['url']
    return card['slides'][p[1]][p[2]]['destination']['url']


def slot_set(obj, slot, val):
    p = slot_path(slot)
    if p[0] == 'components':
        obj['components'][p[1]]['destination']['url'] = val
    else:
        obj['slides'][p[1]][p[2]]['destination']['url'] = val


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


def all_urls(card):
    out = {}
    for i, comp in enumerate(card.get('components') or []):
        if isinstance(comp, dict) and isinstance(comp.get('destination'), dict) and 'url' in comp['destination']:
            out['card.components[%d].destination.url' % i] = comp['destination']['url']
    for i, s in enumerate(card.get('slides') or []):
        for j, comp in enumerate(s):
            if isinstance(comp, dict) and isinstance(comp.get('destination'), dict) and 'url' in comp['destination']:
                out['card.slides[%d][%d].destination.url' % (i, j)] = comp['destination']['url']
    return out


def excluded(u, ch):
    for e in json.load(open(EXCL)):
        if str(e.get('platform', '')).lower() in ('x', 'twitter'):
            ids = {e.get('ad_id'), e.get('unit'), e.get('card_id'), e.get('creative_id')}
            if (set(u['ad_ids']) | {u['unit'], u.get('creative_id')}) & ids and e.get('slot') in (None, ch['slot']):
                return True
    return False


def get_card(reqid, card_id):
    t, name, inp, txt = by_reqid(reqid)
    assert name.endswith('x_ads_native_action'), name
    assert inp.get('action') in ('GET_CARD', 'x_accounts_account_id_cards_card_id_get'), inp
    assert (inp.get('path_params') or {}).get('card_id') == card_id, inp
    assert (inp.get('path_params') or {}).get('account_id') == ACCT, inp
    d = json.loads(txt)
    assert d.get('success') is True and d['data'].get('success') is True, txt[:500]
    card = d['data']['data']['data']
    assert card['id'] == card_id and d['data']['data']['request']['params']['card_id'] == card_id
    return card


def write_line(rec):
    assert set(rec) == set(KEYS), set(rec) ^ set(KEYS)
    with open(OUT, 'a', encoding='utf-8') as f:
        f.write(json.dumps({k: rec[k] for k in KEYS}, ensure_ascii=False) + '\n')


def base(u, ch):
    return {"platform": "x", "account_id": u['account_id'], "unit_type": u['unit_type'], "unit": u['unit'],
            "ad_ids": u['ad_ids'], "ad_names": u['ad_names'], "slot": ch['slot'], "after_expected": ch['new'],
            "new_entity_ids": ""}


def share_note(u):
    s = share()[u['unit']]
    return ('share check 12-Oct ~22:05 UTC: live LIST_PROMOTED_TWEETS (536 incl. deleted, 365 non-deleted) + LIST_TWEETS card_uri of all 448 '
            'promoted tweets\' tweets: %s is carried only by tweet %s, promoted only by %s (no other promoted tweet, deleted or not); '
            'tweet text has no links') % (s['card_uri'], ','.join(s['tweets_with_card']), ','.join(p['id'] for p in s['promoted_using']))


def evaluate(idx, reqid):
    u = units()[idx]
    s = share()[u['unit']]
    card = get_card(reqid, s['card_id'])
    st = {}
    towrite = []
    for ch in u['changes']:
        cur = slot_get(card, ch['slot'])
        if excluded(u, ch):
            r = 'EXCLUDED'
        elif not s['ok']:
            r = 'SHARED'
        elif cur == ch['new'] or eq(cur, ch['new']):
            r = 'AlreadyFixed'
        elif cur == ch['now'] or cur in ch['alt_now'] or eq(cur, ch['now']) or any(eq(cur, a) for a in ch['alt_now']):
            r = 'WRITE'
            towrite.append(ch)
        else:
            r = 'Skipped'
        st[ch['slot']] = {'cur': cur, 'st': r, 'cur_eq_new_exact': cur == ch['new'], 'cur_eq_now_exact': cur == ch['now'],
                          'cur_in_alt_exact': cur in ch['alt_now'],
                          'which': 'now' if (cur == ch['now'] or eq(cur, ch['now'])) else
                          ('alt_now[%d]' % [i for i, a in enumerate(ch['alt_now']) if cur == a or eq(cur, a)][0]
                           if any(cur == a or eq(cur, a) for a in ch['alt_now']) else '')}
    return u, s, card, st, towrite


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'prep':
        idx = int(sys.argv[2]); reqid = sys.argv[3]
        u, s, card, st, towrite = evaluate(idx, reqid)
        print('unit', idx, u['unit'], 'ads', u['ad_ids'], 'card', card['id'], card['card_type'], '| name=', repr(card['name']),
              '| deleted=', card.get('deleted'), '| keys=', sorted(card.keys()), '| exp_signals' if 'experiment_signals' in card else '')
        for k, v in st.items():
            print(' ', k, v['st'], '| exact new/now/alt:', v['cur_eq_new_exact'], v['cur_eq_now_exact'], v['cur_in_alt_exact'], '| matched', v['which'])
            print('    cur:', v['cur'])
        other = {k: v for k, v in all_urls(card).items() if k not in st}
        print('  other URL slots on card (left untouched):', other)
        json.dump({'card_before': card, 'status': st, 'get_req': reqid}, open('%s/pre_%d.json' % (W, idx), 'w'), ensure_ascii=False, indent=1)
        if towrite:
            p = build_payload(card, towrite)
            json.dump(p, open('%s/payload_%d.json' % (W, idx), 'w'), ensure_ascii=False)
            print('PAYLOAD', json.dumps(p, ensure_ascii=False))
            print('PAYLOAD_ASCII', json.dumps(p, ensure_ascii=True))
            odd = sorted({hex(ord(c)) for c in json.dumps(p, ensure_ascii=False) if ord(c) > 127 and not ('؀' <= c <= 'ۿ')})
            print('  non-ascii non-arabic codepoints in payload:', odd)
    elif cmd == 'already':
        # result lines for slots that are already correct (no write)
        idx = int(sys.argv[2]); reqid = sys.argv[3]; extra = sys.argv[4] if len(sys.argv) > 4 else ''
        u, s, card, st, towrite = evaluate(idx, reqid)
        assert not towrite
        for ch in u['changes']:
            v = st[ch['slot']]
            assert v['st'] == 'AlreadyFixed', v
            rec = base(u, ch)
            rec.update(before=v['cur'], after_live=v['cur'], result='AlreadyFixed',
                       detail=('No write. GET_CARD /12/accounts/%s/cards/%s (%s, promoted tweet %s -> tweet %s) req %s: %s already equals "new"%s '
                               '(card updated_at %s). %s.%s') % (
                           u['account_id'], card['id'], card['card_type'], ','.join(u['ad_ids']), u['unit'], reqid, ch['slot'],
                           ' byte for byte' if v['cur_eq_new_exact'] else ' (same params, different order)',
                           card.get('updated_at'), share_note(u), (' ' + extra) if extra else ''))
            write_line(rec)
            print('wrote AlreadyFixed', u['unit'], ch['slot'])
    elif cmd == 'checkdry':
        idx = int(sys.argv[2]); reqid = sys.argv[3]
        t, name, inp, txt = by_reqid(reqid)
        exp = json.load(open('%s/payload_%d.json' % (W, idx)))
        pre = json.load(open('%s/pre_%d.json' % (W, idx)))
        cid = pre['card_before']['id']
        pl = inp.get('payload')
        sent = pl if isinstance(pl, (dict, list)) else json.loads(pl)
        d = json.loads(txt)
        print('action:', inp.get('action'), '| path_params:', inp.get('path_params'), '| dry_run:', inp.get('dry_run'), '| idem:', inp.get('idempotency_key'))
        print('sent==expected:', sent == exp)
        assert d.get('success') is True, txt[:800]
        dd = d['data']
        print('dry_run flag in response:', dd.get('dry_run'), '| method', dd.get('method'), '| endpoint', dd.get('endpoint'))
        prev = dd['request']['payload']
        print('preview==expected:', prev == exp, '| preview card_id:', dd['request'].get('card_id'), '==', cid, dd['request'].get('card_id') == cid,
              '| account', dd['request'].get('account_id'))
        # what differs between the card as read and the preview, URLs blanked
        card = pre['card_before']
        ref = build_payload(card, [])
        print('preview == card-as-read except URL slots:', comparable(prev) == comparable(ref))
        diffs = {k: (v, all_urls(prev).get(k)) for k, v in all_urls(ref).items() if all_urls(prev).get(k) != v}
        print('URL slots changed by preview:', json.dumps(diffs, ensure_ascii=False))
        if sent != exp:
            print('SENT', json.dumps(sent, ensure_ascii=False)); print('EXP ', json.dumps(exp, ensure_ascii=False))
        print('warnings:', dd.get('warnings'))
    elif cmd == 'final':
        # final idx get_req dry_req put_req reread_req [extra]
        idx = int(sys.argv[2]); get_req, dry_req, put_req, rr_req = sys.argv[3:7]
        extra = sys.argv[7] if len(sys.argv) > 7 else ''
        u = units()[idx]
        s = share()[u['unit']]
        pre = json.load(open('%s/pre_%d.json' % (W, idx)))
        assert pre['get_req'] == get_req
        card0 = pre['card_before']
        cid = card0['id']
        exp = json.load(open('%s/payload_%d.json' % (W, idx)))
        # dry run
        t, name, dinp, dtxt = by_reqid(dry_req)
        dd = json.loads(dtxt)['data']
        assert dinp.get('dry_run') is True and dd.get('dry_run') is True
        prev_ok = dd['request']['payload'] == exp and dd['request'].get('card_id') == cid
        dsent = dinp['payload'] if isinstance(dinp['payload'], dict) else json.loads(dinp['payload'])
        # live put
        t, name, pinp, ptxt = by_reqid(put_req)
        assert pinp.get('dry_run') is False, pinp
        assert pinp.get('action') in ('UPDATE_CARD', 'x_accounts_account_id_cards_card_id_put')
        assert (pinp.get('path_params') or {}).get('card_id') == cid and (pinp.get('path_params') or {}).get('account_id') == ACCT
        psent = pinp['payload'] if isinstance(pinp['payload'], dict) else json.loads(pinp['payload'])
        sent_ok = (psent == exp) and (dsent == exp)
        pd = json.loads(ptxt)
        put_ok = pd.get('success') is True and pd['data'].get('success') is True
        put_card = pd['data']['data']['data'] if put_ok else None
        # re-read
        card1 = get_card(rr_req, cid)
        others_same = comparable(card1) == comparable(card0)
        u0 = all_urls(card0); u1 = all_urls(card1)
        for ch in u['changes']:
            v = pre['status'][ch['slot']]
            rec = base(u, ch)
            after = slot_get(card1, ch['slot'])
            if v['st'] != 'WRITE':
                raise SystemExit('slot not in WRITE state: %s' % v)
            fixed = (after == ch['new'])
            other_slots_same = all(u1.get(k) == x for k, x in u0.items() if k not in [c['slot'] for c in u['changes']])
            es0 = card0.get('experiment_signals'); es1 = card1.get('experiment_signals')
            put_url = slot_get(put_card, ch['slot']) if put_card else None
            detail = ('UPDATE_CARD PUT /12/accounts/%s/cards/%s (%s; promoted tweet %s -> tweet %s, card_uri card://%s). '
                      'Pre-read GET_CARD req %s: slot equalled %s%s. Dry-run req %s: preview body %s (name + components%s as read, media_metadata not sent, '
                      'only %s changed). Live PUT req %s (idempotency key %s): %s; response URL %s. Re-read GET_CARD req %s: %s %s "new" byte for byte; '
                      'every other card field (name, card_type, media keys, titles, other URL slots) %s; experiment_signals %s before / %s after; '
                      'updated_at %s -> %s. %s.%s') % (
                u['account_id'], cid, card0.get('card_type'), ','.join(u['ad_ids']), u['unit'], cid,
                get_req, v['which'] or '?', ' byte for byte' if (v['cur_eq_now_exact'] or v['cur_in_alt_exact']) else ' (same params, different order)',
                dry_req, 'matched the planned payload exactly' if prev_ok else 'DID NOT match the planned payload',
                ' + experiment_signals' if 'experiment_signals' in card0 else '', ch['slot'],
                put_req, pinp.get('idempotency_key'), 'success' if put_ok else ('FAILED: ' + ptxt[:400]),
                'equals new' if put_url == ch['new'] else ('DIFFERS: %s' % put_url),
                rr_req, ch['slot'], 'equals' if fixed else 'DOES NOT equal',
                'unchanged' if (others_same and other_slots_same) else 'CHANGED (see card)',
                'none' if es0 is None else json.dumps(es0, ensure_ascii=False), 'none' if es1 is None else json.dumps(es1, ensure_ascii=False),
                card0.get('updated_at'), card1.get('updated_at'), share_note(u), (' ' + extra) if extra else '')
            if not sent_ok:
                detail += ' [WARNING: sent payload differed from the planned payload]'
            rec.update(before=v['cur'], after_live=after, result='Fixed' if (fixed and put_ok) else 'Failed', detail=detail)
            write_line(rec)
            print(rec['result'], u['unit'], ch['slot'], '| prev_ok', prev_ok, '| sent_ok', sent_ok, '| others_same', others_same, other_slots_same)
            print('  after:', after)
