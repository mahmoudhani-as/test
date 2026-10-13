#!/usr/bin/env python3
"""apply7 in_tiktok_9 helper. Reads THIS agent's own Whathead tool calls/results from its transcript, so every
value is byte-exact (no retyping).
usage:
  tt9.py reads                        -> list complete reads found per unit
  tt9.py classify <ad>...             -> classify latest complete read vs plan
  tt9.py build <ad>                   -> build the update payload from the latest complete read; print compact JSON
  tt9.py call <ad> dry|live           -> check the last update call for ad: input == built payload; response summary
  tt9.py verify <ad>                  -> compare the latest complete read after the live call with plan new + pre-read
  tt9.py append <row.json>            -> append one result line to the results file
  tt9.py checkout                     -> validate the results file against plan and transcript
"""
import json, sys, os, re, copy, unicodedata
from urllib.parse import urlsplit, parse_qsl
ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
INP = ROOT + '/apply7/in_tiktok_9.json'
OUT = ROOT + '/apply7/out_tiktok_9.jsonl'
W = ROOT + '/apply7/tt9_work/'
TR = '/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/wf_e62cae8e-5aa/agent-acb6fee896aa34295.jsonl'
EXCL = ROOT + '/work/excl_platform_refused_v2.json'
SP_RE = re.compile(r'^smart_plus_ad\.landing_page_url_list\[(\d+)\]\.landing_page_url$')
PIX_FILE = W + 'pixels.json'   # {"<exact pixel id string>": "<source>"}


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
            if have[k] != v: conflict.append((k, have[k], v))
        else:
            extra.append((k, v))
    e = url
    if extra:
        e = url + ('&' if '?' in url else '?') + '&'.join('%s=%s' % (k, v) for k, v in extra)
    return e, extra, conflict


def text_notes(txt):
    txt = txt or ''
    return {'trailing_ws': txt != txt.rstrip(), 'leading_ws': txt != txt.lstrip(),
            'nonprint': sorted({'U+%04X' % ord(c) for c in txt if unicodedata.category(c) in ('Cf', 'Cc', 'Zs', 'Mn') and c != ' '})}


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
        m = re.search(r'(?:saved to|Full output saved to):?\s*(\S+)', txt)
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


GET_ACTIONS = {'tiktok_ad_get': 'ad_id', 'tiktok_smart_plus_ad_get': 'smart_plus_ad_id'}


def reads():
    out = {}
    for i, tid, inp, txt, iserr in transcript_calls():
        a = inp.get('action')
        if a not in GET_ACTIONS:
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
            complete = ('__mcp_truncated_keys' not in json.dumps(r)) and not trunc and not projected
            out.setdefault(str(r[GET_ACTIONS[a]]), []).append({'order': i, 'tool_use_id': tid, 'request_id': rid, 'complete': complete,
                                                               'kind': 'sp' if a == 'tiktok_smart_plus_ad_get' else 'ad', 'rec': r})
    return out


def latest(ad, after_order=None, before_order=None, R=None):
    rs = (R if R is not None else reads()).get(ad) or []
    rs = [r for r in rs if r['complete'] and (after_order is None or r['order'] > after_order)
          and (before_order is None or r['order'] < before_order)]
    return rs[-1] if rs else None


# ---------------- classification ----------------
def slot_cur(u, ch, rec, kind):
    """returns (cur effective url, url field, utm_params, extra, conflict, index)"""
    if ch['slot'] == 'ad.landing_page_url':
        assert kind == 'ad', 'slot/kind mismatch'
        url = rec.get('landing_page_url'); ups = rec.get('utm_params')
        e, extra, conflict = eff(url, ups)
        return e, url, ups, extra, conflict, None
    m = SP_RE.match(ch['slot'])
    assert m and kind == 'sp', 'unexpected slot %r / kind %r' % (ch['slot'], kind)
    i = int(m.group(1))
    lpl = rec.get('landing_page_url_list') or []
    url = lpl[i].get('landing_page_url') if len(lpl) > i else None
    ups = (rec.get('ad_configuration') or {}).get('utm_params')
    e, extra, conflict = eff(url, ups)
    return e, url, ups, extra, conflict, i


