#!/usr/bin/env python3
"""apply8 in_tiktok_2 helper (read-only analysis of THIS agent's own Whathead calls/results, so values are byte-exact).
usage:
  tt2.py reads                    -> list complete smart_plus reads per unit
  tt2.py prep <ad>                -> classify the latest complete read vs plan; print the update payload (compact JSON)
  tt2.py chk <ad> dry|live        -> check the last update call for <ad> of that kind: input == payload built from the pre-read; response
  tt2.py post <ad>                -> verify the latest complete read after the last live update call
  tt2.py summary                  -> one line per unit (state from transcript)
"""
import json, sys, os, re, copy, unicodedata
from urllib.parse import urlsplit, parse_qsl

ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
INP = ROOT + '/apply8/in_tiktok_2.json'
W = ROOT + '/apply8/work_tiktok_2/'
TR = '/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/wf_28f2cda9-d52/agent-a8665eeefd02ddb96.jsonl'
EXCL = ROOT + '/work/excl_platform_refused_v2.json'
SP_RE = re.compile(r'^smart_plus_ad\.landing_page_url_list\[(\d+)\]\.landing_page_url$')


def units():
    return {u['unit']: u for u in json.load(open(INP))}


def excluded(ad, slot):
    ex = json.load(open(EXCL))
    return any(e.get('platform') == 'tiktok' and str(e.get('ad_id')) == str(ad) and e.get('slot') == slot for e in ex)


def parts(u):
    s = urlsplit(u or '')
    return (s.scheme, s.netloc, s.path, s.fragment), sorted(parse_qsl(s.query, keep_blank_values=True))


def equiv(a, b):
    return parts(a) == parts(b)


def new_utms(new):
    q = parse_qsl(urlsplit(new).query, keep_blank_values=True)
    assert len(set(k for k, _ in q)) == len(q), 'duplicate keys in new'
    assert all(k.startswith('utm_') and k != 'utm_id' for k, _ in q), 'unexpected key in new %r' % q
    return [{'key': k, 'value': v} for k, v in q]


def eff(url, ups):
    """full landing URL incl. separately stored utm_params (keys missing from the URL are appended)"""
    url = url or ''
    have = dict(parse_qsl(urlsplit(url).query, keep_blank_values=True))
    extra = []; conflict = []
    for p in (ups or []):
        k, v = p['key'], p['value']
        if k in have:
            if have[k] != v:
                conflict.append((k, have[k], v))
        else:
            extra.append((k, v))
    e = url
    if extra:
        e = url + ('&' if '?' in url else '?') + '&'.join('%s=%s' % (k, v) for k, v in extra)
    return e, extra, conflict


# ---------------- transcript ----------------
def transcript_calls():
    uses = {}; order = []; res = {}
    for line in open(TR, encoding='utf-8'):
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
                    order.append(c['id'])
                uses[c['id']] = c.get('input') or {}
            if c.get('type') == 'tool_result' and c.get('tool_use_id') in uses:
                cc = c.get('content')
                txt = ''.join(x.get('text', '') for x in cc if isinstance(x, dict)) if isinstance(cc, list) else str(cc)
                res[c['tool_use_id']] = (txt, bool(c.get('is_error')))
    for i, tid in enumerate(order):
        r = res.get(tid)
        yield i, tid, uses[tid], (r[0] if r else None), (r[1] if r else None)


def load_result(txt):
    if txt is None:
        return None
    try:
        return json.loads(txt)
    except Exception:
        m = re.search(r'(/[^\s"\']+\.(?:txt|json))', txt)
        if m and os.path.exists(m.group(1)):
            raw = open(m.group(1), encoding='utf-8').read()
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
    for i, tid, inp, txt, iserr in transcript_calls():
        if inp.get('action') != 'tiktok_smart_plus_ad_get':
            continue
        j = load_result(txt)
        if not j or '_raw_text' in j or not j.get('success'):
            continue
        d = ((j.get('data') or {}).get('data') or {})
        if d.get('code') != 0:
            continue
        rid = d.get('request_id'); lst = ((d.get('data') or {}).get('list')) or []
        trunc = bool(((j.get('meta') or {}).get('mcp_output_budget') or {}).get('truncated'))
        projected = bool(inp.get('result_fields') or inp.get('fields') or inp.get('compact') or inp.get('max_items')
                         or ((inp.get('params') or {}).get('fields')))
        for r in lst:
            if not isinstance(r, dict):
                continue
            complete = ('__mcp_truncated' not in json.dumps(r)) and not trunc and not projected
            out.setdefault(str(r['smart_plus_ad_id']), []).append({'order': i, 'tool_use_id': tid, 'request_id': rid,
                                                                   'complete': complete, 'rec': r})
    return out


