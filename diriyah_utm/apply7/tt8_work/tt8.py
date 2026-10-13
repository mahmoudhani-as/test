#!/usr/bin/env python3
"""apply7 in_tiktok_8 helper (Upgraded Smart+ ads). Reads this agent's own Whathead tool calls/results from its
transcript, so every value is byte-exact (no retyping). Read-only except the 'append' command.
  tt8.py reads                     -> list complete reads per ad
  tt8.py classify <ad>...|all      -> AlreadyFixed / Write / Skipped / HOLD per change, with materials
  tt8.py build <ad>                -> print the smart_plus/ad/update payload built from the latest complete read
  tt8.py call <ad> dry|live        -> check the last update call for ad: input == payload rebuilt from the pre-read; response
  tt8.py verify <ad>               -> compare the latest read after the last live call with plan "new" and with the pre-read
  tt8.py append                    -> append one result row (JSON on stdin) to the results file
"""
import json, sys, os, re, copy
from urllib.parse import urlsplit, parse_qsl
ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
INP = ROOT + '/apply7/in_tiktok_8.json'
OUT = ROOT + '/apply7/out_tiktok_8.jsonl'
T = '/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/wf_a77bf62d-a6a/agent-ab648f526f5c468a0.jsonl'
EXCL = ROOT + '/work/excl_platform_refused_v2.json'
SLOT_RE = re.compile(r'^smart_plus_ad\.landing_page_url_list\[(\d+)\]\.landing_page_url$')
GET = ('tiktok_smart_plus_ad_get',)
UPD = ('tiktok_smart_plus_ad_update',)


def units():
    return {u['unit']: u for u in json.load(open(INP))}


def qs(u):
    return sorted(parse_qsl(urlsplit(u).query, keep_blank_values=True))


def norm(u):
    s = urlsplit(u or '')
    return (s.scheme, s.netloc.lower(), s.path, s.fragment, tuple(qs(u)))


def excluded(ad, slot):
    ex = json.load(open(EXCL))
    return any(str(e.get('ad_id')) == ad and e.get('slot') == slot and e.get('platform') == 'tiktok' for e in ex)


def transcript_calls():
    uses = {}; order = []; res = {}
    for line in open(T, encoding='utf-8'):
        try:
            e = json.loads(line)
        except Exception:
            continue
        content = (e.get('message') or {}).get('content')
        if not isinstance(content, list):
            continue
        for c in content:
            if not isinstance(c, dict):
                continue
            if c.get('type') == 'tool_use' and c.get('name', '').endswith('tiktok_native_action'):
                if c['id'] not in uses:
                    uses[c['id']] = c.get('input') or {}; order.append(c['id'])
            if c.get('type') == 'tool_result' and c.get('tool_use_id') in uses:
                cc = c.get('content')
                txt = ''.join(x.get('text', '') for x in cc if isinstance(x, dict)) if isinstance(cc, list) else str(cc)
                res[c['tool_use_id']] = txt
    for i, tid in enumerate(order):
        yield i, tid, uses[tid], res.get(tid)


def load_result(txt):
    if txt is None:
        return None
    try:
        return json.loads(txt)
    except Exception:
        m = re.search(r'(?:Full output saved to|saved to):?\s*(\S+)', txt)
        if m and os.path.exists(m.group(1).rstrip('.')):
            raw = open(m.group(1).rstrip('.'), encoding='utf-8').read()
            try:
                j = json.loads(raw)
            except Exception:
                return {'_raw_text': txt}
            if isinstance(j, list) and j and isinstance(j[0], dict) and 'text' in j[0]:
                return json.loads(j[0]['text'])
            return j
        return {'_raw_text': txt}