def ad_class(rec, kind):
    if kind == 'sp':
        return 'SMART_PLUS'
    it = rec.get('identity_type'); item = rec.get('tiktok_item_id')
    if it == 'BC_AUTH_TT' and item:
        return 'SPARK_PUSH_HOLD'
    if it == 'BC_AUTH_TT':
        return 'BC_AUTH_TT_NO_ITEM'
    if it == 'CUSTOMIZED_USER':
        return 'CUSTOMIZED_USER'
    if it == 'AUTH_CODE':
        return 'SPARK_PULL'
    return 'OTHER:' + str(it)


def decide(ch, cur):
    if equiv(cur, ch['new']):
        return 'AlreadyFixed'
    if cur == ch['now'] or cur in ch['alt_now']:
        return 'Write'
    return 'Skipped'


def classify(ad, R=None):
    u = units()[ad]; r = latest(ad, R=R)
    if not r:
        return {'ad': ad, 'decision': 'NO_READ'}
    rec = r['rec']; kind = r['kind']
    assert len(u['changes']) == 1, 'multi-change unit'
    ch = u['changes'][0]
    cur, url, ups, extra, conflict, i = slot_cur(u, ch, rec, kind)
    cls = ad_class(rec, kind)
    dec = decide(ch, cur)
    if excluded(ad, ch['slot']):
        dec = 'EXCLUDED'
    if dec == 'Write' and cls == 'SPARK_PUSH_HOLD':
        dec = 'Hold'
    info = {'ad': ad, 'read_order': r['order'], 'request_id': r['request_id'], 'kind': kind, 'cls': cls, 'decision': dec,
            'match': ('new' if dec == 'AlreadyFixed' else 'now' if cur == ch['now'] else ('alt_now[%d]' % ch['alt_now'].index(cur)) if cur in ch['alt_now'] else '-'),
            'cur': cur, 'url_field': url, 'utm_params': ups, 'utm_extra': extra, 'utm_conflict': conflict,
            'ad_name_matches_plan': rec.get('ad_name') == u['ad_names'][0], 'ad_name': rec.get('ad_name'),
            'op': rec.get('operation_status'), 'sec': rec.get('secondary_status'), 'modify_time': rec.get('modify_time'),
            'adgroup_id': rec.get('adgroup_id'), 'advertiser_ok': str(rec.get('advertiser_id')) == u['account_id']}
    if kind == 'ad':
        info.update({'identity_type': rec.get('identity_type'), 'identity_id': rec.get('identity_id'), 'bc': rec.get('identity_authorized_bc_id'),
                     'item': rec.get('tiktok_item_id'), 'ad_format': rec.get('ad_format'), 'video_id': rec.get('video_id'),
                     'image_ids': rec.get('image_ids'), 'music_id': rec.get('music_id'), 'cta': rec.get('call_to_action'),
                     'cta_id': rec.get('call_to_action_id'), 'pixel': rec.get('tracking_pixel_id'), 'text': text_notes(rec.get('ad_text')),
                     'campaign_automation_type': rec.get('campaign_automation_type'), 'nkeys': len(rec)})
    else:
        cl = rec.get('creative_list') or []
        info.update({'slot_index': i, 'n_lp': len(rec.get('landing_page_url_list') or []),
                     'materials': [{'ad_material_id': c.get('ad_material_id'), 'fmt': (c.get('creative_info') or {}).get('ad_format'),
                                    'identity_type': (c.get('creative_info') or {}).get('identity_type'),
                                    'identity_id': (c.get('creative_info') or {}).get('identity_id'),
                                    'item': (c.get('creative_info') or {}).get('tiktok_item_id'),
                                    'video': ((c.get('creative_info') or {}).get('video_info') or {}).get('video_id'),
                                    'n_images': len((c.get('creative_info') or {}).get('image_info') or []),
                                    'status': c.get('material_operation_status')} for c in cl],
                     'ac_keys': sorted((rec.get('ad_configuration') or {}).keys()),
                     'texts': [text_notes(t.get('ad_text')) for t in (rec.get('ad_text_list') or [])]})
    return info


