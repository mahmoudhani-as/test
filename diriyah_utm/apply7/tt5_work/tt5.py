#!/usr/bin/env python3
"""apply7 in_tiktok_5. Payloads built from the exact pre-read text (pre_all.json, extracted from this agent's transcript).
usage:
  tt5.py build                -> build payloads.json for every writable unit, print summary
  tt5.py show <ad_id>         -> print payload as JSON (non-letter non-ASCII chars \\u-escaped) for the tool call
  tt5.py call <ad_id> dry|live -> check the last tiktok_ad_update call for ad_id in the transcript equals the payload; save + summarise result
  tt5.py post <rid> <ad_id>.. -> extract ad/get result <rid>, compare each ad with pre-read and target
"""
import json, sys, unicodedata, subprocess
from urllib.parse import urlsplit, parse_qsl
ROOT = '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm'
INP = ROOT + '/apply7/in_tiktok_5.json'
W = ROOT + '/apply7/tt5_work/'
T = '/root/.claude/projects/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/subagents/workflows/wf_a77bf62d-a6a/agent-a4ff299a36348899c.jsonl'
EXCL = ROOT + '/work/excl_platform_refused_v2.json'
# exact pixel string: pixel/list raw text (req 2026101222143676C358F66C7086F8D3A2 / 20261012221544D0BB3223DE62981F1C34):
# "7347671240183693330" Visit Diriyah - Base Pixel, "7610705877289091089" Visit Diriyah - Restaurants. ad/get shows the base pixel rounded.
PIX = {7347671240183693000: '7347671240183693330'}
assert float('7347671240183693330') == float(7347671240183693000) and float('7610705877289091089') != float(7347671240183693000)

def units(): return {u['unit']: u for u in json.load(open(INP))}
def pre(): return json.load(open(W + 'pre_all.json'))
def new_utms(new): return [{'key': k, 'value': v} for k, v in parse_qsl(urlsplit(new).query, keep_blank_values=True)]

READONLY = {'advertiser_id', 'campaign_id', 'campaign_name', 'adgroup_id', 'adgroup_name', 'create_time', 'modify_time', 'operation_status',
            'secondary_status', 'is_new_structure', 'is_aco', 'campaign_automation_type', 'optimization_event', 'profile_image_url',
            'ad_ref_pixel_id', 'branded_content_disabled', 'landing_page_urls', 'carousel_image_labels', '_req'}
SEND_CU = ['ad_id', 'ad_name', 'identity_id', 'identity_type', 'ad_format', 'video_id', 'image_ids', 'ad_text', 'call_to_action', 'call_to_action_id',
           'landing_page_url', 'utm_params', 'tracking_pixel_id', 'display_name', 'avatar_icon_web_uri', 'aigc_disclosure_type', 'creative_authorized', 'vast_moat_enabled']
SEND_PULL = ['ad_id', 'ad_name', 'identity_id', 'identity_type', 'ad_format', 'tiktok_item_id', 'promotional_music_disabled', 'ad_text', 'call_to_action',
             'call_to_action_id', 'landing_page_url', 'utm_params', 'tracking_pixel_id', 'creative_authorized', 'vast_moat_enabled']
MUST_EMPTY = {'card_id': (None, ''), 'page_id': (None, ''), 'music_id': (None, ''), 'impression_tracking_url': (None, ''), 'click_tracking_url': (None, ''),
              'creative_type': (None, ''), 'ad_texts': (None, '', []), 'viewability_vast_url': (None, ''), 'brand_safety_vast_url': (None, ''),
              'deeplink': (None, ''), 'playable_url': (None, ''), 'viewability_postbid_partner': (None, 'UNSET'), 'brand_safety_postbid_partner': (None, 'UNSET'),
              'deeplink_type': (None, 'NORMAL'), 'fallback_type': (None, 'UNSET'), 'tiktok_item_id': (None, ''), 'app_name': (None, ''),
              'identity_authorized_bc_id': (None, ''), 'dark_post_status': (None,), 'promotional_music_disabled': (None,),
              'creative_auto_enhancement_strategy_list': (None, []), 'product_info': (None, {'product_titles': None, 'selling_points': None, 'product_image_list': None}),
              'video_id': (None, ''), 'image_ids': (None, []), 'display_name': (None, ''), 'avatar_icon_web_uri': (None, ''), 'aigc_disclosure_type': (None,)}

