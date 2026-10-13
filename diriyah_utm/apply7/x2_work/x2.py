# Helper for apply7/in_x_2.json card updates. Reads this agent's own MCP results from its transcript (tr.py).
#   x2.py prep  <idx> <get_rid>          -> classify slots from a GET_CARD result, build payload_<idx>.json, print payload
#   x2.py dry   <idx> <dry_rid>          -> check the dry-run call input + preview body against payload_<idx>.json
#   x2.py live  <idx> <live_rid>         -> check the live call input against payload_<idx>.json, show response
#   x2.py verify <idx> <get_rid>         -> fresh GET_CARD after the write: slot(s) == new byte for byte, rest unchanged
#   x2.py record <idx> <kind> [extra]    -> append one result line per change (kind: written | nowrite)
import json, sys, copy, re
from urllib.parse import urlsplit, parse_qsl
W = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply7/x2_work'
sys.path.insert(0, W)
import tr
IN = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply7/in_x_2.json'
OUT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply7/out_x_2.jsonl'
EXCL = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/work/excl_platform_refused_v2.json'
ACCT = '18ce55o46ul'
GET_ACTIONS = ('GET_CARD', 'x_accounts_account_id_cards_card_id_get')
UPD_ACTIONS = ('UPDATE_CARD', 'x_accounts_account_id_cards_card_id_put')
READONLY_COMP = {'media_metadata'}
KEYS = ["platform", "account_id", "unit_type", "unit", "ad_ids", "ad_names", "slot", "before", "after_expected",
        "after_live", "result", "new_entity_ids", "detail"]


def units():
    return json.load(open(IN, encoding='utf-8'))


def share(u):
    return json.load(open(W + '/share_check.json'))['share'][u['unit']]


def eq(a, b):
    A = urlsplit(a); B = urlsplit(b)
    return ((A.scheme, A.netloc, A.path, A.fragment) == (B.scheme, B.netloc, B.path, B.fragment)
            and sorted(parse_qsl(A.query, keep_blank_values=True)) == sorted(parse_qsl(B.query, keep_blank_values=True)))


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


def strip(comp):
    return {k: copy.deepcopy(v) for k, v in comp.items() if k not in READONLY_COMP}


def build_payload(card, changes):
    p = {'name': card['name']}
    if card.get('components') is not None:
        p['components'] = [strip(c) for c in card['components']]
    if card.get('slides') is not None:
        p['slides'] = [[strip(c) for c in s] for s in card['slides']]
    if 'experiment_signals' in card and card['experiment_signals'] is not None:
        p['experiment_signals'] = copy.deepcopy(card['experiment_signals'])
    for ch in changes:
        slot_set(p, ch['slot'], ch['new'])
    return p


def all_urls(card):
    out = {}
    for i, comp in enumerate(card.get('components') or []):
        if isinstance(comp.get('destination'), dict) and 'url' in comp['destination']:
            out['card.components[%d].destination.url' % i] = comp['destination']['url']
    for i, s in enumerate(card.get('slides') or []):
        for j, comp in enumerate(s):
            if isinstance(comp.get('destination'), dict) and 'url' in comp['destination']:
                out['card.slides[%d][%d].destination.url' % (i, j)] = comp['destination']['url']
    return out


def comparable(card, slots):
    c = copy.deepcopy(card)
    c.pop('updated_at', None)
    for s in slots:
        slot_set(c, s, '<URL>')
    return c


def excluded(u, ch, card_id):
    for e in json.load(open(EXCL)):
        if str(e.get('platform', '')).lower() in ('x', 'twitter'):
            ids = {str(e.get('ad_id')), str(e.get('unit')), str(e.get('card_id')), str(e.get('creative_id'))}
            if (set(u['ad_ids']) | {u['unit'], str(u.get('creative_id')), card_id}) & ids and e.get('slot') in (None, ch['slot']):
                return True
    return False


def card_from(rid):
    tid, name, inp, d = tr.result_json(rid)
    assert name == 'mcp__Whathed_MCP__x_ads_native_action', name
    assert inp.get('action') in GET_ACTIONS, inp
    assert (inp.get('path_params') or {}).get('account_id') == ACCT, inp
    assert d.get('success') is True and d['data'].get('success') is True, json.dumps(d)[:800]
    card = d['data']['data']['data']
    return tid, inp, card, d


