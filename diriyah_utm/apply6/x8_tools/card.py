# Helper for in_x_8 card updates. Reads my own MCP results from my transcript (tr.py).
# Usage:
#   card.py pre  <get_request_id> <unit_idx>   -> status per slot, builds payload_<i>.json, prints ascii payload
#   card.py dry  <dry_request_id> <unit_idx>   -> compares dry-run preview body with payload_<i>.json
#   card.py live <live_request_id> <unit_idx>  -> shows live PUT response summary
#   card.py post <get_request_id> <unit_idx>   -> compares re-read with expected (slots == new, all else unchanged)
import json, sys, copy, re
from urllib.parse import urlsplit, parse_qsl
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/x8_tools')
import tr

W = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/x8_work'
IN = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/in_x_8.json'
EXCL = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/work/excl_platform_refused_v2.json'
READONLY_COMP = {'media_metadata'}


def units():
    return json.load(open(IN))


def mapping():
    return json.load(open(W + '/map.json'))


def result_json(rid):
    x = tr.by_request_id(rid)
    if not x:
        raise SystemExit('request id not found in transcript: ' + rid)
    tid, (name, inp), r = x
    d = json.loads(r)
    return tid, inp, d


def eq(a, b):
    A = urlsplit(a); B = urlsplit(b)
    return ((A.scheme, A.netloc, A.path, A.fragment) == (B.scheme, B.netloc, B.path, B.fragment)
            and sorted(parse_qsl(A.query, keep_blank_values=True)) == sorted(parse_qsl(B.query, keep_blank_values=True)))


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
        obj['components'][int(m.group(1))]['destination']['url'] = val; return
    m = re.fullmatch(r'card\.slides\[(\d+)\]\[(\d+)\]\.destination\.url', slot)
    if m:
        obj['slides'][int(m.group(1))][int(m.group(2))]['destination']['url'] = val; return
    raise ValueError(slot)


def strip(comp):
    return {k: v for k, v in comp.items() if k not in READONLY_COMP}


def build_payload(card, writes):
    p = {'name': card['name']}
    if 'components' in card:
        p['components'] = [strip(c) for c in card['components']]
    if 'slides' in card:
        p['slides'] = [[strip(c) for c in s] for s in card['slides']]
    if 'experiment_signals' in card and card['experiment_signals'] is not None:
        p['experiment_signals'] = card['experiment_signals']
    for slot, new in writes:
        slot_set(p, slot, new)
    return p


def card_of(d):
    assert d.get('success') is True, json.dumps(d)[:800]
    return d['data']['data']['data']


def cmd_pre(rid, i):
    u = units()[i]
    m = mapping()
    pt = u['ad_ids'][0]
    card_id = m[pt]['card_uri'].split('//')[1]
    tid, inp, d = result_json(rid)
    assert inp.get('action') in ('GET_CARD', 'x_accounts_account_id_cards_card_id_get'), inp
    assert inp['path_params']['card_id'] == card_id, (inp, card_id)
    card = card_of(d)
    assert card['id'] == card_id and card['card_uri'] == 'card://' + card_id
    excl = json.load(open(EXCL))
    excl_keys = {(e.get('platform'), str(e.get('ad_id')), e.get('slot')) for e in excl}
    status = {}
    writes = []
    for c in u['changes']:
        slot = c['slot']
        cur = slot_get(card, slot)
        if ('x', u['unit'], slot) in excl_keys or ('x', card_id, slot) in excl_keys or ('x', pt, slot) in excl_keys:
            st = 'EXCLUDED'
        elif cur == c['new'] or eq(cur, c['new']):
            st = 'ALREADY'
        elif cur == c['now'] or cur in c.get('alt_now', []):
            st = 'WRITE'
        elif eq(cur, c['now']) or any(eq(cur, a) for a in c.get('alt_now', [])):
            st = 'WRITE(param-order)'
        else:
            st = 'CHANGED'
        status[slot] = {'cur': cur, 'st': st, 'match': ('now' if cur == c['now'] else ('alt_now' if cur in c.get('alt_now', []) else ''))}
        if st.startswith('WRITE'):
            writes.append((slot, c['new']))
    payload = build_payload(card, writes) if writes else None
    rec = {'card_id': card_id, 'card_before': card, 'status': status, 'get_tool': tid, 'get_rid': rid,
           'payload': payload}
    json.dump(rec, open(W + '/pre_%d.json' % i, 'w'), ensure_ascii=False, indent=1)
    print('unit', i, 'tweet', u['unit'], 'pt', pt, 'card', card_id, card['card_type'], 'deleted', card['deleted'],
          'experiment_signals' in card and card.get('experiment_signals'))
    for slot, s in status.items():
        print('  ', slot, s['st'], s['match'])
        if s['st'] not in ('WRITE',):
            print('      cur:', s['cur'])
    if payload:
        json.dump(payload, open(W + '/payload_%d.json' % i, 'w'), ensure_ascii=False)
        print('PAYLOAD_ASCII:')
        print(json.dumps(payload, ensure_ascii=True, separators=(',', ':')))


