#!/usr/bin/env python3
"""apply7 in_tiktok_7 helper (Upgraded Smart+ ads only).

Read-only parsing of THIS agent's own transcript (the exact Whathead tool inputs and results) plus local plan files.
It makes NO API calls and changes nothing on any ad platform. The only file it appends to is this batch's results
file (out_tiktok_7.jsonl), and only in the 'append' subcommand.

usage:
  tt7.py reads                       list the smart_plus/ad/get reads found for this batch's ads
  tt7.py classify <ad>...            decide AlreadyFixed / Write / Skipped / Hold from the latest complete read
  tt7.py build <ad>                  build the smart_plus/ad/update payload from the latest complete read (payload_<ad>.json)
  tt7.py checkdry <ad>               compare my last dry_run:true call (input + preview body) with payload_<ad>.json and the pre-read
  tt7.py checklive <ad>              summarise my dry_run:false call(s) for <ad>: input == payload?, code, message, request_id
  tt7.py verify <ad>                 compare the latest complete read after the live call with "new" and the pre-read (verify_<ad>.json)
  tt7.py row <ad> <result> [note]    compose one result line from the files above (row_<ad>.json), print it
  tt7.py append <ad>                 append row_<ad>.json as one JSON line to the results file
  tt7.py checkout                    validate every results line against the plan and the transcript
"""
import json, sys, os, re, copy
from urllib.parse import urlsplit, parse_qsl

ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
INP = ROOT + '/apply7/in_tiktok_7.json'
OUT = ROOT + '/apply7/out_tiktok_7.jsonl'
W = ROOT + '/apply7/tt7_work/'
EXCL = ROOT + '/work/excl_platform_refused_v2.json'
T = '/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/wf_96598b86-20e/agent-a5c9f240aaf7c7994.jsonl'
SLOT_RE = re.compile(r'^smart_plus_ad\.landing_page_url_list\[(\d+)\]\.landing_page_url$')
GET_ACTIONS = ('tiktok_smart_plus_ad_get',)
UPD_ACTIONS = ('tiktok_smart_plus_ad_update',)


def units():
    return {u['unit']: u for u in json.load(open(INP, encoding='utf-8'))}


def excluded(ad, slot):
    ex = json.load(open(EXCL, encoding='utf-8'))
    return any(e.get('platform') == 'tiktok' and str(e.get('ad_id')) == str(ad) and e.get('slot') == slot for e in ex)


def qparams(u):
    return sorted(parse_qsl(urlsplit(u or '').query, keep_blank_values=True))


def parts(u):
    s = urlsplit(u or '')
    return (s.scheme, s.netloc, s.path, s.fragment, tuple(qparams(u)))


def slot_index(slot):
    m = SLOT_RE.match(slot)
    assert m, 'unexpected slot %r' % slot
    return int(m.group(1))


def utms_of(new):
    q = parse_qsl(urlsplit(new).query, keep_blank_values=True)
    assert len(set(k for k, _ in q)) == len(q), 'duplicate keys in new'
    assert all(k.startswith('utm_') for k, _ in q), 'non-utm key in new'
    assert not any(k == 'utm_id' for k, _ in q), 'utm_id in new'
    return [{'key': k, 'value': v} for k, v in q]


def eff_url(url, utm_params):
    """full landing URL incl. separately stored utm_params (keys missing from the URL are appended)"""
    url = url or ''
    have = dict(parse_qsl(urlsplit(url).query, keep_blank_values=True))
    extra, conflict = [], []
    for p in (utm_params or []):
        k, v = p.get('key'), p.get('value')
        if k in have:
            if have[k] != v:
                conflict.append((k, have[k], v))
        else:
            extra.append((k, v))
    eff = url
    if extra:
        eff = url + ('&' if '?' in url else '?') + '&'.join('%s=%s' % kv for kv in extra)
    return eff, extra, conflict