# ---------------- payload builders ----------------
EMPTY_AD = ('card_id', 'page_id', 'impression_tracking_url', 'click_tracking_url', 'creative_type', 'ad_texts', 'carousel_image_labels',
            'landing_page_urls', 'viewability_vast_url', 'brand_safety_vast_url', 'deeplink', 'playable_url', 'cpp_url', 'video_view_tracking_url',
            'tracking_app_id', 'tracking_offline_event_set_ids', 'disclaimer_type', 'disclaimer_text', 'disclaimer_clickable_texts',
            'shopping_ads_video_package_id', 'product_specific_type', 'item_group_ids', 'product_set_id', 'sku_ids', 'dynamic_format',
            'carousel_image_index', 'end_card_cta', 'deeplink_utm_params', 'instant_product_page_used', 'page_image_index',
            'promotional_music_disabled', 'item_duet_status', 'item_stitch_status', 'app_name')
DEFAULTS_AD = (('vertical_video_strategy', (None, 'UNSET')), ('fallback_type', (None, 'UNSET')), ('dynamic_destination', (None, 'UNSET')),
               ('shopping_ads_fallback_type', (None, 'DEFAULT')), ('deeplink_type', (None, 'NORMAL')),
               ('viewability_postbid_partner', (None, 'UNSET')), ('brand_safety_postbid_partner', (None, 'UNSET')),
               ('shopping_ads_deeplink_type', (None, 'NONE', 'UNSET')))


def pixels():
    try:
        return json.load(open(PIX_FILE))
    except Exception:
        return {}


def pixel_exact(v):
    if v in (None, 0, '0', ''):
        return None
    for s in pixels():
        if float(int(s)) == float(v) and (not isinstance(v, str) or v == s):
            return s
    raise SystemExit('UNKNOWN PIXEL %r: add the exact id from pixel/list to pixels.json first' % (v,))