def cmd_prep(idx, rid):
    u = units()[idx]; sh = share(u); cid = sh['card_id']
    assert u['account_id'] == ACCT
    tid, inp, card, d = card_from(rid)
    assert inp['path_params']['card_id'] == cid, (inp, cid)
    assert card['id'] == cid and card['card_uri'] == sh['card_uri'], (card['id'], sh)
    print('unit', idx, u['unit'], u['ad_ids'], 'card', card['id'], card['card_type'], 'created', card.get('created_at'),
          'updated', card.get('updated_at'), '| deleted=', card.get('deleted'), '| keys=', sorted(card.keys()))
    print('  name=', repr(card['name']), '| other tweets with card:', sh['other_tweets_with_card'], '| exp_signals:',
          card.get('experiment_signals', '<absent>'))
    status = {}; towrite = []
    for ch in u['changes']:
        cur = slot_get(card, ch['slot'])
        if excluded(u, ch, cid):
            st = 'EXCLUDED'
        elif sh['other_tweets_with_card']:
            st = 'SHARED'
        elif card.get('deleted') is not False:
            st = 'DELETED'
        elif cur == ch['new'] or eq(cur, ch['new']):
            st = 'AlreadyFixed'
        elif cur == ch['now'] or cur in ch['alt_now']:
            st = 'WRITE'; towrite.append(ch)
        else:
            st = 'Skipped'
        status[ch['slot']] = {'cur': cur, 'st': st, 'match': 'now' if cur == ch['now'] else ('alt_now' if cur in ch['alt_now'] else '')}
        print(' ', ch['slot'], st, '| cur==now exact:', cur == ch['now'], '| cur in alt_now:', cur in ch['alt_now'])
        print('    cur:', cur)
    others = {k: v for k, v in all_urls(card).items() if k not in [c['slot'] for c in u['changes']]}
    print('  other URL slots on card (left untouched):', others)
    payload = build_payload(card, towrite) if towrite else None
    json.dump({'card_before': card, 'status': status, 'get_tool': tid, 'get_rid': rid, 'payload': payload},
              open(W + '/pre_%d.json' % idx, 'w'), ensure_ascii=False, indent=1)
    if payload:
        # sanity: payload differs from the card-as-read payload only in the listed slots
        asread = build_payload(card, [])
        diff = [k for k in set(all_urls(payload)) | set(all_urls(asread)) if all_urls(payload).get(k) != all_urls(asread).get(k)]
        assert sorted(diff) == sorted(c['slot'] for c in towrite), diff
        assert comparable(payload, diff) == comparable(asread, diff)
        json.dump(payload, open(W + '/payload_%d.json' % idx, 'w'), ensure_ascii=False)
        print('PAYLOAD:')
        print(json.dumps(payload, ensure_ascii=False, separators=(', ', ': ')))


def sent_payload(inp):
    pl = inp.get('payload')
    return pl if isinstance(pl, (dict, list)) else json.loads(pl)


def cmd_dry(idx, rid):
    u = units()[idx]; cid = share(u)['card_id']
    pre = json.load(open(W + '/pre_%d.json' % idx))
    exp = pre['payload']
    tid, name, inp, d = tr.result_json(rid)
    assert inp.get('action') in UPD_ACTIONS and inp.get('dry_run') is True, inp
    pp = inp.get('path_params') or {}
    print('dry call: action', inp.get('action'), '| path_params', pp, '| dry_run', inp.get('dry_run'))
    assert pp.get('account_id') == ACCT and pp.get('card_id') == cid, pp
    sent = sent_payload(inp)
    print('sent payload == built payload:', sent == exp)
    print(json.dumps(d, ensure_ascii=False)[:2500])
    req = (d.get('data') or {}).get('request') or {}
    prev = req.get('payload')
    if isinstance(prev, str):
        prev = json.loads(prev)
    print('preview payload == built payload:', prev == exp)
    if prev is not None:
        asread = build_payload(pre['card_before'], [])
        diffs = [k for k in set(all_urls(prev)) | set(all_urls(asread)) if all_urls(prev).get(k) != all_urls(asread).get(k)]
        print('URL slots changed by preview vs card as read:', diffs)
        print('non-URL parts identical to card as read:', comparable(prev, diffs) == comparable(asread, diffs))
        for k in diffs:
            print('   ', k, 'preview == new byte for byte:', prev and all_urls(prev)[k] == [c['new'] for c in u['changes'] if c['slot'] == k][0])