def norm(o):
    return json.loads(json.dumps(o))


def cmd_dry(rid, i):
    pre = json.load(open(W + '/pre_%d.json' % i))
    payload = pre['payload']
    tid, inp, d = result_json(rid)
    assert inp.get('dry_run') is True, inp
    sent = inp.get('payload')
    if isinstance(sent, str):
        sent = json.loads(sent)
    print('tool input payload == built payload:', norm(sent) == norm(payload))
    print('tool input path_params:', inp.get('path_params'), 'action:', inp.get('action'))
    print(json.dumps(d, ensure_ascii=False)[:3000])
    # find the body in the preview
    def walk(o, path=''):
        if isinstance(o, dict):
            for k, v in o.items():
                yield path + '.' + k, v
                yield from walk(v, path + '.' + k)
        elif isinstance(o, list):
            for j, v in enumerate(o):
                yield from walk(v, path + '[%d]' % j)
    found = False
    for p, v in walk(d):
        if isinstance(v, dict) and ('slides' in v or 'components' in v):
            print('preview body at', p, '== built payload:', norm(v) == norm(payload))
            found = True
        if isinstance(v, str) and v.startswith('{') and ('slides' in v or 'components' in v):
            try:
                vv = json.loads(v)
                print('preview body(str) at', p, '== built payload:', norm(vv) == norm(payload))
                found = True
            except Exception:
                pass
    print('found body in preview:', found)


def cmd_live(rid, i):
    tid, inp, d = result_json(rid)
    assert inp.get('dry_run') is False, inp
    pre = json.load(open(W + '/pre_%d.json' % i))
    sent = inp.get('payload')
    if isinstance(sent, str):
        sent = json.loads(sent)
    print('live tool input payload == built payload:', norm(sent) == norm(pre['payload']))
    print(json.dumps(d, ensure_ascii=False)[:2500])


def cmd_post(rid, i):
    u = units()[i]
    pre = json.load(open(W + '/pre_%d.json' % i))
    before = pre['card_before']
    tid, inp, d = result_json(rid)
    assert inp.get('action') in ('GET_CARD', 'x_accounts_account_id_cards_card_id_get'), inp
    assert inp['path_params']['card_id'] == pre['card_id']
    after = card_of(d)
    exp = copy.deepcopy(before)
    for c in u['changes']:
        if pre['status'][c['slot']]['st'].startswith('WRITE'):
            slot_set(exp, c['slot'], c['new'])
    res = {}
    for c in u['changes']:
        live = slot_get(after, c['slot'])
        res[c['slot']] = {'after_live': live, 'eq_new_bytes': live == c['new']}
        print('  ', c['slot'], 'after==new bytes:', live == c['new'])
    # compare everything except updated_at
    e2 = {k: v for k, v in exp.items() if k != 'updated_at'}
    a2 = {k: v for k, v in after.items() if k != 'updated_at'}
    same = norm(e2) == norm(a2)
    print('card after == card before with only slot(s) changed (ignoring updated_at):', same)
    if not same:
        for k in set(e2) | set(a2):
            if norm(e2.get(k)) != norm(a2.get(k)):
                print('   DIFF key', k)
                print('     exp:', json.dumps(e2.get(k), ensure_ascii=False)[:1500])
                print('     got:', json.dumps(a2.get(k), ensure_ascii=False)[:1500])
    print('updated_at before/after:', before.get('updated_at'), after.get('updated_at'))
    rec = {'post_tool': tid, 'post_rid': rid, 'card_after': after, 'slots': res, 'rest_unchanged': same}
    json.dump(rec, open(W + '/post_%d.json' % i, 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    cmd, rid, i = sys.argv[1], sys.argv[2], int(sys.argv[3])
    {'pre': cmd_pre, 'dry': cmd_dry, 'live': cmd_live, 'post': cmd_post}[cmd](rid, i)