def latest(ad, after_order=None, before_order=None, R=None):
    rs = (R if R is not None else reads()).get(ad) or []
    rs = [r for r in rs if r['complete'] and (after_order is None or r['order'] > after_order)
          and (before_order is None or r['order'] < before_order)]
    return rs[-1] if rs else None


def update_calls(ad):
    out = []
    for i, tid, inp, txt, iserr in transcript_calls():
        if inp.get('action') != 'tiktok_smart_plus_ad_update':
            continue
        p = inp.get('payload') or {}
        if str(p.get('smart_plus_ad_id')) != ad:
            continue
        out.append({'order': i, 'tool_use_id': tid, 'input': inp, 'txt': txt, 'is_error': iserr,
                    'dry': inp.get('dry_run', True) is not False})
    return out


# ---------------- classification ----------------
def materials(rec):
    out = []
    for c in rec.get('creative_list') or []:
        ci = c.get('creative_info') or {}
        out.append({'ad_material_id': c.get('ad_material_id'), 'fmt': ci.get('ad_format'),
                    'identity_type': ci.get('identity_type'), 'identity_id': ci.get('identity_id'),
                    'item': ci.get('tiktok_item_id'), 'video': (ci.get('video_info') or {}).get('video_id'),
                    'status': c.get('material_operation_status')})
    return out


def classify(ad, rd):
    u = units()[ad]
    assert len(u['changes']) == 1, 'multi-change unit'
    ch = u['changes'][0]
    rec = rd['rec']
    m = SP_RE.match(ch['slot'])
    assert m, 'unexpected slot %r' % ch['slot']
    i = int(m.group(1))
    lpl = rec.get('landing_page_url_list') or []
    url = lpl[i].get('landing_page_url') if len(lpl) > i else None
    ac = rec.get('ad_configuration') or {}
    ups = ac.get('utm_params')
    cur, extra, conflict = eff(url, ups)
    mats = materials(rec)
    spark_push = [x for x in mats if x['identity_type'] == 'BC_AUTH_TT' and x['item']]
    if excluded(ad, ch['slot']):
        decision = 'EXCLUDED'
    elif spark_push:
        decision = 'HOLD_SPARK_PUSH'
    elif conflict:
        decision = 'CONFLICT'
    elif equiv(cur, ch['new']):
        decision = 'AlreadyFixed'
    elif cur == ch['now'] or cur in ch['alt_now']:
        decision = 'Write'
    else:
        decision = 'Skipped'
    return {'ad': ad, 'request_id': rd['request_id'], 'order': rd['order'], 'decision': decision,
            'match': 'now' if cur == ch['now'] else ('alt_now' if cur in ch['alt_now'] else ('new' if equiv(cur, ch['new']) else '-')),
            'cur': cur, 'url_field': url, 'utm_params': ups, 'utm_extra': extra, 'utm_conflict': conflict,
            'slot_index': i, 'n_lp': len(lpl), 'ad_name': rec.get('ad_name'), 'ad_name_matches_plan': rec.get('ad_name') in u['ad_names'],
            'advertiser_ok': str(rec.get('advertiser_id')) == u['account_id'],
            'op': rec.get('operation_status'), 'sec': rec.get('secondary_status'), 'modify_time': rec.get('modify_time'),
            'adgroup_id': rec.get('adgroup_id'), 'materials': mats, 'ac_keys': sorted(ac.keys())}


def build(ad, rd):
    u = units()[ad]; ch = u['changes'][0]
    rec = rd['rec']
    i = int(SP_RE.match(ch['slot']).group(1))
    lpl = copy.deepcopy(rec.get('landing_page_url_list') or [])
    lpl[i]['landing_page_url'] = ch['new']
    p = {'advertiser_id': u['account_id'], 'smart_plus_ad_id': ad, 'landing_page_url_list': lpl}
    ac = copy.deepcopy(rec.get('ad_configuration'))
    if ac is not None:
        if 'utm_params' in ac:
            ac['utm_params'] = new_utms(ch['new'])
        p['ad_configuration'] = ac
    return p


def compact(o):
    return json.dumps(o, ensure_ascii=False, separators=(',', ':'))


def pre_read_for(ad, before_order):
    return latest(ad, before_order=before_order)


def resp_summary(txt):
    j = load_result(txt)
    if j is None:
        return {'raw': None}
    if '_raw_text' in j:
        return {'raw': j['_raw_text'][:1500]}
    out = {'success': j.get('success')}
    d = j.get('data') or {}
    if not j.get('success'):
        out['error'] = j.get('error') or d
        return out
    out['dryRun'] = d.get('dryRun')
    dd = d.get('data') or {}
    if d.get('dryRun'):
        req = dd.get('request') or {}
        out['preview_body'] = req.get('body'); out['warnings'] = dd.get('warnings'); out['preflightBlocking'] = dd.get('preflightBlocking')
        out['path'] = req.get('path')
    else:
        out['code'] = dd.get('code'); out['message'] = dd.get('message'); out['request_id'] = dd.get('request_id'); out['data'] = dd.get('data')
        out['meta'] = d.get('meta')
    return out


