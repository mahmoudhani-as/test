# Helper for in_x_5 card updates. Reads this agent's own MCP results from its transcript
# (exact API text, no retyping), evaluates slots, builds PUT payloads, writes result lines.
import json, sys, copy, re, os
from urllib.parse import urlsplit, parse_qsl

W = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/x5_work'
IN = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/in_x_5.json'
OUT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/out_x_5.jsonl'
EXCL = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/work/excl_platform_refused_v2.json'
T = '/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/wf_438dd2ce-50a/agent-a232e656e8fae4df2.jsonl'


def load_tr():
    """Return list of dicts {id, name, input, result} in call order."""
    calls = {}
    order = []
    results = {}
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
                calls[c['id']] = (c.get('name'), c.get('input'))
                order.append(c['id'])
            elif c.get('type') == 'tool_result':
                rc = c.get('content')
                if isinstance(rc, list):
                    txt = ''.join(x.get('text', '') for x in rc if isinstance(x, dict) and x.get('type') == 'text')
                elif isinstance(rc, str):
                    txt = rc
                else:
                    txt = json.dumps(rc)
                results[c['tool_use_id']] = txt
    out = []
    for i in order:
        n, inp = calls[i]
        out.append({'id': i, 'name': n, 'input': inp, 'result': results.get(i)})
    return out


def by_reqid(reqid):
    for c in load_tr():
        r = c['result'] or ''
        if reqid in r:
            return c
    raise KeyError(reqid)


def result_json(reqid):
    c = by_reqid(reqid)
    return c, json.loads(c['result'])


def eq(a, b):
    A = urlsplit(a)
    B = urlsplit(b)
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


def blank_urls(card):
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


def append_result(row):
    with open(OUT, 'a', encoding='utf-8') as f:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')


MAP = json.load(open(W + '/map_live.json'))
SHARE_NOTE = ('card not shared: live LIST_PROMOTED_TWEETS (12-Oct) has 353 non-deleted promoted tweets, the same count as the 11-Oct inventory '
              '(newest created 2026-09-30 and the 15 newest are all in the inventory, so none added since), and the inventory tweet->card_uri map of all 353 shows only tweet %s carries %s; '
              'live LIST_TWEETS 12-Oct confirms tweet %s card_uri %s and no link in the tweet text; only promoted tweet %s promotes it')


def unit_by_id(unit_id):
    for u in json.load(open(IN)):
        if u['unit'] == unit_id:
            return u
    raise KeyError(unit_id)