# ---------------------------------------------------------------- transcript parsing (read-only)
def transcript_calls():
    uses, order, res, err = {}, [], {}, {}
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
                uses[c['id']] = c.get('input') or {}
                order.append(c['id'])
            if c.get('type') == 'tool_result' and c.get('tool_use_id') in uses:
                cc = c.get('content')
                txt = ''.join(x.get('text', '') for x in cc if isinstance(x, dict)) if isinstance(cc, list) else str(cc)
                res[c['tool_use_id']] = txt
                err[c['tool_use_id']] = bool(c.get('is_error'))
    for i, tid in enumerate(order):
        yield i, tid, uses[tid], res.get(tid), err.get(tid)


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
                return json.loads(''.join(x.get('text', '') for x in j if isinstance(x, dict)))
            return j
        return {'_raw_text': txt}


def reads():
    out = {}
    for i, tid, inp, txt, iserr in transcript_calls():
        if inp.get('action') not in GET_ACTIONS:
            continue
        j = load_result(txt)
        if not j or '_raw_text' in j or not isinstance(j, dict):
            continue
        d = ((j.get('data') or {}).get('data') or {})
        if d.get('code') != 0:
            continue
        rid = d.get('request_id')
        lst = ((d.get('data') or {}).get('list')) or []
        trunc = 'truncated' in json.dumps((j.get('meta') or {}).get('mcp_output_budget') or {}) and \
            bool(((j.get('meta') or {}).get('mcp_output_budget') or {}).get('truncated'))
        projected = bool(inp.get('result_fields') or inp.get('fields') or inp.get('compact') or inp.get('max_items'))
        for r in lst:
            if not isinstance(r, dict) or 'smart_plus_ad_id' not in r:
                continue
            complete = ('__mcp_truncated_keys' not in json.dumps(r)) and not trunc and not projected
            out.setdefault(str(r['smart_plus_ad_id']), []).append(
                {'order': i, 'tool_use_id': tid, 'request_id': rid, 'complete': complete, 'rec': r})
    return out


def latest(ad, after_order=None, before_order=None):
    rs = [r for r in (reads().get(ad) or []) if r['complete']
          and (after_order is None or r['order'] > after_order) and (before_order is None or r['order'] < before_order)]
    return rs[-1] if rs else None


def update_calls(ad, dry):
    found = []
    for i, tid, inp, txt, iserr in transcript_calls():
        if inp.get('action') not in UPD_ACTIONS:
            continue
        body = inp.get('payload') or inp.get('params') or {}
        if str(body.get('smart_plus_ad_id')) != ad:
            continue
        if bool(inp.get('dry_run', True)) != dry:
            continue
        found.append((i, tid, inp, txt, iserr))
    return found


def bignums(o, path=''):
    out = []
    if isinstance(o, dict):
        for k, v in o.items():
            out += bignums(v, path + '.' + k)
    elif isinstance(o, list):
        for k, v in enumerate(o):
            out += bignums(v, path + '[%d]' % k)
    elif isinstance(o, (int, float)) and not isinstance(o, bool):
        out.append((path, o))
    return out


def materials(rec):
    out = []
    for c in rec.get('creative_list') or []:
        ci = c.get('creative_info') or {}
        out.append({'ad_material_id': c.get('ad_material_id'), 'ad_format': ci.get('ad_format'),
                    'identity_type': ci.get('identity_type'), 'identity_id': ci.get('identity_id'),
                    'bc': ci.get('identity_authorized_bc_id'), 'tiktok_item_id': ci.get('tiktok_item_id'),
                    'video_id': (ci.get('video_info') or {}).get('video_id'), 'n_images': len(ci.get('image_info') or []),
                    'status': c.get('material_operation_status')})
    return out