def reads():
    out = {}
    for i, tid, inp, txt in transcript_calls():
        if inp.get('action') not in GET:
            continue
        j = load_result(txt)
        if not j or '_raw_text' in j:
            continue
        d = ((j.get('data') or {}).get('data') or {})
        rid = d.get('request_id'); lst = ((d.get('data') or {}).get('list')) or []
        trunc = bool(((j.get('meta') or {}).get('mcp_output_budget') or {}).get('truncated'))
        projected = bool(inp.get('result_fields') or inp.get('fields') or inp.get('compact') or inp.get('max_items')
                         or ((inp.get('params') or {}).get('fields')))
        for r in lst:
            if not isinstance(r, dict):
                continue
            complete = ('__mcp_truncated_keys' not in json.dumps(r)) and not trunc and not projected
            out.setdefault(r['smart_plus_ad_id'], []).append({'order': i, 'tool_use_id': tid, 'request_id': rid, 'complete': complete, 'rec': r})
    return out


def latest(ad, after_order=None, before_order=None, R=None):
    rs = (R if R is not None else reads()).get(ad) or []
    rs = [r for r in rs if r['complete'] and (after_order is None or r['order'] > after_order)
          and (before_order is None or r['order'] < before_order)]
    return rs[-1] if rs else None


def slot_index(slot):
    m = SLOT_RE.match(slot)
    assert m, 'unexpected slot %r' % slot
    return int(m.group(1))


def new_utms(new):
    q = parse_qsl(urlsplit(new).query, keep_blank_values=True)
    assert len(set(k for k, _ in q)) == len(q), 'duplicate keys in new'
    assert all(k.startswith('utm_') for k, _ in q) and not any(k == 'utm_id' for k, _ in q), 'unexpected key in new'
    return [{'key': k, 'value': v} for k, v in q]


def eff_url(rec, i):
    """URL field, utm_params keys missing from the URL, utm_params values that differ from the URL"""
    url = rec['landing_page_url_list'][i]['landing_page_url']
    have = dict(parse_qsl(urlsplit(url).query, keep_blank_values=True))
    ups = ((rec.get('ad_configuration') or {}).get('utm_params')) or []
    missing = [(p['key'], p['value']) for p in ups if p['key'] not in have]
    differ = [(p['key'], p['value'], have.get(p['key'])) for p in ups if p['key'] in have and have[p['key']] != p['value']]
    return url, missing, differ


def bigints(o, path=''):
    out = []
    if isinstance(o, dict):
        for k, v in o.items(): out += bigints(v, path + '.' + k)
    elif isinstance(o, list):
        for k, v in enumerate(o): out += bigints(v, path + '[%d]' % k)
    elif isinstance(o, (int, float)) and not isinstance(o, bool):
        out.append((path, o))
    return out


def materials(rec):
    cr = rec.get('creative_list') or []
    return [{'ad_material_id': c.get('ad_material_id'), 'ad_format': (c.get('creative_info') or {}).get('ad_format'),
             'identity_type': (c.get('creative_info') or {}).get('identity_type'), 'identity_id': (c.get('creative_info') or {}).get('identity_id'),
             'bc': (c.get('creative_info') or {}).get('identity_authorized_bc_id'),
             'tiktok_item_id': (c.get('creative_info') or {}).get('tiktok_item_id'),
             'video_id': ((c.get('creative_info') or {}).get('video_info') or {}).get('video_id'),
             'n_images': len((c.get('creative_info') or {}).get('image_info') or []),
             'music': ((c.get('creative_info') or {}).get('music_info') or {}).get('music_id'),
             'status': c.get('material_operation_status')} for c in cr]