def finalize(idx, unit_id, get_reqid, dry_reqid, put_reqid, reread_reqid, extra=''):
    u = unit_by_id(unit_id)
    ad = u['ad_ids'][0]
    cid = MAP[ad]['card_id']
    tid = MAP[ad]['tweet_id']
    pre = json.load(open('%s/pre_%d.json' % (W, idx)))
    card0 = pre['card_before']
    assert card0['id'] == cid
    _, dprev = result_json(dry_reqid)
    prev = dprev['data']['request']['payload']
    assert dprev['data'].get('dry_run') is True
    assert dprev['data']['request']['card_id'] == cid
    prev_ok = (prev == pre['payload'])
    _, dput = result_json(put_reqid)
    assert dput.get('success') is True and dput['data'].get('success') is True, str(dput)[:500]
    put_card = dput['data']['data']['data']
    _, drr = result_json(reread_reqid)
    card1 = drr['data']['data']['data']
    assert card1['id'] == cid
    rows = []
    others_same = (blank_urls(card1) == blank_urls(card0))
    url_slots0 = all_urls(card0)
    url_slots1 = all_urls(card1)
    for ch in u['changes']:
        before = slot_get(card0, ch['slot'])
        after = slot_get(card1, ch['slot'])
        put_after = slot_get(put_card, ch['slot'])
        fixed = (after == ch['new'])
        other_slots_same = all(url_slots1[k] == v for k, v in url_slots0.items() if k != ch['slot'])
        es0 = card0.get('experiment_signals')
        es1 = card1.get('experiment_signals')
        detail = ('UPDATE_CARD PUT /12/accounts/%s/cards/%s (promoted tweet %s -> tweet %s, card_uri card://%s, %s) OK: '
                  'GET_CARD pre-read req %s: slot equalled "now" byte for byte; dry-run req %s preview body == card as read with only %s changed '
                  '(read-only media_metadata not sent)%s; live PUT req %s (response URL %s); GET_CARD re-read req %s: %s %s "new" byte for byte; '
                  'name, card_type, media keys, DETAILS title (exact codepoints incl. trailing/zero-width spaces) and every other card field %s; '
                  'experiment_signals: %s before / %s after; card updated_at %s -> %s. %s%s') % (
            u['account_id'], cid, ad, tid, cid, card0.get('card_type'),
            get_reqid, dry_reqid, ch['slot'], '' if prev_ok else ' [PREVIEW MISMATCH]', put_reqid,
            'equals new' if put_after == ch['new'] else 'DIFFERS: ' + put_after,
            reread_reqid, ch['slot'], 'equals' if fixed else 'DOES NOT equal',
            'unchanged' if (others_same and other_slots_same) else 'CHANGED (see card)',
            'none' if es0 is None else json.dumps(es0, ensure_ascii=False), 'none' if es1 is None else json.dumps(es1, ensure_ascii=False),
            card0.get('updated_at'), card1.get('updated_at'),
            SHARE_NOTE % (tid, 'card://' + cid, tid, 'card://' + cid, ad), (' ' + extra) if extra else '')
        row = {'platform': 'x', 'account_id': u['account_id'], 'unit_type': u['unit_type'], 'unit': u['unit'],
               'ad_ids': u['ad_ids'], 'ad_names': u['ad_names'], 'slot': ch['slot'], 'before': before,
               'after_expected': ch['new'], 'after_live': after,
               'result': 'Fixed' if (fixed and prev_ok) else ('Fixed' if fixed else 'Failed'),
               'new_entity_ids': '', 'detail': detail}
        rows.append(row)
    return rows, others_same


def prep(idx, unit_id, get_reqid):
    u = unit_by_id(unit_id)
    ad = u['ad_ids'][0]
    cid = MAP[ad]['card_id']
    _, d = result_json(get_reqid)
    card = d['data']['data']['data']
    assert card['id'] == cid, (card['id'], cid)
    assert d['data']['data']['request']['params']['card_id'] == cid
    sts = []
    for ch in u['changes']:
        cur = slot_get(card, ch['slot'])
        if eq(cur, ch['new']):
            st = 'ALREADY'
        elif cur == ch['now'] or cur in ch['alt_now']:
            st = 'WRITE'
        else:
            st = 'SKIP'
        sts.append((ch['slot'], st, cur))
    p = build_payload(card, [ch for ch, s in zip(u['changes'], sts) if s[1] == 'WRITE'])
    json.dump({'card_before': card, 'payload': p, 'get_reqid': get_reqid, 'status': sts}, open('%s/pre_%d.json' % (W, idx), 'w'), ensure_ascii=False, indent=1)
    return card, p, sts


def check_preview(idx, dry_reqid):
    pre = json.load(open('%s/pre_%d.json' % (W, idx)))
    _, d = result_json(dry_reqid)
    assert d['data'].get('dry_run') is True
    prev = d['data']['request']['payload']
    cid = pre['card_before']['id']
    assert d['data']['request']['card_id'] == cid
    card = pre['card_before']
    ref = {'name': card['name']}
    if card.get('components') is not None:
        ref['components'] = [strip(x) for x in card['components']]
    if card.get('slides') is not None:
        ref['slides'] = [[strip(x) for x in s] for s in card['slides']]
    if 'experiment_signals' in card:
        ref['experiment_signals'] = card['experiment_signals']

    def bl(p):
        p = json.loads(json.dumps(p))
        for comp in p.get('components') or []:
            if isinstance(comp.get('destination'), dict):
                comp['destination']['url'] = '<URL>'
        for s in p.get('slides') or []:
            for comp in s:
                if isinstance(comp.get('destination'), dict):
                    comp['destination']['url'] = '<URL>'
        return p
    return prev == pre['payload'], bl(prev) == bl(ref), cid