def build_ad(u, ch, rec, cls, probs):
    a = rec; new = ch['new']
    for k in EMPTY_AD:
        if a.get(k) not in (None, '', [], {}):
            probs.append('non-empty %s=%r' % (k, a.get(k)))
    for k, ok in DEFAULTS_AD:
        if a.get(k) not in ok:
            probs.append('unexpected %s=%r' % (k, a.get(k)))
    pi = a.get('product_info')
    if not (pi is None or all(v is None for v in pi.values())):
        probs.append('product_info=%r' % (pi,))
    if a.get('is_aco') not in (False, None):
        probs.append('is_aco=%r' % a.get('is_aco'))
    if a.get('campaign_automation_type') not in (None, 'MANUAL'):
        probs.append('campaign_automation_type=%r' % a.get('campaign_automation_type'))
    cr = {'ad_id': a['ad_id'], 'ad_name': a['ad_name']}
    if cls == 'CUSTOMIZED_USER':
        cr['identity_id'] = a['identity_id']; cr['identity_type'] = a['identity_type']
        cr['ad_format'] = a['ad_format']
        if a['ad_format'] not in ('SINGLE_VIDEO', 'SINGLE_IMAGE'):
            probs.append('CUSTOMIZED_USER ad_format=%r' % a['ad_format'])
        if a.get('video_id'): cr['video_id'] = a['video_id']
        if a.get('image_ids'): cr['image_ids'] = a['image_ids']
        if a.get('music_id'): probs.append('music_id on CUSTOMIZED_USER %r' % a.get('music_id'))
        cr['ad_text'] = a['ad_text']
        for k in ('display_name', 'avatar_icon_web_uri', 'aigc_disclosure_type'):
            if a.get(k) not in (None, ''): cr[k] = a[k]
        for k in ('creative_authorized', 'vast_moat_enabled'):
            if k in a and a[k] is not None: cr[k] = a[k]
        if a.get('identity_authorized_bc_id'): probs.append('bc id on CUSTOMIZED_USER')
        if a.get('dark_post_status') not in (None,): probs.append('dark_post_status on CUSTOMIZED_USER %r' % a.get('dark_post_status'))
        if a.get('creative_auto_enhancement_strategy_list'): cr['creative_auto_enhancement_strategy_list'] = a['creative_auto_enhancement_strategy_list']
    elif cls == 'BC_AUTH_TT_NO_ITEM':
        cr['identity_type'] = a['identity_type']; cr['identity_id'] = a['identity_id']; cr['identity_authorized_bc_id'] = a['identity_authorized_bc_id']
        cr['ad_format'] = a['ad_format']
        if a['ad_format'] != 'CAROUSEL_ADS': probs.append('BC_AUTH_TT no-item ad_format=%r' % a['ad_format'])
        if a.get('video_id'): probs.append('video_id on carousel %r' % a.get('video_id'))
        cr['image_ids'] = a['image_ids']
        if a.get('music_id'): cr['music_id'] = a['music_id']
        cr['ad_text'] = a['ad_text']
    elif cls == 'SPARK_PULL':
        cr['identity_type'] = a['identity_type']; cr['identity_id'] = a['identity_id']
        cr['ad_format'] = a['ad_format']
        it = a.get('tiktok_item_id')
        if not isinstance(it, str) or not it.isdigit(): probs.append('tiktok_item_id not an exact string: %r' % (it,))
        cr['tiktok_item_id'] = it
        cr['ad_text'] = a.get('ad_text')
        if a.get('identity_authorized_bc_id'): probs.append('bc id on AUTH_CODE %r' % a.get('identity_authorized_bc_id'))
        probs.append('SPARK_PULL builder: review every field against the read')
    else:
        probs.append('class not handled by this builder: ' + cls)
    if a.get('call_to_action_id'):
        if a.get('call_to_action') not in (None, ''): probs.append('both CTA and CTA id')
        cr['call_to_action_id'] = a['call_to_action_id']
    else:
        cr['call_to_action'] = a['call_to_action']
    cr['landing_page_url'] = new
    if a.get('utm_params'):
        cr['utm_params'] = new_utms(new)
    if cls == 'BC_AUTH_TT_NO_ITEM':
        cr['dark_post_status'] = a['dark_post_status']
        if a.get('creative_auto_enhancement_strategy_list'): cr['creative_auto_enhancement_strategy_list'] = a['creative_auto_enhancement_strategy_list']
        cr['creative_authorized'] = a['creative_authorized']; cr['vast_moat_enabled'] = a['vast_moat_enabled']
        if a.get('aigc_disclosure_type') not in (None, ''): probs.append('aigc on BC_AUTH_TT %r' % a.get('aigc_disclosure_type'))
    px = pixel_exact(a.get('tracking_pixel_id'))
    if px: cr['tracking_pixel_id'] = px
    return {'advertiser_id': u['account_id'], 'adgroup_id': a['adgroup_id'], 'creatives': [cr]}


def bignums(o, path=''):
    out = []
    if isinstance(o, dict):
        for k, v in o.items(): out += bignums(v, path + '.' + k)
    elif isinstance(o, list):
        for i, v in enumerate(o): out += bignums(v, path + '[%d]' % i)
    elif isinstance(o, (int, float)) and not isinstance(o, bool) and abs(o) > 2 ** 53:
        out.append((path, o))
    return out


def build_sp(u, ch, rec, i, probs):
    lpl = copy.deepcopy(rec['landing_page_url_list'])
    lpl[i]['landing_page_url'] = ch['new']
    ac = copy.deepcopy(rec.get('ad_configuration') or {})
    if ac.get('utm_params'):
        ac['utm_params'] = new_utms(ch['new'])
    elif 'utm_params' in ac:
        probs.append('utm_params present but empty: left as read')
    for p, v in bignums(ac):
        probs.append('big number in ad_configuration %s=%r (precision!)' % (p, v))
    return {'advertiser_id': u['account_id'], 'smart_plus_ad_id': rec['smart_plus_ad_id'], 'landing_page_url_list': lpl, 'ad_configuration': ac}