def classify(ad):
    u = units()[ad]
    r = latest(ad)
    if not r:
        return {'ad': ad, 'decision': 'NO_READ'}
    rec = r['rec']
    mats = materials(rec)
    ac = rec.get('ad_configuration') or {}
    spark = [m for m in mats if m['identity_type'] == 'BC_AUTH_TT' and m['tiktok_item_id']]
    if ac.get('identity_type') == 'BC_AUTH_TT' and ac.get('tiktok_item_id'):
        spark.append({'ad_configuration': True, 'tiktok_item_id': ac.get('tiktok_item_id')})
    out = []
    for ch in u['changes']:
        i = slot_index(ch['slot'])
        lpl = rec.get('landing_page_url_list') or []
        url = lpl[i].get('landing_page_url') if len(lpl) > i else None
        cur, extra, conflict = eff_url(url, ac.get('utm_params'))
        if excluded(ad, ch['slot']):
            d = ('Excluded', 'slot is on the platform-refused list')
        elif url is None:
            d = ('Skipped', 'slot missing: landing_page_url_list has %d entries' % len(lpl))
        elif conflict:
            d = ('Skipped', 'utm_params conflict with the URL: %r' % conflict)
        elif cur == ch['new']:
            d = ('AlreadyFixed', 'byte-identical')
        elif parts(cur) == parts(ch['new']):
            d = ('AlreadyFixed', 'same scheme/host/path/fragment and params, other order')
        elif cur == ch['now']:
            d = ('Write', 'cur == now (byte-identical)')
        elif cur in ch['alt_now']:
            d = ('Write', 'cur == alt_now[%d]' % ch['alt_now'].index(cur))
        elif parts(cur) == parts(ch['now']):
            d = ('Write', 'cur == now (same params, other order)')
        elif any(parts(cur) == parts(a) for a in ch['alt_now']):
            d = ('Write', 'cur == alt_now (same params, other order)')
        else:
            d = ('Skipped', 'changed since plan')
        if d[0] == 'Write' and spark:
            d = ('Hold', 'Spark item present: %r' % spark)
        out.append({'slot': ch['slot'], 'decision': d[0], 'why': d[1], 'url_field': url, 'cur': cur, 'n_lp': len(lpl),
                    'extra_utm': extra, 'conflict': conflict, 'utm_params': ac.get('utm_params'),
                    'has_utm_params': 'utm_params' in ac})
    return {'ad': ad, 'read_order': r['order'], 'request_id': r['request_id'], 'ad_name': rec.get('ad_name'),
            'plan_ad_name': u['ad_names'][0], 'advertiser_id': rec.get('advertiser_id'),
            'campaign_name': rec.get('campaign_name'), 'operation_status': rec.get('operation_status'),
            'secondary_status': rec.get('secondary_status'), 'modify_time': rec.get('modify_time'),
            'ac_keys': sorted(ac.keys()), 'ac_bignums': [b for b in bignums(ac) if abs(b[1]) > 2 ** 53],
            'pixel': (ac.get('tracking_info') or {}).get('tracking_pixel_id'), 'cta_id': ac.get('call_to_action_id'),
            'materials': mats, 'spark': spark, 'n_text': len(rec.get('ad_text_list') or []), 'changes': out}