def cmd_live(idx, rid):
    u = units()[idx]; cid = share(u)['card_id']
    pre = json.load(open(W + '/pre_%d.json' % idx))
    tid, name, inp, d = tr.result_json(rid)
    assert inp.get('action') in UPD_ACTIONS and inp.get('dry_run') is False, inp
    pp = inp.get('path_params') or {}
    assert pp.get('account_id') == ACCT and pp.get('card_id') == cid, pp
    print('live call payload == built payload:', sent_payload(inp) == pre['payload'], '| idem', inp.get('idempotency_key'))
    print(json.dumps(d, ensure_ascii=False)[:3000])


def cmd_verify(idx, rid):
    u = units()[idx]; cid = share(u)['card_id']
    pre = json.load(open(W + '/pre_%d.json' % idx))
    tid, inp, card, d = card_from(rid)
    assert inp['path_params']['card_id'] == cid
    assert tid != pre['get_tool'], 'need a fresh GET after the write'
    print('re-read req', rid, 'updated_at before', pre['card_before'].get('updated_at'), 'after', card.get('updated_at'))
    res = {}
    for ch in u['changes']:
        v = slot_get(card, ch['slot'])
        res[ch['slot']] = {'after_live': v, 'eq_new_bytes': v == ch['new']}
        print(' ', ch['slot'], 'equals new byte for byte:', v == ch['new'])
        print('    live:', v)
    slots = [c['slot'] for c in u['changes']]
    before = pre['card_before']
    ob = {k: v for k, v in all_urls(before).items() if k not in slots}
    oa = {k: v for k, v in all_urls(card).items() if k not in slots}
    same = comparable(card, slots) == comparable(before, slots)
    print('  other URL slots unchanged:', ob == oa)
    print('  card otherwise identical (excluding updated_at and the listed URL slots):', same)
    if not same:
        print('BEFORE', json.dumps(comparable(before, slots), ensure_ascii=False))
        print('AFTER ', json.dumps(comparable(card, slots), ensure_ascii=False))
    json.dump({'card_after': card, 'get_tool': tid, 'get_rid': rid, 'slots': res, 'rest_unchanged': same},
              open(W + '/post_%d.json' % idx, 'w'), ensure_ascii=False, indent=1)


def write_line(rec):
    assert set(rec) == set(KEYS), set(rec) ^ set(KEYS)
    with open(OUT, 'a', encoding='utf-8') as f:
        f.write(json.dumps({k: rec[k] for k in KEYS}, ensure_ascii=False) + '\n')


