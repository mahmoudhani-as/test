#!/usr/bin/env python3
"""apply7 in_tiktok_10 helper (Upgraded Smart+ ads only). Reads this agent's own Whathead tool calls/results
from its transcript, so every value is byte-exact (no retyping).
usage:
  tt10.py reads                       -> parse every tiktok_smart_plus_ad_get result, save reads.json
  tt10.py classify <ad_id>...         -> classify latest complete read vs plan (AlreadyFixed / write / Skipped)
  tt10.py build <ad_id>               -> build smart_plus/ad/update payload from latest complete read, print compact JSON
  tt10.py call <ad_id> dry|live       -> check the last smart_plus update call for ad_id: input == built payload; response summary
  tt10.py verify <ad_id>              -> compare latest read after the live call with plan "new" and with the pre-read
  tt10.py append <row.json>           -> append one result line to the results file
"""
import json, sys, os, re, copy
from urllib.parse import urlsplit, parse_qsl
ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
INP = ROOT + '/apply7/in_tiktok_10.json'
OUT = ROOT + '/apply7/out_tiktok_10.jsonl'
W = ROOT + '/apply7/tt10_work/'
T = '/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/wf_96598b86-20e/agent-aeb44c3368cc310c5.jsonl'
EXCL = ROOT + '/work/excl_platform_refused_v2.json'
SLOT_RE = re.compile(r'^smart_plus_ad\.landing_page_url_list\[(\d+)\]\.landing_page_url$')


def units():
    return {u['unit']: u for u in json.load(open(INP))}


def qs(u):
    return sorted(parse_qsl(urlsplit(u).query, keep_blank_values=True))


def norm(u):
    s = urlsplit(u or '')
    return (s.scheme, s.netloc.lower(), s.path, s.fragment, tuple(qs(u)))


def excluded(ad, slot):
    try:
        ex = json.load(open(EXCL))
    except Exception:
        return False
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
        if m and os.path.exists(m.group(1)):
            raw = open(m.group(1), encoding='utf-8').read()
            try:
                j = json.loads(raw)
            except Exception:
                return None
            if isinstance(j, list) and j and isinstance(j[0], dict) and 'text' in j[0]:
                return json.loads(j[0]['text'])
            return j
        return {'_raw_text': txt}


def reads():
    out = {}
    for i, tid, inp, txt in transcript_calls():
        if inp.get('action') not in ('tiktok_smart_plus_ad_get', 'tiktok_smart_ad_get'):
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
            complete = ('__mcp_truncated_keys' not in r) and not trunc and not projected
            out.setdefault(r['smart_plus_ad_id'], []).append({'order': i, 'tool_use_id': tid, 'request_id': rid, 'complete': complete, 'rec': r})
    return out


