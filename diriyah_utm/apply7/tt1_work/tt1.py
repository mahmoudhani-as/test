#!/usr/bin/env python3
"""apply7 in_tiktok_1 helper. Reads Whathead tool calls/results from this agent's own transcript so payloads are byte-exact.
usage:
  tt1.py reads                      -> parse every tiktok_ad_get result in the transcript, save reads.json (ad_id -> list of reads)
  tt1.py classify <ad_id>...        -> classify latest complete read vs plan
  tt1.py build <ad_id>              -> build ad/update payload from latest complete read (prints safe JSON)
  tt1.py call <ad_id> dry|live      -> check last ad/update call for ad_id equals built payload, show response summary
  tt1.py verify <ad_id>             -> compare latest read after the live call with the read used for build
  tt1.py append <row.json>          -> append one result line
"""
import json, sys, os, unicodedata, re
from urllib.parse import urlsplit, parse_qsl
ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
INP = ROOT + '/apply7/in_tiktok_1.json'
OUT = ROOT + '/apply7/out_tiktok_1.jsonl'
W = ROOT + '/apply7/tt1_work/'
T = '/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/wf_96598b86-20e/agent-a5ce28750ccc2448c.jsonl'
# raw pixel/list text (req 20261012221203344C11081568B883AF61 and 8 other reads): 7347671240183693330 'Visit Diriyah - Base Pixel', 7610705877289091089 'Visit Diriyah - Restaurants'
PIX = {7347671240183693000: '7347671240183693330', 7610705877289091000: '7610705877289091089'}
EXCL = ROOT + '/work/excl_platform_refused_v2.json'


def units():
    return {u['unit']: u for u in json.load(open(INP))}


def qs(u):
    return sorted(parse_qsl(urlsplit(u).query, keep_blank_values=True))


def norm(u):
    s = urlsplit((u or '').strip())
    return (s.scheme, s.netloc.lower(), s.path, s.fragment, tuple(qs(u)))


def transcript_calls():
    """yield (order, tool_use_id, tool_use_input, result_text) for tiktok_native_action calls"""
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
        return None


def reads():
    out = {}
    for i, tid, inp, txt in transcript_calls():
        if inp.get('action') != 'tiktok_ad_get':
            continue
        j = load_result(txt)
        if not j:
            continue
        d = (((j.get('data') or {}).get('data') or {}))
        rid = d.get('request_id'); lst = ((d.get('data') or {}).get('list')) or []
        trunc_budget = bool(((j.get('meta') or {}).get('mcp_output_budget') or {}).get('truncated'))
        projected = bool(inp.get('result_fields') or inp.get('fields') or inp.get('compact') or inp.get('max_items'))
        trunc_budget = trunc_budget or projected or bool(((d.get('meta') or {}).get('mcp_output_budget') or {}).get('truncated'))
        for r in lst:
            if not isinstance(r, dict):
                continue
            complete = ('__mcp_truncated_keys' not in r) and not trunc_budget
            out.setdefault(r['ad_id'], []).append({'order': i, 'tool_use_id': tid, 'request_id': rid, 'complete': complete, 'rec': r})
    json.dump(out, open(W + 'reads.json', 'w'), ensure_ascii=False, indent=1)
    return out


def latest(ad, complete=True, after_order=None):
    rs = reads().get(ad) or []
    rs = [r for r in rs if (r['complete'] or not complete) and (after_order is None or r['order'] > after_order)]
    return rs[-1] if rs else None


def effective_url(rec):
    """landing_page_url plus separately stored utm_params (keys missing from the URL would be appended; differing values flagged)."""
    url = rec.get('landing_page_url') or ''
    have = dict(parse_qsl(urlsplit(url).query, keep_blank_values=True))
    have_raw = dict(p.split('=', 1) if '=' in p else (p, '') for p in urlsplit(url).query.split('&') if p)
    missing = [(p['key'], p['value']) for p in (rec.get('utm_params') or []) if p['key'] not in have]
    differ = [(p['key'], p['value'], have_raw.get(p['key'])) for p in (rec.get('utm_params') or [])
              if p['key'] in have and p['value'] != have_raw.get(p['key']) and p['value'] != have.get(p['key'])]
    eff = url
    if missing:
        eff = url + ('&' if urlsplit(url).query else ('?' if '?' not in url else '')) + '&'.join('%s=%s' % kv for kv in missing)
    return eff, missing, differ