def build(ad):
    u = units()[ad]; ch = u['changes'][0]; R = reads(); r = latest(ad, R=R)
    info = classify(ad, R=R)
    assert info['decision'] == 'Write', 'decision is %s' % info['decision']
    rec = r['rec']; probs = []
    if not info['ad_name_matches_plan']: probs.append('ad_name differs from plan: %r' % rec.get('ad_name'))
    if info['utm_conflict']: probs.append('utm_params conflict with URL: %r' % info['utm_conflict'])
    if not info['advertiser_ok']: probs.append('advertiser mismatch')
    if r['kind'] == 'sp':
        P = build_sp(u, ch, rec, info['slot_index'], probs)
        meth = 'tiktok_smart_plus_ad_update'
    else:
        P = build_ad(u, ch, rec, info['cls'], probs)
        meth = 'tiktok_ad_update'
    json.dump({'payload': P, 'action': meth, 'pre_read': r['request_id'], 'pre_order': r['order'], 'pre_rec': rec, 'info': info, 'probs': probs},
              open(W + 'payload_%s.json' % ad, 'w'), ensure_ascii=False, indent=1)
    print('ACTION', meth, '| class', info['cls'], '| pre-read', r['request_id'], '| probs:', probs)
    print(json.dumps(P, ensure_ascii=False, separators=(',', ':')))


def paycheck(ad):
    """every payload field equals the pre-read except the URL (+ utm_params, + exact pixel string)"""
    pb = json.load(open(W + 'payload_%s.json' % ad)); P = pb['payload']; a = pb['pre_rec']; new = units()[ad]['changes'][0]['new']
    bad = []
    if pb['action'] == 'tiktok_ad_update':
        cr = P['creatives'][0]
        for k, v in cr.items():
            if k == 'landing_page_url':
                if v != new: bad.append(k)
            elif k == 'utm_params':
                if v != new_utms(new): bad.append(k)
            elif k == 'tracking_pixel_id':
                if float(int(v)) != float(a.get('tracking_pixel_id')): bad.append(k)
            elif a.get(k) != v:
                bad.append(k)
        if P['advertiser_id'] != str(a['advertiser_id']) or P['adgroup_id'] != a['adgroup_id']: bad.append('top')
        notsent = [k for k in a if k not in cr and a[k] not in (None, '', [], {})]
        print(ad, 'OK' if not bad else 'BAD ' + str(bad), '| sent:', list(cr.keys()))
        print('   not sent (non-empty in read):', notsent)
    else:
        i = pb['info']['slot_index']
        lb = P['landing_page_url_list']; la = a['landing_page_url_list']
        if len(lb) != len(la): bad.append('lpl length')
        for j, (x, y) in enumerate(zip(lb, la)):
            x = dict(x); y = dict(y)
            if j == i:
                if x.get('landing_page_url') != new: bad.append('lpl[i] != new')
                x.pop('landing_page_url', None); y.pop('landing_page_url', None)
            if x != y: bad.append('lpl[%d] other keys differ' % j)
        acb = dict(P['ad_configuration']); aca = dict(a.get('ad_configuration') or {})
        ub = acb.pop('utm_params', None); ua = aca.pop('utm_params', None)
        if acb != aca: bad.append('ad_configuration differs beyond utm_params')
        if ua:
            if ub != new_utms(new): bad.append('utm_params != UTMs of new')
        elif ub != ua:
            bad.append('utm_params changed although absent/empty')
        if sorted(P) != ['ad_configuration', 'advertiser_id', 'landing_page_url_list', 'smart_plus_ad_id']: bad.append('top keys %r' % sorted(P))
        print(ad, 'OK' if not bad else 'BAD ' + str(bad), '| sent top keys:', sorted(P), '| creative_list NOT sent')
    return not bad


# ---------------- calls ----------------
UPD = ('tiktok_ad_update', 'tiktok_smart_plus_ad_update')


def body_of(inp):
    b = inp.get('payload') or inp.get('params') or {}
    if isinstance(b, str):
        try: b = json.loads(b)
        except Exception: b = {}
    return b


def update_calls(ad):
    found = []
    for i, tid, inp, txt, iserr in transcript_calls():
        if inp.get('action') not in UPD:
            continue
        b = body_of(inp)
        ids = [str(b.get('smart_plus_ad_id'))] + [str(c.get('ad_id')) for c in (b.get('creatives') or []) if isinstance(c, dict)]
        if ad in ids:
            found.append((i, tid, inp, txt, iserr))
    return found