def latest(ad, complete=True, after_order=None, before_order=None):
    rs = reads().get(ad) or []
    rs = [r for r in rs if (r['complete'] or not complete) and (after_order is None or r['order'] > after_order)
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
    """full landing URL incl. separately stored utm_params (keys missing from the URL), plus diffs"""
    url = rec['landing_page_url_list'][i]['landing_page_url']
    have = dict(parse_qsl(urlsplit(url).query, keep_blank_values=True))
    ups = ((rec.get('ad_configuration') or {}).get('utm_params')) or []
    missing = [(p['key'], p['value']) for p in ups if p['key'] not in have]
    differ = [(p['key'], p['value'], have.get(p['key'])) for p in ups if p['key'] in have and have[p['key']] != p['value']]
    return url, missing, differ


def classify(ad):
    u = units()[ad]; r = latest(ad)
    if not r:
        return {'ad': ad, 'decision': 'NO_READ'}
    rec = r['rec']; out = []
    cr = rec.get('creative_list') or []
    mats = [{'ad_material_id': c.get('ad_material_id'), 'ad_format': (c.get('creative_info') or {}).get('ad_format'),
             'identity_type': (c.get('creative_info') or {}).get('identity_type'), 'identity_id': (c.get('creative_info') or {}).get('identity_id'),
             'tiktok_item_id': (c.get('creative_info') or {}).get('tiktok_item_id'),
             'video_id': ((c.get('creative_info') or {}).get('video_info') or {}).get('video_id'),
             'n_images': len((c.get('creative_info') or {}).get('image_info') or [])} for c in cr]
    for ch in u['changes']:
        i = slot_index(ch['slot'])
        url, missing, differ = eff_url(rec, i)
        if excluded(ad, ch['slot']):
            c = ('EXCLUDED', 'platform-refused list')
        elif url == ch['new']:
            c = ('AlreadyFixed', 'byte-identical')
        elif norm(url) == norm(ch['new']):
            c = ('AlreadyFixed', 'same params, other order')
        elif url == ch['now']:
            c = ('write', 'now')
        elif url in ch['alt_now']:
            c = ('write', 'alt_now[%d]' % ch['alt_now'].index(url))
        elif norm(url) == norm(ch['now']):
            c = ('write', 'now (same params, other order)')
        elif any(norm(url) == norm(a) for a in ch['alt_now']):
            c = ('write', 'alt_now (same params, other order)')
        else:
            c = ('Skipped', 'changed since plan')
        out.append({'slot': ch['slot'], 'decision': c[0], 'why': c[1], 'cur': url, 'n_lp': len(rec['landing_page_url_list']),
                    'utm_params_missing_from_url': missing, 'utm_params_differing': differ,
                    'utm_params': (rec.get('ad_configuration') or {}).get('utm_params')})
    return {'ad': ad, 'read_order': r['order'], 'request_id': r['request_id'], 'ad_name': rec.get('ad_name'),
            'operation_status': rec.get('operation_status'), 'secondary_status': rec.get('secondary_status'),
            'modify_time': rec.get('modify_time'), 'materials': mats, 'changes': out}


def build(ad):
    u = units()[ad]; r = latest(ad); rec = r['rec']
    assert len(u['changes']) == 1, 'multi-change unit: handle explicitly'
    ch = u['changes'][0]; i = slot_index(ch['slot'])
    lpl = copy.deepcopy(rec['landing_page_url_list'])
    lpl[i]['landing_page_url'] = ch['new']
    ac = copy.deepcopy(rec['ad_configuration'])
    if 'utm_params' in ac:
        ac['utm_params'] = new_utms(ch['new'])
    p = {'advertiser_id': u['account_id'], 'smart_plus_ad_id': ad, 'landing_page_url_list': lpl, 'ad_configuration': ac}
    json.dump({'payload': p, 'pre_read': r['request_id'], 'pre_order': r['order'], 'pre_rec': rec}, open(W + 'payload_%s.json' % ad, 'w'), ensure_ascii=False, indent=1)
    return p


def update_calls(ad):
    found = []
    for i, tid, inp, txt in transcript_calls():
        if inp.get('action') not in ('tiktok_smart_plus_ad_update', 'tiktok_smart_ad_update'):
            continue
        body = inp.get('payload') or inp.get('params') or {}
        if str(body.get('smart_plus_ad_id')) == ad:
            found.append((i, tid, inp, txt))
    return found


def call(ad, mode):
    P = json.load(open(W + 'payload_%s.json' % ad))['payload']
    want_dry = (mode == 'dry')
    found = [f for f in update_calls(ad) if bool(f[2].get('dry_run', True)) == want_dry]
    if not found:
        print('no %s call found' % mode); return
    i, tid, inp, txt = found[-1]
    body_in = inp.get('payload') or inp.get('params') or {}
    print('calls(%s):' % mode, len(found), 'order', i, '| input == built payload:', body_in == P,
          '| other args:', {k: v for k, v in inp.items() if k not in ('payload', 'params')})
    if body_in != P:
        for k in sorted(set(body_in) | set(P)):
            if body_in.get(k) != P.get(k):
                print('  DIFF', k, json.dumps(body_in.get(k), ensure_ascii=False)[:400], '!=', json.dumps(P.get(k), ensure_ascii=False)[:400])
    j = load_result(txt)
    if j is None:
        print('no result'); return
    if '_raw_text' in j:
        print('raw result:', j['_raw_text'][:1500]); return
    print('success:', j.get('success'), '| error:', json.dumps(j.get('error'), ensure_ascii=False)[:800])
    d = j.get('data') or {}
    if want_dry:
        req = ((d.get('data') or {}).get('request')) or {}
        body = req.get('body')
        print('dry path:', req.get('path'), '| body == payload:', body == P, '| warnings:', (d.get('meta') or {}).get('warnings') or d.get('warnings'))
        if body is not None and body != P:
            for k in sorted(set(body) | set(P)):
                if body.get(k) != P.get(k):
                    print('  BODY DIFF', k, json.dumps(body.get(k), ensure_ascii=False)[:600], '!=', json.dumps(P.get(k), ensure_ascii=False)[:600])
        print('dry keys:', list((d.get('data') or {}).keys()), json.dumps(d, ensure_ascii=False)[:300] if body is None else '')
    else:
        dd = d.get('data') or {}
        print('live code:', dd.get('code'), '| message:', dd.get('message'), '| request_id:', dd.get('request_id'))
        print('live data:', json.dumps(dd.get('data'), ensure_ascii=False)[:1500])


def verify(ad):
    u = units()[ad]; ch = u['changes'][0]; i = slot_index(ch['slot'])
    pb = json.load(open(W + 'payload_%s.json' % ad))
    pre = pb['pre_rec']
    lives = [f for f in update_calls(ad) if not bool(f[2].get('dry_run', True))]
    after = lives[-1][0] if lives else pb['pre_order']
    r = latest(ad, after_order=after)
    if not r:
        print('no complete read after the live call'); return
    rec = r['rec']
    url, missing, differ = eff_url(rec, i)
    ac_pre = dict(pre.get('ad_configuration') or {}); ac_post = dict(rec.get('ad_configuration') or {})
    up_post = ac_post.pop('utm_params', None); ac_pre.pop('utm_params', None)
    res = {'read_request_id': r['request_id'], 'after_live': url, 'equals_new_bytes': url == ch['new'],
           'utm_params_ok': (up_post is None and 'utm_params' not in (pre.get('ad_configuration') or {})) or
                            sorted((p['key'], p['value']) for p in (up_post or [])) == sorted((p['key'], p['value']) for p in new_utms(ch['new'])),
           'utm_id_present': any(p['key'] == 'utm_id' for p in (up_post or [])) or 'utm_id=' in url,
           'post_utm_params': up_post, 'missing_from_url': missing, 'differing': differ,
           'other_lp_entries_same': [x for k, x in enumerate(rec['landing_page_url_list']) if k != i] == [x for k, x in enumerate(pre['landing_page_url_list']) if k != i],
           'ad_configuration_other_same': ac_pre == ac_post,
           'creative_list_same': rec.get('creative_list') == pre.get('creative_list'),
           'ad_text_list_same': rec.get('ad_text_list') == pre.get('ad_text_list'),
           'ad_name_same': rec.get('ad_name') == pre.get('ad_name'),
           'operation_status': (pre.get('operation_status'), rec.get('operation_status')),
           'secondary_status': (pre.get('secondary_status'), rec.get('secondary_status')),
           'adgroup_same': rec.get('adgroup_id') == pre.get('adgroup_id'),
           'modify_time': (pre.get('modify_time'), rec.get('modify_time'))}
    if not res['ad_configuration_other_same']:
        res['ac_diff'] = {k: (ac_pre.get(k), ac_post.get(k)) for k in set(ac_pre) | set(ac_post) if ac_pre.get(k) != ac_post.get(k)}
    other = {k for k in set(pre) | set(rec) if k not in ('landing_page_url_list', 'ad_configuration', 'creative_list', 'ad_text_list', 'ad_name',
                                                          'operation_status', 'secondary_status', 'modify_time', 'adgroup_id')}
    res['other_fields_diff'] = {k: (pre.get(k), rec.get(k)) for k in other if pre.get(k) != rec.get(k)}
    print(json.dumps(res, ensure_ascii=False, indent=1))


def append(path):
    row = json.load(open(path))
    req = ['platform', 'account_id', 'unit_type', 'unit', 'ad_ids', 'ad_names', 'slot', 'before', 'after_expected', 'after_live', 'result', 'new_entity_ids', 'detail']
    miss = [k for k in req if k not in row]
    assert not miss, 'missing %r' % miss
    assert row['result'] in ('Fixed', 'AlreadyFixed', 'Failed', 'Skipped', 'NotAttempted')
    with open(OUT, 'a', encoding='utf-8') as f:
        f.write(json.dumps({k: row[k] for k in req}, ensure_ascii=False) + '\n')
    print('appended', row['unit'], row['result'])


def checkout():
    """read-only: validate every results line against the plan and this transcript"""
    U = units(); seen = set(); ok = True
    for n, line in enumerate(open(OUT, encoding='utf-8'), 1):
        row = json.loads(line)
        u = U.get(row['unit']); ch = [c for c in u['changes'] if c['slot'] == row['slot']][0]
        key = (row['unit'], row['slot'])
        errs = []
        if key in seen: errs.append('duplicate')
        seen.add(key)
        if row['after_expected'] != ch['new']: errs.append('after_expected != plan new')
        if row['account_id'] != u['account_id'] or row['ad_ids'] != u['ad_ids'] or row['ad_names'] != u['ad_names'] or row['unit_type'] != u['unit_type']:
            errs.append('unit fields differ from plan')
        i = slot_index(row['slot'])
        rs = reads().get(row['unit']) or []
        lives = [f for f in update_calls(row['unit']) if not bool(f[2].get('dry_run', True))]
        if lives:
            first_live = lives[0][0]
            pre = [r for r in rs if r['complete'] and r['order'] < first_live]
            post = [r for r in rs if r['complete'] and r['order'] > lives[-1][0]]
            if not pre or row['before'] != pre[-1]['rec']['landing_page_url_list'][i]['landing_page_url']: errs.append('before != pre-read')
            if not post or row['after_live'] != post[-1]['rec']['landing_page_url_list'][i]['landing_page_url']: errs.append('after_live != read-back')
            if row['result'] == 'Fixed' and row['after_live'] != ch['new']: errs.append('Fixed but after_live != new')
        else:
            lastr = [r for r in rs if r['complete']]
            if row['result'] in ('AlreadyFixed', 'Skipped', 'NotAttempted') and lastr:
                cur = lastr[-1]['rec']['landing_page_url_list'][i]['landing_page_url']
                if row['before'] != cur or row['after_live'] != cur: errs.append('before/after_live != cur')
            if row['result'] == 'Fixed': errs.append('Fixed without a live call')
        print(n, row['unit'], row['result'], 'OK' if not errs else errs)
        ok = ok and not errs
    missing = [(k, c['slot']) for k, u in U.items() for c in u['changes'] if (k, c['slot']) not in seen]
    print('all lines OK:', ok, '| changes without a line:', len(missing), missing[:20])


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'checkout':
        checkout(); sys.exit(0)
    if cmd == 'reads':
        rs = reads(); print({k: [(x['order'], x['request_id'], x['complete']) for x in v] for k, v in rs.items() if k in units()})
    elif cmd == 'classify':
        for ad in sys.argv[2:]:
            print(json.dumps(classify(ad), ensure_ascii=False, indent=1))
    elif cmd == 'build':
        print(json.dumps(build(sys.argv[2]), ensure_ascii=False, separators=(',', ':')))
    elif cmd == 'call':
        call(sys.argv[2], sys.argv[3])
    elif cmd == 'verify':
        verify(sys.argv[2])
    elif cmd == 'append':
        append(sys.argv[2])