def cmd_prep(ad):
    R = reads(); rd = latest(ad, R=R)
    if not rd:
        print(json.dumps({'ad': ad, 'decision': 'NO_READ'})); return
    c = classify(ad, rd)
    print(json.dumps(c, ensure_ascii=False, indent=1))
    if c['decision'] == 'Write':
        p = build(ad, rd)
        json.dump({'pre_read_order': rd['order'], 'pre_read_request_id': rd['request_id'], 'payload': p},
                  open(W + 'payload_%s.json' % ad, 'w'), ensure_ascii=False, indent=1)
        print('PAYLOAD:')
        print(compact(p))


def cmd_chk(ad, kind):
    calls = [c for c in update_calls(ad) if c['dry'] == (kind == 'dry')]
    if not calls:
        print('no %s call for %s' % (kind, ad)); return
    c = calls[-1]
    rd = pre_read_for(ad, c['order'])
    built = build(ad, rd)
    inp = c['input']
    ok_payload = inp.get('payload') == built
    print(json.dumps({'call_order': c['order'], 'pre_read_order': rd['order'], 'pre_read_request_id': rd['request_id'],
                      'input_payload_equals_built': ok_payload, 'dry_run_flag': inp.get('dry_run'),
                      'other_input_keys': sorted(k for k in inp if k not in ('payload',)),
                      'is_error': c['is_error']}, ensure_ascii=False))
    if not ok_payload:
        print('INPUT:', compact(inp.get('payload'))); print('BUILT:', compact(built))
    s = resp_summary(c['txt'])
    if kind == 'dry' and s.get('preview_body') is not None:
        print('preview_body_equals_payload:', s['preview_body'] == built, '| warnings:', s.get('warnings'),
              '| preflightBlocking:', s.get('preflightBlocking'), '| path:', s.get('path'))
        if s['preview_body'] != built:
            print('PREVIEW:', compact(s['preview_body']))
    else:
        print(json.dumps(s, ensure_ascii=False)[:3000])


def diff_fields(a, b, prefix=''):
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            out += diff_fields(a.get(k, '<absent>'), b.get(k, '<absent>'), prefix + '.' + k if prefix else k)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            out += diff_fields(x, y, '%s[%d]' % (prefix, i))
    elif a != b:
        out.append((prefix, a, b))
    return out


def cmd_post(ad):
    u = units()[ad]; ch = u['changes'][0]
    calls = [c for c in update_calls(ad) if not c['dry']]
    if not calls:
        print('no live call for', ad); return
    lc = calls[-1]
    pre = pre_read_for(ad, calls[0]['order'])
    R = reads()
    post = latest(ad, after_order=lc['order'], R=R)
    if not post:
        print('no read after live call'); return
    i = int(SP_RE.match(ch['slot']).group(1))
    rec = post['rec']
    url = (rec.get('landing_page_url_list') or [])[i].get('landing_page_url')
    ups = (rec.get('ad_configuration') or {}).get('utm_params')
    cur, extra, conflict = eff(url, ups)
    def norm(r):
        r = copy.deepcopy(r)
        r['creative_list'] = sorted(r.get('creative_list') or [], key=lambda c: str(c.get('ad_material_id')))
        return r
    d = diff_fields(norm(pre['rec']), norm(rec))
    other = [x for x in d if x[0] not in ('modify_time',) and not x[0].startswith('landing_page_url_list[%d].landing_page_url' % i)
             and not x[0].startswith('ad_configuration.utm_params')]
    pre_items = [m['item'] for m in materials(pre['rec'])]; post_items = [m['item'] for m in materials(rec)]
    out = {'post_read_order': post['order'], 'post_read_request_id': post['request_id'],
           'url_field_equals_new_bytes': url == ch['new'], 'eff_equals_new_bytes': cur == ch['new'],
           'utm_params_after': ups, 'utm_params_match_new': (ups is None) or (ups == new_utms(ch['new'])),
           'utm_extra': extra, 'utm_conflict': conflict,
           'items_before': pre_items, 'items_after': post_items,
           'other_changes': other, 'op_sec': [rec.get('operation_status'), rec.get('secondary_status')],
           'modify_time': [pre['rec'].get('modify_time'), rec.get('modify_time')],
           'pre_read_request_id': pre['request_id'], 'n_live_calls': len(calls)}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print('AFTER_LIVE:', cur)


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'reads':
        for k, v in reads().items():
            print(k, [(x['order'], x['request_id'], x['complete']) for x in v])
    elif a[0] == 'prep':
        for ad in a[1:]:
            cmd_prep(ad)
    elif a[0] == 'chk':
        cmd_chk(a[1], a[2])
    elif a[0] == 'post':
        cmd_post(a[1])