def call(ad, mode):
    pb = json.load(open(W + 'payload_%s.json' % ad)); P = pb['payload']
    want_dry = (mode == 'dry')
    found = [f for f in update_calls(ad) if bool(f[2].get('dry_run', True)) == want_dry]
    allc = update_calls(ad)
    print('update calls for ad (all modes):', [(f[0], 'dry' if f[2].get('dry_run', True) else 'LIVE') for f in allc])
    if not found:
        print('no %s call found' % mode); return
    i, tid, inp, txt, iserr = found[-1]
    b = body_of(inp)
    print('calls(%s):' % mode, len(found), '| order', i, '| action', inp.get('action'), '== built', inp.get('action') == pb['action'],
          '| input payload == built payload:', b == P, '| other args:', {k: v for k, v in inp.items() if k not in ('payload', 'params')})
    if b != P:
        for k in sorted(set(b) | set(P)):
            if b.get(k) != P.get(k):
                print('  DIFF', k, json.dumps(b.get(k), ensure_ascii=False)[:600], '!=', json.dumps(P.get(k), ensure_ascii=False)[:600])
    j = load_result(txt)
    if j is None:
        print('no result yet'); return
    if '_raw_text' in j:
        print('RAW RESULT (is_error=%s):' % iserr, j['_raw_text'][:3000]); return
    print('success:', j.get('success'), '| error:', json.dumps(j.get('error'), ensure_ascii=False)[:1500])
    d = j.get('data') or {}
    if want_dry:
        req = ((d.get('data') or {}).get('request')) or {}
        body = req.get('body')
        print('dryRun:', d.get('dryRun'), '| path:', req.get('path'), '| preview body == payload:', body == P,
              '| warnings:', (d.get('data') or {}).get('warnings'), '| preflightBlocking:', (d.get('data') or {}).get('preflightBlocking'))
        if body is not None and body != P:
            for k in sorted(set(body) | set(P)):
                if body.get(k) != P.get(k):
                    print('  BODY DIFF', k, json.dumps(body.get(k), ensure_ascii=False)[:800], '!=', json.dumps(P.get(k), ensure_ascii=False)[:800])
            if 'creatives' in P:
                cb = body['creatives'][0]; cp = P['creatives'][0]
                for k in sorted(set(cb) | set(cp)):
                    if cb.get(k) != cp.get(k):
                        print('  CREATIVE DIFF', k, repr(cb.get(k))[:300], '!=', repr(cp.get(k))[:300])
    else:
        dd = d.get('data') or {}
        print('dryRun:', d.get('dryRun'), '| live code:', dd.get('code'), '| message:', dd.get('message'), '| request_id:', dd.get('request_id'))
        data = dd.get('data') or {}
        if pb['action'] == 'tiktok_ad_update':
            print('ad_ids:', data.get('ad_ids'), '| need_audit:', data.get('need_audit'))
            for cr in data.get('creatives') or []:
                print('resp landing_page_url == new:', cr.get('landing_page_url') == P['creatives'][0]['landing_page_url'],
                      '| modify_time', cr.get('modify_time'), '| ad_text == sent:', cr.get('ad_text') == P['creatives'][0].get('ad_text'))
        else:
            lpl = data.get('landing_page_url_list') or []
            print('resp lpl:', json.dumps(lpl, ensure_ascii=False)[:600], '| modify_time', data.get('modify_time'),
                  '| status', data.get('operation_status'), data.get('secondary_status'))
        print('meta:', json.dumps(d.get('meta'), ensure_ascii=False)[:500])