def classify(ad, R=None):
    u = units()[ad]; r = latest(ad, R=R)
    if not r:
        return {'ad': ad, 'decision': 'NO_READ'}
    rec = r['rec']; out = []
    mats = materials(rec)
    spark_push = [m for m in mats if m['identity_type'] == 'BC_AUTH_TT' and m['tiktok_item_id']]
    for ch in u['changes']:
        i = slot_index(ch['slot'])
        lpl = rec.get('landing_page_url_list') or []
        if len(lpl) <= i:
            out.append({'slot': ch['slot'], 'decision': 'Skipped', 'why': 'slot missing (%d entries)' % len(lpl)}); continue
        url, missing, differ = eff_url(rec, i)
        if excluded(ad, ch['slot']):
            c = ('EXCLUDED', 'platform-refused list')
        elif url == ch['new']:
            c = ('AlreadyFixed', 'byte-identical')
        elif norm(url) == norm(ch['new']):
            c = ('AlreadyFixed', 'same params, other order')
        elif url == ch['now']:
            c = ('Write', 'now (byte-identical)')
        elif url in ch['alt_now']:
            c = ('Write', 'alt_now[%d]' % ch['alt_now'].index(url))
        elif norm(url) == norm(ch['now']):
            c = ('Write', 'now (same params, other order)')
        elif any(norm(url) == norm(a) for a in ch['alt_now']):
            c = ('Write', 'alt_now (same params, other order)')
        else:
            c = ('Skipped', 'changed since plan')
        out.append({'slot': ch['slot'], 'decision': c[0], 'why': c[1], 'cur': url, 'n_lp': len(lpl),
                    'utm_params_missing_from_url': missing, 'utm_params_differing': differ,
                    'utm_params': (rec.get('ad_configuration') or {}).get('utm_params')})
    return {'ad': ad, 'read_order': r['order'], 'request_id': r['request_id'], 'ad_name': rec.get('ad_name'), 'plan_name': u['ad_names'],
            'adv': rec.get('advertiser_id'), 'operation_status': rec.get('operation_status'), 'secondary_status': rec.get('secondary_status'),
            'modify_time': rec.get('modify_time'), 'materials': mats, 'spark_push_materials': spark_push,
            'ac_keys': sorted((rec.get('ad_configuration') or {}).keys()), 'ac_numbers': bigints(rec.get('ad_configuration') or {}),
            'changes': out}


def build_from(u, rec):
    assert len(u['changes']) == 1, 'multi-change unit: handle explicitly'
    ch = u['changes'][0]; i = slot_index(ch['slot'])
    lpl = copy.deepcopy(rec['landing_page_url_list'])
    lpl[i]['landing_page_url'] = ch['new']
    p = {'advertiser_id': u['account_id'], 'smart_plus_ad_id': u['unit'], 'landing_page_url_list': lpl}
    if 'ad_configuration' in rec:
        ac = copy.deepcopy(rec['ad_configuration'])
        if ac.get('utm_params'):
            ac['utm_params'] = new_utms(ch['new'])
        p['ad_configuration'] = ac
    return p


def update_calls(ad):
    found = []
    for i, tid, inp, txt in transcript_calls():
        if inp.get('action') not in UPD:
            continue
        body = inp.get('payload') or inp.get('params') or {}
        if str(body.get('smart_plus_ad_id')) == ad:
            found.append((i, tid, inp, txt))
    return found


def call(ad, mode):
    u = units()[ad]; want_dry = (mode == 'dry')
    found = [f for f in update_calls(ad) if bool(f[2].get('dry_run', True)) == want_dry]
    if not found:
        print('no %s call found' % mode); return
    i, tid, inp, txt = found[-1]
    pre = latest(ad, before_order=i)
    P = build_from(u, pre['rec'])
    body_in = inp.get('payload') or inp.get('params') or {}
    print('calls(%s):' % mode, len(found), 'order', i, '| pre-read', pre['request_id'], 'order', pre['order'],
          '| input == payload rebuilt from pre-read:', body_in == P, '| other args:', {k: v for k, v in inp.items() if k not in ('payload', 'params')})
    if body_in != P:
        for k in sorted(set(body_in) | set(P)):
            if body_in.get(k) != P.get(k):
                print('  DIFF', k, json.dumps(body_in.get(k), ensure_ascii=False)[:600], '!=', json.dumps(P.get(k), ensure_ascii=False)[:600])
    j = load_result(txt)
    if j is None:
        print('no result yet'); return
    if '_raw_text' in j:
        print('raw result:', j['_raw_text'][:2000]); return
    print('success:', j.get('success'), '| error:', json.dumps(j.get('error'), ensure_ascii=False)[:1000])
    d = j.get('data') or {}
    if want_dry:
        req = ((d.get('data') or {}).get('request')) or d.get('request') or {}
        body = req.get('body')
        print('dry method/path:', req.get('method'), req.get('path'), '| preview body == payload:', body == P)
        if body is not None and body != P:
            for k in sorted(set(body) | set(P)):
                if body.get(k) != P.get(k):
                    print('  BODY DIFF', k, json.dumps(body.get(k), ensure_ascii=False)[:600], '!=', json.dumps(P.get(k), ensure_ascii=False)[:600])
        print('dry other:', json.dumps({k: v for k, v in (d.get('data') or d).items() if k != 'request'}, ensure_ascii=False)[:800])
    else:
        dd = d.get('data') or {}
        print('live code:', dd.get('code'), '| message:', dd.get('message'), '| request_id:', dd.get('request_id'))
        print('live data:', json.dumps(dd.get('data'), ensure_ascii=False)[:1500])