def excluded(ad, slot):
    return any(e['platform'] == 'tiktok' and str(e.get('ad_id')) == ad and e.get('slot') == slot for e in json.load(open(EXCL)))


def classify(ad):
    u = units()[ad]; ch = u['changes'][0]
    r = latest(ad)
    if r is None:
        return {'ad': ad, 'class': ('NoRead', '')}
    rec = r['rec']
    url, missing, differ = effective_url(rec)
    kind = rec.get('identity_type')
    spark_push = (kind == 'BC_AUTH_TT' and bool(rec.get('tiktok_item_id')))
    if url == ch['new']:
        c = ('AlreadyFixed', 'exact')
    elif norm(url) == norm(ch['new']):
        c = ('AlreadyFixed', 'same params, other order')
    elif url == ch['now']:
        c = ('write', 'now (exact)')
    elif url in (ch.get('alt_now') or []):
        c = ('write', 'alt_now[%d] (exact)' % (ch['alt_now'].index(url)))
    elif norm(url) == norm(ch['now']):
        c = ('write', 'now (same params, other order)')
    elif any(norm(url) == norm(a) for a in (ch.get('alt_now') or [])):
        c = ('write', 'alt_now (same params, other order)')
    else:
        c = ('Skipped', 'changed since plan')
    if differ:
        c = (c[0] + '?', c[1] + ' | utm_params differ from URL: %r' % (differ,))
    return {'ad': ad, 'read_req': r['request_id'], 'class': c, 'identity_type': kind, 'tiktok_item_id': rec.get('tiktok_item_id'),
            'spark_push': spark_push, 'excluded': excluded(ad, ch['slot']), 'cur': url, 'raw_url': rec.get('landing_page_url'),
            'utm_params_missing_from_url': missing, 'utm_params_differing': differ, 'utm_params': rec.get('utm_params'),
            'modify_time': rec.get('modify_time'), 'status': [rec.get('operation_status'), rec.get('secondary_status')],
            'adgroup_id': rec.get('adgroup_id'), 'cta': [rec.get('call_to_action'), rec.get('call_to_action_id')],
            'pixel': rec.get('tracking_pixel_id'), 'format': [rec.get('ad_format'), rec.get('campaign_automation_type'), rec.get('is_aco')],
            'name_ok': rec.get('ad_name') == u['ad_names'][0],
            'ad_text_trailing_ws': (rec.get('ad_text') or '') != (rec.get('ad_text') or '').rstrip()}


READONLY = {'advertiser_id', 'campaign_id', 'campaign_name', 'adgroup_id', 'adgroup_name', 'create_time', 'modify_time', 'operation_status',
            'secondary_status', 'is_new_structure', 'is_aco', 'campaign_automation_type', 'optimization_event', 'profile_image_url',
            'ad_ref_pixel_id', 'branded_content_disabled', 'landing_page_urls', 'carousel_image_labels'}
SEND_CU = ['ad_id', 'ad_name', 'identity_id', 'identity_type', 'ad_format', 'video_id', 'image_ids', 'ad_text', 'call_to_action', 'call_to_action_id',
           'landing_page_url', 'utm_params', 'tracking_pixel_id', 'display_name', 'avatar_icon_web_uri', 'aigc_disclosure_type', 'creative_authorized', 'vast_moat_enabled']