def cmd_record(idx, kind, dry='', live='', extra=''):
    u = units()[idx]; sh = share(u); cid = sh['card_id']
    pre = json.load(open(W + '/pre_%d.json' % idx))
    card = pre['card_before']
    post = json.load(open(W + '/post_%d.json' % idx)) if kind == 'written' else None
    sc = json.load(open(W + '/share_check.json'))
    share_txt = ('card used only by this unit: tweet %s carries card://%s and is promoted only by %s (live LIST_PROMOTED_TWEETS with_deleted, '
                 'all promoted tweets created since the earliest card in this batch, reqs %s); live LIST_TWEETS card_uri of the %d other tweets '
                 'behind those promoted tweets (req %s) shows none carries this card; tweet text has no URLs.'
                 % (u['unit'], cid, ','.join(u['ad_ids']), '+'.join(sc['list_pt_reqs']), sc['n_other_checked'], sc['list_tweets_req']))
    es = card.get('experiment_signals')
    es_txt = ('experiment_signals carried as read: %s.' % json.dumps(es)) if es else 'no experiment_signals on the card as read (nothing to carry).'
    head = 'X card %s (%s, deleted=%s) behind promoted tweet %s -> tweet %s; pre-read GET_CARD req %s.' % (
        cid, card['card_type'], card['deleted'], ','.join(u['ad_ids']), u['unit'], pre['get_rid'])
    nw = sum(1 for s in pre['status'].values() if s['st'] == 'WRITE')
    for ch in u['changes']:
        s = pre['status'][ch['slot']]
        cur = s['cur']
        rec = {'platform': 'x', 'account_id': u['account_id'], 'unit_type': u['unit_type'], 'unit': u['unit'],
               'ad_ids': u['ad_ids'], 'ad_names': u['ad_names'], 'slot': ch['slot'], 'before': cur,
               'after_expected': ch['new'], 'after_live': cur, 'result': '', 'new_entity_ids': '', 'detail': ''}
        if s['st'] == 'AlreadyFixed':
            rec['result'] = 'AlreadyFixed'
            rec['detail'] = 'No write made: live value already equals new%s. %s %s' % (
                '' if cur == ch['new'] else ' (same params, different order)', head, share_txt)
        elif s['st'] == 'Skipped':
            rec['result'] = 'Skipped'
            rec['detail'] = 'changed since plan: ' + cur + ' | ' + head
        elif s['st'] == 'SHARED':
            rec['result'] = 'Skipped'
            rec['detail'] = 'card shared by other promoted tweets: ' + json.dumps(sh['other_tweets_with_card']) + ' | ' + head
        elif s['st'] == 'EXCLUDED':
            rec['result'] = 'Skipped'
            rec['detail'] = 'slot listed in excl_platform_refused_v2.json; not written. ' + head
        elif s['st'] == 'DELETED':
            rec['result'] = 'Skipped'
            rec['detail'] = 'card is deleted; not written. ' + head
        elif s['st'] == 'WRITE':
            if kind == 'written':
                v = post['slots'][ch['slot']]['after_live']
                ok = post['slots'][ch['slot']]['eq_new_bytes']
                rec['after_live'] = v
                rec['result'] = 'Fixed' if ok else 'Failed'
                rec['detail'] = ('UPDATE_CARD PUT /12/accounts/%s/cards/%s %s: before equalled %s byte for byte; dry-run req %s preview body = '
                                 'name + %s as read (read-only media_metadata not sent) with only the %d listed destination url(s) set to new; '
                                 'live req %s (with idempotency key) OK; independent GET_CARD re-read req %s: this slot %s new byte for byte; '
                                 'card otherwise %s (name, card_type, media keys, titles, destination types, deleted=false, created_at). %s %s %s'
                                 % (ACCT, cid, 'OK' if ok else 'returned but read-back differs',
                                    "'now'" if s['match'] == 'now' else "an 'alt_now' value", dry,
                                    'slides' if card.get('slides') else 'components', nw, live, post['get_rid'],
                                    'equals' if ok else 'DOES NOT equal',
                                    'identical to the pre-read' if post['rest_unchanged'] else 'DIFFERENT from the pre-read (see post_%d.json)' % idx,
                                    es_txt, head, share_txt))
            else:
                rec['result'] = kind  # Failed / NotAttempted passed explicitly
                rec['detail'] = extra + ' | ' + head
                extra_used = True
        else:
            raise SystemExit('unknown status ' + s['st'])
        if extra and s['st'] == 'WRITE' and kind == 'written':
            rec['detail'] += ' ' + extra
        write_line(rec)
        print('recorded', idx, u['unit'], ch['slot'], rec['result'], '| after==new:', rec['after_live'] == ch['new'])


if __name__ == '__main__':
    cmd = sys.argv[1]; idx = int(sys.argv[2])
    if cmd == 'prep': cmd_prep(idx, sys.argv[3])
    elif cmd == 'dry': cmd_dry(idx, sys.argv[3])
    elif cmd == 'live': cmd_live(idx, sys.argv[3])
    elif cmd == 'verify': cmd_verify(idx, sys.argv[3])
    elif cmd == 'record': cmd_record(idx, sys.argv[3], *sys.argv[4:])
    else: raise SystemExit('bad cmd')
