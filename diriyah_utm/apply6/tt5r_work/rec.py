#!/usr/bin/env python3
"""rec.py <ad_id> [extra note]  -> builds the Fixed/Failed result row from transcript evidence and appends it."""
import json, sys, importlib.util
spec = importlib.util.spec_from_file_location('tt5r', '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply6/tt5r_work/tt5r.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
ad = sys.argv[1]; extra = sys.argv[2] if len(sys.argv) > 2 else ''
u = m.units()[ad]; ch = u['changes'][0]
pb = json.load(open(m.W + 'payload_%s.json' % ad)); P = pb['payload']; cr = P['creatives'][0]
rs = m.reads()[ad]
pre = [r for r in rs if r['request_id'] == pb['pre_read']][-1]; a = pre['rec']
cls = m.classify  # noqa
cur = a['landing_page_url']
how = 'now (exact)' if cur == ch['now'] else ('alt_now[%d] (exact)' % ch['alt_now'].index(cur) if cur in (ch.get('alt_now') or []) else 'matched after normalisation')
# dry + live calls for this ad
calls = {'dry': [], 'live': []}
for i, tid, inp, txt in m.transcript_calls():
    if inp.get('action') != 'tiktok_ad_update': continue
    crs = (inp.get('payload') or {}).get('creatives') or []
    if crs and crs[0].get('ad_id') == ad:
        calls['dry' if inp.get('dry_run', True) else 'live'].append((i, inp, m.load_result(txt), txt))
dry = calls['dry'][-1]; dj = dry[2]
dbody = ((dj.get('data') or {}).get('data') or {}).get('request', {}).get('body')
assert dry[1]['payload'] == P and dbody == P, 'dry run mismatch'
lives = calls['live']; assert 1 <= len(lives) <= 2
lv = lives[-1]; assert lv[1]['payload'] == P
ld = ((lv[2] or {}).get('data') or {}).get('data') or {}
post = [r for r in rs if r['order'] > lv[0] and r['complete']][-1]; b = post['rec']
diffs = {k: [a.get(k), b.get(k)] for k in sorted(set(a) | set(b)) if k not in ('landing_page_url', 'utm_params', 'modify_time') and a.get(k) != b.get(k)}
url_ok = b.get('landing_page_url') == ch['new']
utm_ok = sorted((p['key'], p['value']) for p in (b.get('utm_params') or [])) == sorted((p['key'], p['value']) for p in m.new_utms(ch['new']))
cta = ('call_to_action_id %s' % a['call_to_action_id']) if a.get('call_to_action_id') else ('CTA %s' % a.get('call_to_action'))
tw = (a.get('ad_text') or '') != (a.get('ad_text') or '').rstrip()
pix = ('pixel exact string %s (ad/get shows it rounded; pixel/list req 20261012221203344C11081568B883AF61)' % cr['tracking_pixel_id']) if 'tracking_pixel_id' in cr else 'no pixel on the ad (tracking_pixel_id 0, not sent)'
det = ("pre-read ad/get req %s: URL == %s (CUSTOMIZED_USER manual %s, identity %s, %s, utm_params %d keys old values%s; status %s / %s, modify_time %s). "
       "dry_run preview body == payload byte for byte (creative fields as read: ad_name, identity, ad_format, video_id, image_ids, ad_text%s, %s, display_name, avatar, aigc_disclosure_type %s, creative_authorized %s, vast_moat %s; %s) with only landing_page_url = new and utm_params = %d UTMs of new (no utm_id). "
       "Live full ad/update (%d live attempt%s) code %s %s req %s, need_audit=%s. Re-read ad/get req %s: landing_page_url %s new byte for byte, utm_params %s, %s; status %s / %s; modify_time %s -> %s.") % (
    pre['request_id'], how, a['ad_format'], a['identity_id'], cta, len(a.get('utm_params') or []),
    ', incl. utm_id' if any(p['key'] == 'utm_id' for p in (a.get('utm_params') or [])) else ', no utm_id',
    a.get('operation_status'), a.get('secondary_status'), a.get('modify_time'),
    ' byte-identical (no trailing space)' if not tw else ' (had trailing space)', cta, a.get('aigc_disclosure_type'), str(a.get('creative_authorized')).lower(), str(a.get('vast_moat_enabled')).lower(), pix,
    len(cr.get('utm_params') or []), len(lives), '' if len(lives) == 1 else 's', ld.get('code'), ld.get('message'), ld.get('request_id'), str((ld.get('data') or {}).get('need_audit')).lower(),
    post['request_id'], '==' if url_ok else '!=', 'match new (%d keys, no utm_id)' % len(b.get('utm_params') or []) if utm_ok else 'MISMATCH %s' % b.get('utm_params'),
    'every other field identical to the pre-read' if not diffs else 'OTHER FIELDS CHANGED: %s' % json.dumps(diffs, ensure_ascii=False),
    b.get('operation_status'), b.get('secondary_status'), a.get('modify_time'), b.get('modify_time'))
if tw:
    det += " ad_text trailing space trimmed by gateway (accepted by user)." if (b.get('ad_text') != a.get('ad_text')) else " ad_text had a trailing space; read-back ad_text unchanged."
if extra: det += ' ' + extra
row = {'unit': ad, 'before': cur, 'after_live': b.get('landing_page_url'), 'result': 'Fixed' if (url_ok and utm_ok and ld.get('code') == 0) else 'Failed', 'detail': det}
json.dump(row, open(m.W + 'row_%s.json' % ad, 'w'), ensure_ascii=False)
print(json.dumps(row, ensure_ascii=False, indent=1))
m.append(row)