def verify(ad):
    u = units()[ad]; ch = u['changes'][0]; i = slot_index(ch['slot'])
    R = reads()
    lives = [f for f in update_calls(ad) if not bool(f[2].get('dry_run', True))]
    if not lives:
        print('no live call'); return
    first_live = lives[0][0]; last_live = lives[-1][0]
    pre = latest(ad, before_order=first_live, R=R)['rec']
    r = latest(ad, after_order=last_live, R=R)
    if not r:
        print('no complete read after the live call'); return
    rec = r['rec']
    url, missing, differ = eff_url(rec, i)
    ac_pre = dict(pre.get('ad_configuration') or {}); ac_post = dict(rec.get('ad_configuration') or {})
    up_pre = ac_pre.pop('utm_params', None); up_post = ac_post.pop('utm_params', None)
    res = {'read_request_id': r['request_id'], 'after_live': url, 'equals_new_bytes': url == ch['new'],
           'utm_params_pre': up_pre, 'utm_params_post': up_post,
           'utm_params_ok': (up_pre is None and up_post is None) or (bool(up_pre) and sorted((p['key'], p['value']) for p in (up_post or [])) == sorted((p['key'], p['value']) for p in new_utms(ch['new']))) or (up_pre == [] and up_post in (None, [])),
           'utm_id_present': any(p['key'] == 'utm_id' for p in (up_post or [])) or 'utm_id=' in url,
           'missing_from_url': missing, 'differing': differ,
           'other_lp_entries_same': [x for k, x in enumerate(rec['landing_page_url_list']) if k != i] == [x for k, x in enumerate(pre['landing_page_url_list']) if k != i],
           'lp_entry_other_keys_same': {k: v for k, v in rec['landing_page_url_list'][i].items() if k != 'landing_page_url'} == {k: v for k, v in pre['landing_page_url_list'][i].items() if k != 'landing_page_url'},
           'ad_configuration_other_same': ac_pre == ac_post,
           'creative_list_same': rec.get('creative_list') == pre.get('creative_list'),
           'ad_text_list_same': rec.get('ad_text_list') == pre.get('ad_text_list'),
           'ad_name_same': rec.get('ad_name') == pre.get('ad_name'),
           'operation_status': (pre.get('operation_status'), rec.get('operation_status')),
           'secondary_status': (pre.get('secondary_status'), rec.get('secondary_status')),
           'adgroup_same': rec.get('adgroup_id') == pre.get('adgroup_id'),
           'modify_time': (pre.get('modify_time'), rec.get('modify_time')),
           'materials_post': materials(rec)}
    if not res['ad_configuration_other_same']:
        res['ac_diff'] = {k: (ac_pre.get(k), ac_post.get(k)) for k in set(ac_pre) | set(ac_post) if ac_pre.get(k) != ac_post.get(k)}
    other = {k for k in set(pre) | set(rec) if k not in ('landing_page_url_list', 'ad_configuration', 'creative_list', 'ad_text_list', 'ad_name',
                                                          'operation_status', 'secondary_status', 'modify_time', 'adgroup_id')}
    res['other_fields_diff'] = {k: (pre.get(k), rec.get(k)) for k in other if pre.get(k) != rec.get(k)}
    print(json.dumps(res, ensure_ascii=False, indent=1))