def build_one(ad):
    u = units()[ad]; ch = u['changes'][0]; a = pre()[ad]
    assert ch['slot'] == 'ad.landing_page_url' and len(u['changes']) == 1
    assert not any(e['platform'] == 'tiktok' and str(e.get('ad_id')) == ad and e.get('slot') == ch['slot'] for e in json.load(open(EXCL)))
    new = ch['new']; sp = urlsplit(new); q = parse_qsl(sp.query, keep_blank_values=True)
    assert all(k.startswith('utm_') and k != 'utm_id' for k, v in q) and len({k for k, v in q}) == len(q), q
    assert '#' not in new and sp.fragment == ''
    assert a['ad_id'] == ad and a['advertiser_id'] == u['account_id'] and a['ad_name'] == u['ad_names'][0]
    assert a['landing_page_url'] == ch['now'] or a['landing_page_url'] in ch['alt_now']
    assert a['campaign_automation_type'] == 'MANUAL' and a['is_aco'] is False and a['ad_format'] == 'SINGLE_VIDEO'
    it = a['identity_type']
    if it == 'CUSTOMIZED_USER':
        send = SEND_CU; assert a['video_id'] and a['image_ids'] and not a.get('tiktok_item_id')
    elif it == 'AUTH_CODE':
        send = SEND_PULL; assert a['tiktok_item_id'] and isinstance(a['tiktok_item_id'], str) and not a.get('video_id')
    else:
        raise SystemExit('not built: ' + it)
    unknown = []
    for k, v in a.items():
        if k in READONLY or k in send: continue
        if it == 'AUTH_CODE' and k in ('display_name', 'app_name'):   # derived from the TikTok account for Spark Pull ads (kept unchanged on 12-Oct ad 1837620326148306)
            continue
        if k in MUST_EMPTY:
            assert v in MUST_EMPTY[k], (ad, k, v); continue
        unknown.append((k, v))
    assert not unknown, ('unhandled fields', unknown)
    cr = {}
    for k in send:
        if k == 'landing_page_url': cr[k] = new; continue
        if k == 'utm_params':
            if a.get('utm_params') is not None: cr[k] = new_utms(new)
            continue
        if k == 'tracking_pixel_id':
            tp = a.get('tracking_pixel_id')
            if tp not in (0, None, ''): cr[k] = PIX[tp]
            continue
        if k == 'call_to_action' and a.get('call_to_action_id'): continue
        if k == 'call_to_action_id' and not a.get('call_to_action_id'): continue
        if k == 'call_to_action' and not a.get('call_to_action'): continue
        if k in a and a[k] is not None: cr[k] = a[k]
    if it == 'AUTH_CODE':
        assert 'video_id' not in cr and cr['tiktok_item_id'] == a['tiktok_item_id']
    return {'advertiser_id': u['account_id'], 'adgroup_id': a['adgroup_id'], 'creatives': [cr]}

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

def transcript_calls():
    uses = {}; order = []; res = {}
    for line in open(T, encoding='utf-8'):
        try: e = json.loads(line)
        except Exception: continue
        content = (e.get('message') or {}).get('content')
        if not isinstance(content, list): continue
        for c in content:
            if not isinstance(c, dict): continue
            if c.get('type') == 'tool_use' and c.get('name', '').endswith('tiktok_native_action'):
                uses[c['id']] = c.get('input') or {}; order.append(c['id'])
            if c.get('type') == 'tool_result' and c.get('tool_use_id') in uses:
                cc = c.get('content')
                res[c['tool_use_id']] = ''.join(x.get('text', '') for x in cc if isinstance(x, dict)) if isinstance(cc, list) else str(cc)
    for i, tid in enumerate(order):
        yield i, tid, uses[tid], res.get(tid)