MUST_EMPTY = {'card_id': (None, ''), 'page_id': (None, ''), 'music_id': (None, ''), 'impression_tracking_url': (None, ''), 'click_tracking_url': (None, ''),
              'creative_type': (None, ''), 'ad_texts': (None, '', []), 'viewability_vast_url': (None, ''), 'brand_safety_vast_url': (None, ''),
              'deeplink': (None, ''), 'playable_url': (None, ''), 'viewability_postbid_partner': (None, 'UNSET'), 'brand_safety_postbid_partner': (None, 'UNSET'),
              'deeplink_type': (None, 'NORMAL'), 'vertical_video_strategy': (None, 'UNSET'), 'fallback_type': (None, 'UNSET'), 'dynamic_destination': (None, 'UNSET'),
              'shopping_ads_fallback_type': (None, 'DEFAULT'), 'tiktok_item_id': (None, ''), 'app_name': (None, ''), 'identity_authorized_bc_id': (None, ''),
              'dark_post_status': (None,), 'promotional_music_disabled': (None,), 'tracking_app_id': (None, ''), 'tracking_offline_event_set_ids': (None, []),
              'creative_auto_enhancement_strategy_list': (None, []), 'disclaimer_type': (None, ''), 'cpp_url': (None, ''), 'video_view_tracking_url': (None, ''),
              'product_specific_type': (None, ''), 'item_group_ids': (None, []), 'sku_ids': (None, []), 'product_set_id': (None, ''), 'shopping_ads_video_package_id': (None, ''),
              'shopping_ads_deeplink_type': (None, ''), 'deeplink_utm_params': (None, []), 'end_card_cta': (None, ''), 'dynamic_format': (None, 'UNSET', ''),
              'instant_product_page_used': (None, False), 'page_image_index': (None,), 'carousel_image_index': (None,), 'item_duet_status': (None,), 'item_stitch_status': (None,)}


def new_utms(new):
    q = urlsplit(new).query
    raw = [p.split('=', 1) for p in q.split('&') if p]
    assert all(len(kv) == 2 for kv in raw)
    dec = parse_qsl(q, keep_blank_values=True)
    assert [tuple(kv) for kv in raw] == list(dec), 'new URL has encoded values; decide raw vs decoded'
    return [{'key': k, 'value': v} for k, v in raw]


def build(ad):
    u = units()[ad]; ch = u['changes'][0]
    r = latest(ad); a = r['rec']
    assert ch['slot'] == 'ad.landing_page_url' and len(u['changes']) == 1
    new = ch['new']; q = parse_qsl(urlsplit(new).query, keep_blank_values=True)
    assert all(k.startswith('utm_') and k != 'utm_id' for k, v in q) and len({k for k, v in q}) == len(q), q
    assert a['ad_id'] == ad and a['advertiser_id'] == u['account_id'] and a['ad_name'] == u['ad_names'][0]
    assert a['identity_type'] == 'CUSTOMIZED_USER', 'only CUSTOMIZED_USER handled by this builder'
    assert not a.get('tiktok_item_id')
    assert a['campaign_automation_type'] == 'MANUAL' and a['is_aco'] is False and a['ad_format'] == 'SINGLE_VIDEO'
    assert a['video_id'] and a['image_ids']
    unknown = []
    for k, v in a.items():
        if k in READONLY or k in SEND_CU or k == '__mcp_truncated_keys':
            continue
        if k in MUST_EMPTY:
            assert v in MUST_EMPTY[k], (ad, k, v)
            continue
        unknown.append((k, v))
    assert not unknown, ('unhandled fields', unknown)
    cr = {}
    for k in SEND_CU:
        if k == 'landing_page_url':
            cr[k] = new; continue
        if k == 'utm_params':
            if a.get('utm_params') is not None:
                cr[k] = new_utms(new)
            continue
        if k == 'tracking_pixel_id':
            tp = a.get('tracking_pixel_id')
            if tp not in (0, None, ''):
                cr[k] = PIX[tp]
            continue
        if k == 'call_to_action' and a.get('call_to_action_id'):
            continue   # CTA portfolio wins; send id only (as read)
        if k == 'call_to_action_id' and not a.get('call_to_action_id'):
            continue
        if k == 'call_to_action' and not a.get('call_to_action'):
            continue
        if k in a and a[k] is not None:
            cr[k] = a[k]
    p = {'advertiser_id': u['account_id'], 'adgroup_id': a['adgroup_id'], 'creatives': [cr]}
    c = classify(ad)
    assert c['class'][0] == 'write' and not c['spark_push'] and not c['excluded'] and c['read_req'] == r['request_id'], c
    json.dump({'payload': p, 'pre_read': r['request_id'], 'pre_order': r['order'], 'pre_rec': a, 'pre_class': c['class'][1], 'pre_cur': c['cur']},
              open(W + 'payload_%s.json' % ad, 'w'), ensure_ascii=False, indent=1)
    return p