def append():
    row = json.loads(sys.stdin.read())
    req = ['platform', 'account_id', 'unit_type', 'unit', 'ad_ids', 'ad_names', 'slot', 'before', 'after_expected', 'after_live', 'result', 'new_entity_ids', 'detail']
    miss = [k for k in req if k not in row]
    assert not miss, 'missing %r' % miss
    assert row['result'] in ('Fixed', 'AlreadyFixed', 'Failed', 'Skipped', 'NotAttempted')
    u = units()[row['unit']]
    ch = [c for c in u['changes'] if c['slot'] == row['slot']][0]
    assert row['after_expected'] == ch['new'], 'after_expected != plan new'
    assert row['account_id'] == u['account_id'] and row['ad_ids'] == u['ad_ids'] and row['ad_names'] == u['ad_names'] and row['unit_type'] == u['unit_type']
    if row['result'] == 'Fixed':
        assert row['after_live'] == ch['new'], 'Fixed but after_live != new'
    with open(OUT, 'a', encoding='utf-8') as f:
        f.write(json.dumps({k: row[k] for k in req}, ensure_ascii=False) + '\n')
    print('appended', row['unit'], row['result'])


def rec(ad, result, detail):
    """build the result row from the plan + this transcript's reads, then append it"""
    u = units()[ad]; assert len(u['changes']) == 1; ch = u['changes'][0]; i = slot_index(ch['slot'])
    R = reads()
    lives = [f for f in update_calls(ad) if not bool(f[2].get('dry_run', True))]
    if lives:
        pre = latest(ad, before_order=lives[0][0], R=R); post = latest(ad, after_order=lives[-1][0], R=R)
        before = pre['rec']['landing_page_url_list'][i]['landing_page_url']
        after = post['rec']['landing_page_url_list'][i]['landing_page_url'] if post else None
        assert after is not None, 'no read-back after the live call'
    else:
        r = latest(ad, R=R)
        before = after = r['rec']['landing_page_url_list'][i]['landing_page_url']
    if result == 'Fixed':
        assert after == ch['new'], 'Fixed but read-back != new'
    if result == 'AlreadyFixed':
        assert not lives and norm(before) == norm(ch['new'])
    row = {'platform': 'tiktok', 'account_id': u['account_id'], 'unit_type': u['unit_type'], 'unit': ad, 'ad_ids': u['ad_ids'],
           'ad_names': u['ad_names'], 'slot': ch['slot'], 'before': before, 'after_expected': ch['new'], 'after_live': after,
           'result': result, 'new_entity_ids': '', 'detail': detail}
    with open(OUT, 'a', encoding='utf-8') as f:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')
    print('appended', ad, result, '| before==now:', before == ch['now'], '| after_live==new:', after == ch['new'])


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'rec':
        rec(sys.argv[2], sys.argv[3], sys.argv[4]); sys.exit(0)
    if cmd == 'reads':
        rs = reads(); U = units()
        print({k: [(x['order'], x['request_id'], x['complete']) for x in v] for k, v in rs.items() if k in U})
        print('ads without a complete read:', [k for k in U if not any(x['complete'] for x in rs.get(k, []))])
    elif cmd == 'classify':
        R = reads()
        ads = list(units()) if sys.argv[2:] == ['all'] else sys.argv[2:]
        for ad in ads:
            print(json.dumps(classify(ad, R=R), ensure_ascii=False))
    elif cmd == 'build':
        u = units()[sys.argv[2]]; r = latest(sys.argv[2])
        print('pre-read', r['request_id'], 'order', r['order'])
        print(json.dumps(build_from(u, r['rec']), ensure_ascii=False, separators=(',', ':')))
    elif cmd == 'call':
        call(sys.argv[2], sys.argv[3])
    elif cmd == 'verify':
        verify(sys.argv[2])
    elif cmd == 'append':
        append()