def build(ad):
    u = units()[ad]
    assert len(u['changes']) == 1, 'multi-change unit: handle explicitly'
    ch = u['changes'][0]
    i = slot_index(ch['slot'])
    c = classify(ad)
    assert c['changes'][0]['decision'] == 'Write', 'not a Write decision: %r' % c['changes'][0]['decision']
    assert c['advertiser_id'] == u['account_id']
    r = latest(ad)
    rec = r['rec']
    lpl = copy.deepcopy(rec['landing_page_url_list'])
    lpl[i]['landing_page_url'] = ch['new']
    ac = copy.deepcopy(rec.get('ad_configuration') or {})
    if ac.get('utm_params'):
        ac['utm_params'] = utms_of(ch['new'])
    p = {'advertiser_id': u['account_id'], 'smart_plus_ad_id': ad, 'landing_page_url_list': lpl, 'ad_configuration': ac}
    big = [b for b in bignums(p) if abs(b[1]) > 2 ** 53]
    assert not big, 'numbers above 2^53 in payload (need exact strings): %r' % big
    json.dump({'payload': p, 'pre_request_id': r['request_id'], 'pre_order': r['order'], 'pre_rec': rec,
               'classify': c}, open(W + 'payload_%s.json' % ad, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return p


def body_vs_pre(body, pre, ch):
    """True if body differs from the pre-read only in landing_page_url_list[i].landing_page_url and ad_configuration.utm_params"""
    i = slot_index(ch['slot'])
    msgs = []
    if sorted(body) != ['ad_configuration', 'advertiser_id', 'landing_page_url_list', 'smart_plus_ad_id']:
        msgs.append('unexpected top-level keys %r' % sorted(body))
    acb = dict(body.get('ad_configuration') or {})
    aca = dict(pre.get('ad_configuration') or {})
    ub, ua = acb.pop('utm_params', None), aca.pop('utm_params', None)
    if acb != aca:
        msgs.append('ad_configuration differs beyond utm_params: %r' % {k: (aca.get(k), acb.get(k)) for k in set(aca) | set(acb) if aca.get(k) != acb.get(k)})
    if ua:
        if ub != utms_of(ch['new']):
            msgs.append('utm_params != UTMs of new: %r' % ub)
    elif ub != ua:
        msgs.append('utm_params changed although absent/empty in the read: %r -> %r' % (ua, ub))
    lb, la = body.get('landing_page_url_list') or [], pre.get('landing_page_url_list') or []
    if len(lb) != len(la):
        msgs.append('landing_page_url_list length differs')
    for j, (x, y) in enumerate(zip(lb, la)):
        x, y = dict(x), dict(y)
        if j == i:
            if x.get('landing_page_url') != ch['new']:
                msgs.append('landing_page_url_list[%d] != new' % j)
            x.pop('landing_page_url', None)
            y.pop('landing_page_url', None)
        if x != y:
            msgs.append('landing_page_url_list[%d] other keys differ' % j)
    if str(body.get('smart_plus_ad_id')) != str(pre.get('smart_plus_ad_id')):
        msgs.append('smart_plus_ad_id differs')
    if str(body.get('advertiser_id')) != str(pre.get('advertiser_id')):
        msgs.append('advertiser_id differs')
    return (not msgs), msgs


def checkdry(ad):
    pb = json.load(open(W + 'payload_%s.json' % ad, encoding='utf-8'))
    P, pre = pb['payload'], pb['pre_rec']
    ch = units()[ad]['changes'][0]
    found = update_calls(ad, dry=True)
    res = {'ad': ad, 'n_dry_calls': len(found)}
    if not found:
        res['error'] = 'no dry_run:true call found'
    else:
        i, tid, inp, txt, iserr = found[-1]
        body_in = inp.get('payload') or {}
        res['order'] = i
        res['input_equals_payload'] = body_in == P
        res['other_args'] = {k: v for k, v in inp.items() if k not in ('payload',)}
        j = load_result(txt)
        if not j or '_raw_text' in j:
            res['raw'] = (txt or '')[:1500]
        else:
            res['success'] = j.get('success')
            res['error'] = j.get('error')
            d = j.get('data') or {}
            req = ((d.get('data') or {}).get('request')) or {}
            body = req.get('body')
            res['dry_path'] = req.get('path')
            res['dry_method'] = req.get('method')
            res['preview_body_equals_payload'] = body == P
            if body is not None:
                ok, msgs = body_vs_pre(body, pre, ch)
                res['preview_vs_pre_only_url_and_utm'] = ok
                res['preview_vs_pre_msgs'] = msgs
            res['warnings'] = (d.get('meta') or {}).get('warnings') or d.get('warnings') or (j.get('meta') or {}).get('warnings')
    json.dump(res, open(W + 'dry_%s.json' % ad, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return res


def checklive(ad):
    P = json.load(open(W + 'payload_%s.json' % ad, encoding='utf-8'))['payload']
    out = []
    for i, tid, inp, txt, iserr in update_calls(ad, dry=False):
        r = {'order': i, 'input_equals_payload': (inp.get('payload') or {}) == P, 'is_error': iserr,
             'other_args': {k: v for k, v in inp.items() if k not in ('payload',)}}
        j = load_result(txt)
        if not j or '_raw_text' in j:
            r['raw'] = (txt or '')[:1500]
        else:
            r['success'] = j.get('success')
            r['error'] = j.get('error')
            dd = ((j.get('data') or {}).get('data')) or {}
            r['code'], r['message'], r['request_id'] = dd.get('code'), dd.get('message'), dd.get('request_id')
            r['data'] = json.dumps(dd.get('data'), ensure_ascii=False)[:600]
        out.append(r)
    json.dump(out, open(W + 'live_%s.json' % ad, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return out


def verify(ad):
    ch = units()[ad]['changes'][0]
    i = slot_index(ch['slot'])
    pb = json.load(open(W + 'payload_%s.json' % ad, encoding='utf-8'))
    pre = pb['pre_rec']
    lives = update_calls(ad, dry=False)
    after = lives[-1][0] if lives else pb['pre_order']
    r = latest(ad, after_order=after)
    if not r:
        return {'ad': ad, 'error': 'no complete read after the live call'}
    rec = r['rec']
    ac_post = dict(rec.get('ad_configuration') or {})
    ac_pre = dict(pre.get('ad_configuration') or {})
    up_post, up_pre = ac_post.pop('utm_params', None), ac_pre.pop('utm_params', None)
    url = rec['landing_page_url_list'][i]['landing_page_url'] if len(rec.get('landing_page_url_list') or []) > i else None
    eff, extra, conflict = eff_url(url, up_post)
    want_up = utms_of(ch['new']) if up_pre else up_pre
    res = {'ad': ad, 'read_request_id': r['request_id'], 'read_order': r['order'], 'after_live': url, 'after_eff': eff,
           'equals_new_bytes': url == ch['new'], 'eff_equals_new': eff == ch['new'],
           'had_utm_params': bool(up_pre),
           'utm_params_ok': (sorted((p['key'], p['value']) for p in (up_post or [])) == sorted((p['key'], p['value']) for p in (want_up or []))
                             and len(up_post or []) == len(want_up or [])),
           'utm_id_present': any(p.get('key') == 'utm_id' for p in (up_post or [])) or 'utm_id=' in (url or ''),
           'post_utm_params': up_post, 'extra': extra, 'conflict': conflict,
           'other_lp_entries_same': [x for k, x in enumerate(rec.get('landing_page_url_list') or []) if k != i] ==
                                    [x for k, x in enumerate(pre.get('landing_page_url_list') or []) if k != i],
           'lp_len_same': len(rec.get('landing_page_url_list') or []) == len(pre.get('landing_page_url_list') or []),
           'ad_configuration_other_same': ac_pre == ac_post,
           'creative_list_same': rec.get('creative_list') == pre.get('creative_list'),
           'creative_list_same_unordered': sorted(json.dumps(x, sort_keys=True, ensure_ascii=False) for x in (rec.get('creative_list') or [])) ==
                                           sorted(json.dumps(x, sort_keys=True, ensure_ascii=False) for x in (pre.get('creative_list') or [])),
           'ad_text_list_same': rec.get('ad_text_list') == pre.get('ad_text_list'),
           'ad_name_same': rec.get('ad_name') == pre.get('ad_name'),
           'operation_status': (pre.get('operation_status'), rec.get('operation_status')),
           'secondary_status': (pre.get('secondary_status'), rec.get('secondary_status')),
           'modify_time': (pre.get('modify_time'), rec.get('modify_time')),
           'items_before': [m['tiktok_item_id'] for m in materials(pre)],
           'items_after': [m['tiktok_item_id'] for m in materials(rec)]}
    if not res['ad_configuration_other_same']:
        res['ac_diff'] = {k: (ac_pre.get(k), ac_post.get(k)) for k in set(ac_pre) | set(ac_post) if ac_pre.get(k) != ac_post.get(k)}
    skip = ('landing_page_url_list', 'ad_configuration', 'creative_list', 'ad_text_list', 'ad_name', 'operation_status',
            'secondary_status', 'modify_time')
    res['other_fields_diff'] = {k: (pre.get(k), rec.get(k)) for k in set(pre) | set(rec) if k not in skip and pre.get(k) != rec.get(k)}
    res['all_other_unchanged'] = (res['other_lp_entries_same'] and res['lp_len_same'] and res['ad_configuration_other_same']
                                  and res['creative_list_same_unordered'] and res['ad_text_list_same'] and res['ad_name_same']
                                  and res['operation_status'][0] == res['operation_status'][1] and not res['other_fields_diff'])
    json.dump(res, open(W + 'verify_%s.json' % ad, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return res


def mat_text(mats):
    return '; '.join('material %s %s %s identity %s%s%s%s%s' % (
        m['ad_material_id'], m['ad_format'], m['identity_type'], m['identity_id'],
        (' / BC %s' % m['bc']) if m['bc'] else '',
        (' tiktok_item_id %s' % m['tiktok_item_id']) if m['tiktok_item_id'] else ' no tiktok_item_id',
        (' video %s' % m['video_id']) if m['video_id'] else '',
        (' %d image(s)' % m['n_images']) if m['n_images'] else '') for m in mats)


def row(ad, result, note=''):
    u = units()[ad]
    ch = u['changes'][0]
    base = {'platform': 'tiktok', 'account_id': u['account_id'], 'unit_type': u['unit_type'], 'unit': ad,
            'ad_ids': u['ad_ids'], 'ad_names': u['ad_names'], 'slot': ch['slot'], 'after_expected': ch['new'],
            'new_entity_ids': ''}
    if result in ('Fixed', 'Failed') and os.path.exists(W + 'payload_%s.json' % ad):
        pb = json.load(open(W + 'payload_%s.json' % ad, encoding='utf-8'))
        c = pb['classify']
        cc = c['changes'][0]
        dry = json.load(open(W + 'dry_%s.json' % ad, encoding='utf-8')) if os.path.exists(W + 'dry_%s.json' % ad) else {}
        lv = json.load(open(W + 'live_%s.json' % ad, encoding='utf-8')) if os.path.exists(W + 'live_%s.json' % ad) else []
        vf = json.load(open(W + 'verify_%s.json' % ad, encoding='utf-8')) if os.path.exists(W + 'verify_%s.json' % ad) else {}
        P = pb['payload']
        ub = [(p['key'], p['value']) for p in (cc['utm_params'] or [])]
        acs = [k for k in c['ac_keys'] if k != 'utm_params']
        live_txt = ' | '.join('attempt %d: %s' % (n + 1, ('code %s %s req %s' % (x.get('code'), x.get('message'), x.get('request_id')))
                                                  if 'code' in x else ('error %s' % (x.get('error') or x.get('raw')))) for n, x in enumerate(lv))
        detail = ('Upgraded Smart+ ad, %d material(s): %s. Pre-read smart_plus/ad/get req %s: landing_page_url_list[%d] %s; '
                  'ad_configuration.utm_params %s; tracking_pixel_id %s; call_to_action_id %s; operation_status %s, secondary_status %s, modify_time %s. '
                  'Dry run: call input == built payload %s, preview body == payload %s, preview vs live read differs only in the URL (+utm_params) %s '
                  '(smart_plus_ad_id + landing_page_url_list with only [%d].landing_page_url = new + ad_configuration as read (%s) with %s; '
                  'creative_list / ad_text_list / ad_name / status not sent). Live smart_plus/ad/update: %s. '
                  ) % (len(c['materials']), mat_text(c['materials']), pb['pre_request_id'], slot_index(ch['slot']), cc['why'],
                       ('had %d keys %s' % (len(ub), json.dumps(dict(ub), ensure_ascii=False))) if ub else ('absent' if not cc['has_utm_params'] else 'empty'),
                       json.dumps(c['pixel']), json.dumps(c['cta_id']), c['operation_status'], c['secondary_status'], c['modify_time'],
                       dry.get('input_equals_payload'), dry.get('preview_body_equals_payload'), dry.get('preview_vs_pre_only_url_and_utm'),
                       slot_index(ch['slot']), ', '.join(acs),
                       ('utm_params = the %d UTMs of new, no utm_id' % len(P['ad_configuration'].get('utm_params') or [])) if ub else 'utm_params left as read (none)',
                       live_txt or 'none')
        if vf and 'error' not in vf:
            detail += ('Read-back smart_plus/ad/get req %s: landing_page_url_list[%d] %s new byte for byte; utm_params %s%s; '
                       'other fields (ad_configuration, creative_list, ad_text_list, ad_name, other URL entries, adgroup, operation_status) unchanged: %s%s; '
                       'post ids before %s after %s; operation_status %s -> %s, secondary_status %s -> %s; modify_time %s -> %s.') % (
                vf['read_request_id'], slot_index(ch['slot']), '==' if vf['equals_new_bytes'] else '!=',
                (('%d keys matching new' % len(vf['post_utm_params'] or [])) if vf['had_utm_params'] else 'absent before and after (not added)')
                if vf['utm_params_ok'] else 'NOT as expected: %r' % vf['post_utm_params'],
                ' (utm_id present!)' if vf['utm_id_present'] else ', no utm_id',
                vf['all_other_unchanged'], '' if vf['all_other_unchanged'] else ' %r' % {k: vf.get(k) for k in ('ac_diff', 'other_fields_diff', 'creative_list_same', 'ad_text_list_same', 'ad_name_same')},
                vf['items_before'], vf['items_after'], vf['operation_status'][0], vf['operation_status'][1],
                vf['secondary_status'][0], vf['secondary_status'][1], vf['modify_time'][0], vf['modify_time'][1])
            if not vf.get('creative_list_same') and vf.get('creative_list_same_unordered'):
                detail += (' The read-back lists the same creative_list materials (identical content) in a different order than the pre-read;'
                           ' creative_list was not sent.')
            after_live = vf['after_live']
        else:
            after_live = cc['cur']
        if note:
            detail += ' ' + note
        ok = bool(vf) and 'error' not in vf and vf['equals_new_bytes'] and vf['eff_equals_new'] and vf['utm_params_ok'] and not vf['utm_id_present']
        if result == 'Fixed':
            assert ok, 'verify does not support Fixed'
        rowd = dict(base, before=cc['cur'], after_live=after_live, result=result, detail=detail)
    else:
        c = classify(ad)
        cc = c['changes'][0]
        detail = ('Upgraded Smart+ ad, %d material(s): %s. Read smart_plus/ad/get req %s: landing_page_url_list[%d] %s; '
                  'operation_status %s, secondary_status %s, modify_time %s.') % (
            len(c['materials']), mat_text(c['materials']), c['request_id'], slot_index(ch['slot']), cc['why'],
            c['operation_status'], c['secondary_status'], c['modify_time'])
        if result == 'Skipped':
            detail = 'changed since plan: %s. ' % cc['cur'] + detail
        if note:
            detail += ' ' + note
        rowd = dict(base, before=cc['cur'], after_live=cc['cur'], result=result, detail=detail)
    order = ['platform', 'account_id', 'unit_type', 'unit', 'ad_ids', 'ad_names', 'slot', 'before', 'after_expected',
             'after_live', 'result', 'new_entity_ids', 'detail']
    rowd = {k: rowd[k] for k in order}
    json.dump(rowd, open(W + 'row_%s.json' % ad, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return rowd


def append(ad):
    rowd = json.load(open(W + 'row_%s.json' % ad, encoding='utf-8'))
    assert rowd['result'] in ('Fixed', 'AlreadyFixed', 'Failed', 'Skipped', 'NotAttempted')
    done = set()
    if os.path.exists(OUT):
        for line in open(OUT, encoding='utf-8'):
            if line.strip():
                x = json.loads(line)
                done.add((x['unit'], x['slot']))
    assert (rowd['unit'], rowd['slot']) not in done, 'already has a line'
    with open(OUT, 'a', encoding='utf-8') as f:
        f.write(json.dumps(rowd, ensure_ascii=False) + '\n')
    return 'appended %s %s' % (rowd['unit'], rowd['result'])


def checkout():
    U = units()
    seen, ok = set(), True
    for n, line in enumerate(open(OUT, encoding='utf-8'), 1):
        if not line.strip():
            continue
        x = json.loads(line)
        u = U.get(x['unit'])
        errs = []
        if not u:
            errs.append('unit not in plan')
        else:
            ch = [c for c in u['changes'] if c['slot'] == x['slot']][0]
            if (x['unit'], x['slot']) in seen:
                errs.append('duplicate')
            seen.add((x['unit'], x['slot']))
            if x['after_expected'] != ch['new']:
                errs.append('after_expected != plan new')
            if x['account_id'] != u['account_id'] or x['ad_ids'] != u['ad_ids'] or x['ad_names'] != u['ad_names']:
                errs.append('unit fields differ')
            if x['result'] == 'Fixed' and x['after_live'] != ch['new']:
                errs.append('Fixed but after_live != new')
            lives = update_calls(x['unit'], dry=False)
            if x['result'] == 'Fixed' and not lives:
                errs.append('Fixed without a live call')
            if x['result'] in ('AlreadyFixed', 'Skipped', 'NotAttempted') and lives:
                errs.append('%s but a live call exists' % x['result'])
        print(n, x['unit'], x['result'], 'OK' if not errs else errs)
        ok = ok and not errs
    missing = [(k, c['slot']) for k, u in U.items() for c in u['changes'] if (k, c['slot']) not in seen]
    print('all lines OK:', ok, '| changes without a line:', len(missing), missing)


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'reads':
        rs = reads()
        U = units()
        print(json.dumps({k: [(x['order'], x['request_id'], x['complete']) for x in v] for k, v in rs.items() if k in U}, indent=0))
        print('my units without a complete read:', [k for k in U if not any(x['complete'] for x in rs.get(k, []))])
    elif cmd == 'classify':
        for ad in sys.argv[2:]:
            c = classify(ad)
            print(json.dumps(c, ensure_ascii=False))
    elif cmd == 'build':
        print(json.dumps(build(sys.argv[2]), ensure_ascii=False, separators=(',', ':')))
    elif cmd == 'checkdry':
        print(json.dumps(checkdry(sys.argv[2]), ensure_ascii=False, indent=1))
    elif cmd == 'checklive':
        print(json.dumps(checklive(sys.argv[2]), ensure_ascii=False, indent=1))
    elif cmd == 'verify':
        print(json.dumps(verify(sys.argv[2]), ensure_ascii=False, indent=1))
    elif cmd == 'row':
        print(json.dumps(row(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else ''), ensure_ascii=False, indent=1))
    elif cmd == 'append':
        print(append(sys.argv[2]))
    elif cmd == 'checkout':
        checkout()
    else:
        print(__doc__)