def safe_dumps(o):
    s = json.dumps(o, ensure_ascii=False); out = []
    for c in s:
        cat = unicodedata.category(c)
        if ord(c) > 0xFFFF:
            v = ord(c) - 0x10000; out.append('\\u%04x\\u%04x' % (0xD800 + (v >> 10), 0xDC00 + (v & 0x3FF)))
        elif ord(c) > 127 and (cat in ('Cf', 'Cc', 'Zs', 'Mn', 'Me', 'Co', 'Cs', 'So', 'Sk') or not cat.startswith('L')):
            out.append('\\u%04x' % ord(c))
        else:
            out.append(c)
    t = ''.join(out); assert json.loads(t) == o
    return t


def call(ad, mode):
    want_dry = (mode == 'dry')
    P = json.load(open(W + 'payload_%s.json' % ad))['payload']
    found = []
    for i, tid, inp, txt in transcript_calls():
        if inp.get('action') != 'tiktok_ad_update':
            continue
        pl = inp.get('payload') or {}
        crs = pl.get('creatives') or []
        if crs and crs[0].get('ad_id') == ad and bool(inp.get('dry_run', True)) == want_dry:
            found.append((i, tid, inp, txt))
    if not found:
        print('no matching call'); return
    i, tid, inp, txt = found[-1]
    print('calls found:', len(found), 'order', i, 'payload_equal:', inp.get('payload') == P, 'dry_run:', inp.get('dry_run'),
          'other args:', {k: v for k, v in inp.items() if k not in ('payload',)})
    if inp.get('payload') != P:
        a = inp.get('payload') or {}
        for k in set(P) | set(a):
            if k != 'creatives' and P.get(k) != a.get(k):
                print('DIFF top', k, P.get(k), a.get(k))
        for k in set(P['creatives'][0]) | set((a.get('creatives') or [{}])[0]):
            if P['creatives'][0].get(k) != a['creatives'][0].get(k):
                print('DIFF', k, repr(P['creatives'][0].get(k))[:300], '!=', repr(a['creatives'][0].get(k))[:300])
    if txt is None:
        print('no result yet'); return
    open(W + 'resp_%s_%s.json' % (mode, ad), 'w', encoding='utf-8').write(txt)
    j = load_result(txt)
    if j is None:
        print('RAW:', txt[:2000]); return
    d = (j.get('data') or {}).get('data') or {}
    if want_dry:
        body = ((d.get('request') or {}).get('body'))
        print('dry body == payload:', body == P, '| warnings:', d.get('warnings'), 'preflightBlocking:', d.get('preflightBlocking'),
              '| path:', (d.get('request') or {}).get('path'))
        if body != P:
            print(json.dumps(body, ensure_ascii=False)[:3000])
            for k in set(P['creatives'][0]) | set(((body or {}).get('creatives') or [{}])[0]):
                if P['creatives'][0].get(k) != body['creatives'][0].get(k):
                    print('BODY DIFF', k, repr(P['creatives'][0].get(k))[:300], '!=', repr(body['creatives'][0].get(k))[:300])
    else:
        print('success:', j.get('success'), 'code:', d.get('code'), 'message:', d.get('message'), 'request_id:', d.get('request_id'))
        dd = d.get('data') or {}
        print('ad_ids:', dd.get('ad_ids'), 'need_audit:', dd.get('need_audit'))
        for c in dd.get('creatives') or []:
            print('resp landing_page_url == new:', c.get('landing_page_url') == P['creatives'][0]['landing_page_url'], '| modify_time', c.get('modify_time'),
                  '| utm', c.get('utm_params'))
        if not j.get('success'):
            print('ERR', json.dumps(j, ensure_ascii=False)[:2000])