# ---------------- verify ----------------
def verify(ad):
    u = units()[ad]; ch = u['changes'][0]; new = ch['new']
    pb = json.load(open(W + 'payload_%s.json' % ad)); pre = pb['pre_rec']; info = pb['info']
    lives = [f for f in update_calls(ad) if not bool(f[2].get('dry_run', True))]
    after = lives[-1][0] if lives else pb['pre_order']
    R = reads(); r = latest(ad, after_order=after, R=R)
    if not r:
        print('no complete read after the live call'); return
    rec = r['rec']; kind = r['kind']
    cur, url, ups, extra, conflict, i = slot_cur(u, ch, rec, kind)
    res = {'read_request_id': r['request_id'], 'read_order': r['order'], 'after_live': url, 'after_eff': cur,
           'url_equals_new_bytes': url == new, 'eff_equals_new_bytes': cur == new, 'utm_extra': extra, 'utm_conflict': conflict}
    if kind == 'ad':
        had = bool(pre.get('utm_params'))
        up = [(p['key'], p['value']) for p in (rec.get('utm_params') or [])]
        q = [(p['key'], p['value']) for p in new_utms(new)]
        res['utm_ok'] = (sorted(up) == sorted(q) and len(up) == len(q)) if had else (rec.get('utm_params') == pre.get('utm_params'))
        res['utm_keys_after'] = [k for k, v in up]
        res['utm_id_after'] = any(k == 'utm_id' for k, v in up) or 'utm_id=' in (url or '')
        res['diffs'] = [(k, pre.get(k, '<absent>'), rec.get(k, '<absent>')) for k in sorted(set(pre) | set(rec))
                        if k not in ('landing_page_url', 'utm_params', 'modify_time') and pre.get(k, '<absent>') != rec.get(k, '<absent>')]
        res['nkeys'] = (len(pre), len(rec)); res['item_after'] = rec.get('tiktok_item_id', '<absent>')
    else:
        acp = dict(pre.get('ad_configuration') or {}); aca = dict(rec.get('ad_configuration') or {})
        upa = aca.pop('utm_params', None); upp = acp.pop('utm_params', None)
        if upp:
            res['utm_ok'] = sorted((p['key'], p['value']) for p in (upa or [])) == sorted((p['key'], p['value']) for p in new_utms(new)) and len(upa or []) == len(new_utms(new))
        else:
            res['utm_ok'] = (upa == upp)
        res['utm_keys_after'] = [p['key'] for p in (upa or [])]
        res['utm_id_after'] = any(p['key'] == 'utm_id' for p in (upa or [])) or 'utm_id=' in (url or '')
        diffs = []
        if acp != aca:
            diffs.append(('ad_configuration(other)', {k: acp.get(k) for k in set(acp) | set(aca) if acp.get(k) != aca.get(k)},
                          {k: aca.get(k) for k in set(acp) | set(aca) if acp.get(k) != aca.get(k)}))
        lp = pre.get('landing_page_url_list') or []; la = rec.get('landing_page_url_list') or []
        if len(lp) != len(la): diffs.append(('landing_page_url_list length', len(lp), len(la)))
        else:
            for j, (x, y) in enumerate(zip(lp, la)):
                x = dict(x); y = dict(y)
                if j == i: x.pop('landing_page_url', None); y.pop('landing_page_url', None)
                if x != y: diffs.append(('landing_page_url_list[%d]' % j, x, y))
        for k in sorted(set(pre) | set(rec)):
            if k in ('landing_page_url_list', 'ad_configuration', 'modify_time'): continue
            if pre.get(k, '<absent>') != rec.get(k, '<absent>'): diffs.append((k, pre.get(k, '<absent>'), rec.get(k, '<absent>')))
        res['diffs'] = diffs
        res['items_before'] = [(c.get('creative_info') or {}).get('tiktok_item_id') for c in pre.get('creative_list') or []]
        res['items_after'] = [(c.get('creative_info') or {}).get('tiktok_item_id') for c in rec.get('creative_list') or []]
    res['status'] = ((pre.get('operation_status'), pre.get('secondary_status')), (rec.get('operation_status'), rec.get('secondary_status')))
    res['modify_time'] = (pre.get('modify_time'), rec.get('modify_time'))
    res['FIXED'] = bool(res['url_equals_new_bytes'] and res['eff_equals_new_bytes'] and res['utm_ok'] and not res['utm_id_after'])
    print(json.dumps(res, ensure_ascii=False, indent=1))


# ---------------- results ----------------
REQ = ['platform', 'account_id', 'unit_type', 'unit', 'ad_ids', 'ad_names', 'slot', 'before', 'after_expected', 'after_live', 'result', 'new_entity_ids', 'detail']