if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'build':
        P = {}; held = {}
        for ad, u in units().items():
            a = pre()[ad]
            if a['identity_type'] == 'BC_AUTH_TT' and a.get('tiktok_item_id'):
                held[ad] = a['tiktok_item_id']; continue
            P[ad] = build_one(ad)
        json.dump(P, open(W + 'payloads.json', 'w'), ensure_ascii=False, indent=1)
        print('held (Spark Push):', held)
        for ad, p in P.items():
            cr = p['creatives'][0]
            print(ad, cr['identity_type'], sorted(cr.keys()), 'utm', [x['key'] for x in cr.get('utm_params', [])])
    elif cmd == 'show':
        print(safe_dumps(json.load(open(W + 'payloads.json'))[sys.argv[2]]))
    elif cmd == 'call':
        ad, mode = sys.argv[2], sys.argv[3]; want_dry = (mode == 'dry')
        P = json.load(open(W + 'payloads.json'))[ad]
        found = [(i, tid, inp, txt) for i, tid, inp, txt in transcript_calls()
                 if inp.get('action') == 'tiktok_ad_update' and ((inp.get('payload') or {}).get('creatives') or [{}])[0].get('ad_id') == ad
                 and bool(inp.get('dry_run', True)) == want_dry]
        if not found: sys.exit('no matching call')
        i, tid, inp, txt = found[-1]
        extra = {k: v for k, v in inp.items() if k not in ('action', 'payload', 'dry_run')}
        print('calls found:', len(found), '| payload_equal:', inp.get('payload') == P, '| dry_run:', inp.get('dry_run'), '| other args:', extra)
        if inp.get('payload') != P:
            a = inp.get('payload') or {}
            for k in set(P['creatives'][0]) | set((a.get('creatives') or [{}])[0]):
                if P['creatives'][0].get(k) != (a.get('creatives') or [{}])[0].get(k): print('DIFF', k, repr(P['creatives'][0].get(k))[:300], '!=', repr((a.get('creatives') or [{}])[0].get(k))[:300])
        if txt is None: sys.exit('no result yet')
        open(W + 'resp_%s_%s.json' % (mode, ad), 'w', encoding='utf-8').write(txt)
        try: j = json.loads(txt)
        except Exception: print('non-JSON result:', txt[:2000]); sys.exit(0)
        if want_dry:
            dd = (j.get('data') or {}).get('data') or {}
            body = (dd.get('request') or {}).get('body')
            print('preview body == payload:', body == P, '| dryRun:', dd.get('dryRun'), '| path:', (dd.get('request') or {}).get('path'), '| warnings:', dd.get('warnings'), '| preflightBlocking:', dd.get('preflightBlocking'))
            if body != P: print(json.dumps(j, ensure_ascii=False)[:3000])
        else:
            print(json.dumps(j, ensure_ascii=False)[:1500])
    elif cmd == 'post':
        rid = sys.argv[2]; ads = sys.argv[3:]
        fn = W + 'post_%s.json' % rid
        subprocess.run(['python3', '-I', W + 'extract.py', rid, fn], check=True, capture_output=True)
        d = json.load(open(fn)); dd = d['data']['data']; assert dd['code'] == 0 and dd['request_id'] == rid
        post = {a['ad_id']: a for a in dd['data']['list'] if isinstance(a, dict)}
        PRE = pre(); U = units(); res = {}
        for ad in ads:
            a = post.get(ad)
            if a is None: print(ad, 'NOT IN READ'); continue
            new = U[ad]['changes'][0]['new']; q = parse_qsl(urlsplit(new).query, keep_blank_values=True)
            up = [(x['key'], x['value']) for x in (a.get('utm_params') or [])]
            p = PRE[ad]
            diffs = [(k, p.get(k, '<absent>'), a.get(k, '<absent>')) for k in sorted(set(p) | set(a)) if k not in ('landing_page_url', 'utm_params', 'modify_time', '_req') and p.get(k) != a.get(k)]
            r = {'url_ok': a['landing_page_url'] == new, 'utm_ok': sorted(up) == sorted(q) and len(up) == len(q), 'after_live': a['landing_page_url'],
                 'utm_after': up, 'diffs': diffs, 'modify': [p['modify_time'], a['modify_time']], 'status': [a['operation_status'], a['secondary_status']],
                 'item': a.get('tiktok_item_id'), 'ad_text_same': a.get('ad_text') == p.get('ad_text')}
            res[ad] = r
            print(ad, json.dumps(r, ensure_ascii=False))
        json.dump(res, open(W + 'postcheck_%s.json' % rid, 'w'), ensure_ascii=False, indent=1)