def verify(ad):
    u = units()[ad]; ch = u['changes'][0]
    pb = json.load(open(W + 'payload_%s.json' % ad))
    rs = reads().get(ad) or []
    pre = [r for r in rs if r['request_id'] == pb['pre_read']][-1]
    live_orders = [i for i, tid, inp, txt in transcript_calls() if inp.get('action') == 'tiktok_ad_update' and inp.get('dry_run') is False
                   and ((inp.get('payload') or {}).get('creatives') or [{}])[0].get('ad_id') == ad]
    last_live = max(live_orders) if live_orders else pb['pre_order']
    post = [r for r in rs if r['order'] > last_live and r['complete']]
    if not post:
        print('no post read'); return
    post = post[-1]
    a, b = pre['rec'], post['rec']
    eff = effective_url(b)
    out = {'post_read': post['request_id'], 'url_equal_new_bytes': b.get('landing_page_url') == ch['new'], 'after_live': b.get('landing_page_url'),
           'effective_after': eff[0], 'effective_equal_new_bytes': eff[0] == ch['new'],
           'utm_params_ok': sorted((p['key'], p['value']) for p in (b.get('utm_params') or [])) == sorted((p['key'], p['value']) for p in new_utms(ch['new'])),
           'utm_id_present': any(p['key'] == 'utm_id' for p in (b.get('utm_params') or [])) or 'utm_id=' in (b.get('landing_page_url') or ''),
           'post_utm_params': b.get('utm_params'), 'missing_differ': eff[1:]}
    diffs = {}
    for k in sorted(set(a) | set(b)):
        if k in ('landing_page_url', 'utm_params', 'modify_time'):
            continue
        if a.get(k) != b.get(k):
            diffs[k] = [a.get(k), b.get(k)]
    out['other_diffs'] = diffs
    out['modify_time'] = [a.get('modify_time'), b.get('modify_time')]
    out['status'] = [b.get('operation_status'), b.get('secondary_status')]
    print(json.dumps(out, ensure_ascii=False, indent=1))
    json.dump(out, open(W + 'verify_%s.json' % ad, 'w'), ensure_ascii=False, indent=1)