def append(path):
    row = json.load(open(path))
    miss = [k for k in REQ if k not in row]
    assert not miss, 'missing %r' % miss
    assert row['result'] in ('Fixed', 'AlreadyFixed', 'Failed', 'Skipped', 'NotAttempted')
    u = units()[row['unit']]
    assert row['after_expected'] == [c for c in u['changes'] if c['slot'] == row['slot']][0]['new']
    done = set()
    if os.path.exists(OUT):
        for l in open(OUT, encoding='utf-8'):
            if l.strip():
                x = json.loads(l); done.add((x['unit'], x['slot']))
    assert (row['unit'], row['slot']) not in done, 'already recorded'
    with open(OUT, 'a', encoding='utf-8') as f:
        f.write(json.dumps({k: row[k] for k in REQ}, ensure_ascii=False) + '\n')
    print('appended', row['unit'], row['result'])


def checkout():
    U = units(); seen = set(); ok = True; R = reads()
    for n, line in enumerate(open(OUT, encoding='utf-8'), 1):
        row = json.loads(line)
        u = U.get(row['unit']); ch = [c for c in u['changes'] if c['slot'] == row['slot']][0]
        key = (row['unit'], row['slot']); errs = []
        if key in seen: errs.append('duplicate')
        seen.add(key)
        if row['after_expected'] != ch['new']: errs.append('after_expected != plan new')
        if row['account_id'] != u['account_id'] or row['ad_ids'] != u['ad_ids'] or row['ad_names'] != u['ad_names'] or row['unit_type'] != u['unit_type']:
            errs.append('unit fields differ from plan')
        rs = [r for r in (R.get(row['unit']) or []) if r['complete']]
        lives = [f for f in update_calls(row['unit']) if not bool(f[2].get('dry_run', True))]
        if lives:
            pre = [r for r in rs if r['order'] < lives[0][0]]; post = [r for r in rs if r['order'] > lives[-1][0]]
            if not pre or row['before'] != slot_cur(u, ch, pre[-1]['rec'], pre[-1]['kind'])[0]: errs.append('before != pre-read')
            if not post or row['after_live'] != slot_cur(u, ch, post[-1]['rec'], post[-1]['kind'])[1]: errs.append('after_live != read-back')
            if row['result'] == 'Fixed' and row['after_live'] != ch['new']: errs.append('Fixed but after_live != new')
        else:
            if row['result'] == 'Fixed': errs.append('Fixed without a live call')
            if rs and row['result'] in ('AlreadyFixed', 'Skipped', 'NotAttempted'):
                cur = slot_cur(u, ch, rs[-1]['rec'], rs[-1]['kind'])[0]
                if row['before'] != cur or row['after_live'] != cur: errs.append('before/after_live != latest read')
        print(n, row['unit'], row['result'], 'OK' if not errs else errs)
        ok = ok and not errs
    missing = [(k, c['slot']) for k, u in U.items() for c in u['changes'] if (k, c['slot']) not in seen]
    print('all lines OK:', ok, '| changes without a line:', len(missing), missing)


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'reads':
        R = reads(); U = units()
        for k in U:
            print(k, [(x['order'], x['request_id'], x['kind'], x['complete']) for x in R.get(k, [])])
    elif cmd == 'classify':
        R = reads()
        for ad in (sys.argv[2:] or list(units())):
            c = classify(ad, R=R)
            if '-v' in os.environ.get('TT9', ''):
                print(json.dumps(c, ensure_ascii=False, indent=1))
            else:
                print(json.dumps(c, ensure_ascii=False))
    elif cmd == 'build':
        build(sys.argv[2])
    elif cmd == 'paycheck':
        for ad in sys.argv[2:]: paycheck(ad)
    elif cmd == 'show-dry':
        call(sys.argv[2], 'dry')
    elif cmd == 'show-sent':
        call(sys.argv[2], 'live')
    elif cmd == 'readback':
        verify(sys.argv[2])
    elif cmd == 'append':
        append(sys.argv[2])
    elif cmd == 'checkout':
        checkout()