def append(row):
    u = units()[row['unit']]
    base = {'platform': 'tiktok', 'account_id': u['account_id'], 'unit_type': u['unit_type'], 'unit': u['unit'], 'ad_ids': u['ad_ids'],
            'ad_names': u['ad_names'], 'slot': u['changes'][0]['slot'], 'after_expected': u['changes'][0]['new'], 'new_entity_ids': ''}
    base.update(row)
    keys = ['platform', 'account_id', 'unit_type', 'unit', 'ad_ids', 'ad_names', 'slot', 'before', 'after_expected', 'after_live', 'result', 'new_entity_ids', 'detail']
    line = {k: base.get(k, '') for k in keys}
    assert line['result'] in ('Fixed', 'AlreadyFixed', 'Failed', 'Skipped', 'NotAttempted')
    if line['result'] == 'Fixed':
        assert line['after_live'] == line['after_expected']
    target = W + 'pending.jsonl' if os.environ.get('TT1_PENDING') else OUT
    with open(target, 'a', encoding='utf-8') as f:
        f.write(json.dumps(line, ensure_ascii=False) + '\n')
    print('appended', line['unit'], line['result'], '->', os.path.basename(target))


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'reads':
        r = reads()
        for k, v in r.items():
            print(k, [(x['request_id'], x['complete']) for x in v])
    elif cmd == 'classify':
        for ad in sys.argv[2:]:
            print(json.dumps(classify(ad), ensure_ascii=False))
    elif cmd == 'build':
        p = build(sys.argv[2]); print(safe_dumps(p))
    elif cmd == 'call':
        call(sys.argv[2], sys.argv[3])
    elif cmd == 'verify':
        verify(sys.argv[2])
    elif cmd == 'append':
        append(json.load(open(sys.argv[2])))
    elif cmd == 'finish':
        # finish <ad> [extra-detail]: check last live call + read-back, append Fixed (or Failed) with a standard detail
        ad = sys.argv[2]; extra = sys.argv[3] if len(sys.argv) > 3 else ''
        u = units()[ad]; ch = u['changes'][0]
        pb = json.load(open(W + 'payload_%s.json' % ad))
        P = pb['payload']
        lives = [(i, inp, txt) for i, tid, inp, txt in transcript_calls() if inp.get('action') == 'tiktok_ad_update' and inp.get('dry_run') is False
                 and ((inp.get('payload') or {}).get('creatives') or [{}])[0].get('ad_id') == ad]
        drys = [(i, inp, txt) for i, tid, inp, txt in transcript_calls() if inp.get('action') == 'tiktok_ad_update' and inp.get('dry_run') is not False
                and ((inp.get('payload') or {}).get('creatives') or [{}])[0].get('ad_id') == ad]
        assert lives and drys, 'no live/dry call'
        assert all(inp.get('payload') == P for i, inp, txt in lives + drys), 'a call differs from the built payload'
        dj = load_result(drys[-1][2]); dbody = ((((dj or {}).get('data') or {}).get('data') or {}).get('request') or {}).get('body')
        assert dbody == P, 'dry body differs'
        att = []
        for n, (i, inp, txt) in enumerate(lives, 1):
            j = load_result(txt) or {}
            d = (j.get('data') or {}).get('data') or {}
            if j.get('success') and d.get('code') == 0:
                att.append('live attempt %d: code 0 OK req %s need_audit=%s' % (n, d.get('request_id'), (d.get('data') or {}).get('need_audit')))
            else:
                err = (j.get('error') or {})
                tk = ((err.get('details') or {}).get('upstream_details') or {}).get('tiktok') or {}
                att.append('live attempt %d: FAILED %s %s %s' % (n, tk.get('code') or err.get('code'), tk.get('message') or err.get('message') or (txt or '')[:150], tk.get('request_id') or ''))
        rs = reads().get(ad) or []
        post = [r for r in rs if r['order'] > lives[-1][0] and r['complete']]
        assert post, 'no full read after the last live call'
        b = post[-1]['rec']; a = pb['pre_rec']
        eff = effective_url(b)
        ok_url = b.get('landing_page_url') == ch['new'] and eff[0] == ch['new']
        ok_utm = (b.get('utm_params') is None and a.get('utm_params') is None) or \
                 sorted((p['key'], p['value']) for p in (b.get('utm_params') or [])) == sorted((p['key'], p['value']) for p in new_utms(ch['new']))
        no_id = not any(p['key'] == 'utm_id' for p in (b.get('utm_params') or [])) and 'utm_id=' not in (b.get('landing_page_url') or '')
        diffs = {k: [a.get(k), b.get(k)] for k in sorted(set(a) | set(b)) if k not in ('landing_page_url', 'utm_params', 'modify_time') and a.get(k) != b.get(k)}
        trimmed = False
        if set(diffs) == {'ad_text'} and (a.get('ad_text') or '').rstrip() == (b.get('ad_text') or '') and a.get('ad_text') != b.get('ad_text'):
            trimmed = True; diffs = {}
        c = classify_pre = None
        detail = ('ad/update full update (%s %s %s, no tiktok_item_id). Pre-read req %s: URL == %s (utm_params %s keys%s). '
                  'dry_run OK (call input and preview body == built payload; every creative field as read, only landing_page_url = new and utm_params = the %d UTMs of new, no utm_id; pixel sent as exact string 7347671240183693330). %s. '
                  'Read-back req %s: landing_page_url %s new byte for byte; utm_params %s; %s; modify_time %s -> %s; status %s / %s%s.%s') % (
            a.get('identity_type'), a.get('campaign_automation_type'), a.get('ad_format'), pb['pre_read'], pb.get('pre_class', 'now'),
            len(a.get('utm_params') or []), ', no utm_id' if not any(p['key'] == 'utm_id' for p in (a.get('utm_params') or [])) else ', had utm_id',
            len(new_utms(ch['new'])), '; '.join(att), post[-1]['request_id'], '==' if ok_url else '!=',
            'match the UTMs of new (no utm_id)' if ok_utm and no_id else 'MISMATCH %r' % (b.get('utm_params'),),
            'no other field changed' if not diffs else 'OTHER FIELDS CHANGED: %r' % (diffs,),
            a.get('modify_time'), b.get('modify_time'), b.get('operation_status'), b.get('secondary_status'),
            ' (unchanged)' if [a.get('operation_status'), a.get('secondary_status')] == [b.get('operation_status'), b.get('secondary_status')] else ' (CHANGED from %s / %s)' % (a.get('operation_status'), a.get('secondary_status')),
            (' ad_text trailing space trimmed by gateway.' if trimmed else '') + ((' ' + extra) if extra else ''))
        res = 'Fixed' if (ok_url and ok_utm and no_id) else 'Failed'
        append({'unit': ad, 'before': pb['pre_cur'] if 'pre_cur' in pb else a.get('landing_page_url'), 'after_live': b.get('landing_page_url'), 'result': res, 'detail': detail})
        print(detail)
    elif cmd == 'already':
        # already <ad>: append AlreadyFixed from the latest full read
        ad = sys.argv[2]; u = units()[ad]; ch = u['changes'][0]
        c = classify(ad); assert c['class'][0] == 'AlreadyFixed', c['class']
        r = latest(ad); a = r['rec']
        ok_utm = a.get('utm_params') is None or sorted((p['key'], p['value']) for p in (a.get('utm_params') or [])) == sorted((p['key'], p['value']) for p in new_utms(ch['new']))
        detail = ('pre-read ad/get req %s: landing_page_url %s new (%s); utm_params %s; no write. %s %s %s, tiktok_item_id %s; status %s / %s; modify_time %s.') % (
            r['request_id'], '==' if a.get('landing_page_url') == ch['new'] else 'same params as', c['class'][1],
            ('%d keys == the UTMs of new (no utm_id)' % len(a.get('utm_params') or [])) if ok_utm else 'DIFFER from new: %r' % (a.get('utm_params'),),
            a.get('identity_type'), a.get('campaign_automation_type'), a.get('ad_format'), a.get('tiktok_item_id'),
            a.get('operation_status'), a.get('secondary_status'), a.get('modify_time'))
        append({'unit': ad, 'before': c['cur'], 'after_live': c['cur'], 'result': 'AlreadyFixed', 'detail': detail})
        print(detail)
    elif cmd == 'notattempted':
        # notattempted <detail-file> <ad>...   (cur = latest complete read of this session, else '' + note)
        detail = open(sys.argv[2], encoding='utf-8').read().strip()
        done = set()
        if os.path.exists(OUT):
            for line in open(OUT, encoding='utf-8'):
                try:
                    done.add(json.loads(line)['unit'])
                except Exception:
                    pass
        for ad in sys.argv[3:]:
            if ad in done:
                print('already has a result line', ad); continue
            r = latest(ad)
            cur = effective_url(r['rec'])[0] if r else ''
            d = detail + (' | live slot read this session: req %s' % r['request_id'] if r else ' | live slot not read this session (TikTok API errors); before/after_live left empty')
            append({'unit': ad, 'before': cur, 'after_live': cur, 'result': 'NotAttempted', 'detail': d})
