#!/usr/bin/env python3
"""Compose a result line for one unit of in_tiktok_9 from the transcript data (no hand-typed values) and append it.
usage: tt9rec.py <ad> [--note "<text>"] [--dry-only]   (--dry-only prints the line without appending)"""
import json, sys
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply7/tt9_work')
import tt9
from tt9 import *

args = sys.argv[1:]; ad = args[0]
note = args[args.index('--note') + 1] if '--note' in args else ''
u = units()[ad]; ch = u['changes'][0]; new = ch['new']
R = reads()


def call_info(mode):
    want_dry = (mode == 'dry')
    fs = [f for f in update_calls(ad) if bool(f[2].get('dry_run', True)) == want_dry]
    out = []
    for i, tid, inp, txt, iserr in fs:
        j = load_result(txt) or {}
        d = j.get('data') or {}
        o = {'order': i, 'input': body_of(inp), 'action': inp.get('action'), 'success': j.get('success'),
             'error': j.get('error'), 'raw': j.get('_raw_text'), 'is_error': iserr}
        if want_dry:
            o['body'] = (((d.get('data') or {}).get('request')) or {}).get('body')
            o['warnings'] = (d.get('data') or {}).get('warnings')
        else:
            dd = d.get('data') or {}
            o['code'] = dd.get('code'); o['message'] = dd.get('message'); o['request_id'] = dd.get('request_id')
            o['resp'] = dd.get('data')
        out.append(o)
    return out


def utm_desc(ups):
    if not ups:
        return 'no utm_params'
    ks = [p['key'] for p in ups]
    return 'utm_params %d keys %s%s' % (len(ks), '/'.join(k.replace('utm_', '') for k in ks), ' incl. utm_id' if 'utm_id' in ks else ', no utm_id')


lives = call_info('live'); drys = call_info('dry')
row = {'platform': 'tiktok', 'account_id': u['account_id'], 'unit_type': u['unit_type'], 'unit': u['unit'], 'ad_ids': u['ad_ids'],
       'ad_names': u['ad_names'], 'slot': ch['slot'], 'after_expected': new, 'new_entity_ids': ''}

if lives:
    pb = json.load(open(W + 'payload_%s.json' % ad)); P = pb['payload']; info = pb['info']; pre = pb['pre_rec']
    first_live = lives[0]['order']
    prer = latest(ad, before_order=first_live, R=R)
    assert prer and prer['request_id'] == pb['pre_read'], 'payload not built from the last read before the live call'
    cur_before = slot_cur(u, ch, prer['rec'], prer['kind'])[0]
    postr = latest(ad, after_order=lives[-1]['order'], R=R)
    assert postr, 'no read-back after the live call'
    cur_after, url_after, ups_after, extra, conflict, i = slot_cur(u, ch, postr['rec'], postr['kind'])
    rec = postr['rec']
    # dry-run evidence (last dry before first live)
    d_ok = [d for d in drys if d['order'] < first_live]
    dlast = d_ok[-1] if d_ok else None
    dry_txt = ('dry_run: call input == built payload (%s), preview body == payload (%s), warnings %s' %
               (dlast['input'] == P, dlast['body'] == P, dlast['warnings'])) if dlast else 'NO DRY RUN FOUND'
    live_txt = '; '.join('live attempt %d: input == dry-run payload (%s), %s' % (
        n + 1, l['input'] == P,
        ('code %s %s req %s' % (l['code'], l['message'], l['request_id'])) if l.get('code') is not None else
        ('error %s' % json.dumps(l.get('error') or l.get('raw'), ensure_ascii=False)[:400])) for n, l in enumerate(lives))
    if postr['kind'] == 'sp':
        acp = dict(pre.get('ad_configuration') or {}); aca = dict(rec.get('ad_configuration') or {})
        upp = acp.pop('utm_params', None); upa = aca.pop('utm_params', None)
        utm_ok = (sorted((p['key'], p['value']) for p in (upa or [])) == sorted((p['key'], p['value']) for p in new_utms(new))
                  and len(upa or []) == len(new_utms(new))) if upp else (upa == upp)
        diffs = []
        if acp != aca: diffs.append('ad_configuration other keys')
        lp = pre.get('landing_page_url_list') or []; la = rec.get('landing_page_url_list') or []
        if len(lp) != len(la): diffs.append('landing_page_url_list length')
        for k in sorted(set(pre) | set(rec)):
            if k in ('landing_page_url_list', 'ad_configuration', 'modify_time'): continue
            if k == 'secondary_status': continue
            if pre.get(k, '<absent>') != rec.get(k, '<absent>'): diffs.append(k)
        mats = info['materials']
        mdesc = ', '.join('%s %s identity %s%s%s' % (m['fmt'], m['identity_type'], m['identity_id'],
                                                     ', video %s' % m['video'] if m['video'] else '', ', tiktok_item_id %s' % m['item'] if m['item'] else ', no tiktok_item_id')
                          for m in mats)
        items_before = [(c.get('creative_info') or {}).get('tiktok_item_id') for c in pre.get('creative_list') or []]
        items_after = [(c.get('creative_info') or {}).get('tiktok_item_id') for c in rec.get('creative_list') or []]
        sent_utm = ('ad_configuration as read with only utm_params = the %d UTMs of new (no utm_id)' % len(new_utms(new))) if upp else \
                   'ad_configuration as read (the ad has no utm_params; none added)'
        detail = ('Upgraded Smart+ ad (creative_list: %s; ad_configuration keys %s). Pre-read smart_plus/ad/get req %s: URL == %s (%s; %s / %s; modify_time %s). '
                  'smart_plus/ad/update payload: landing_page_url_list as read with only [%d].landing_page_url = new, %s; creative_list, ad_text_list, ad_name and status NOT sent. '
                  '%s. %s. Re-read smart_plus/ad/get req %s: landing_page_url_list[%d].landing_page_url %s new byte for byte; %s %s; '
                  'creative_list tiktok_item_id before %s / after %s; other fields changed: %s; %s / %s; modify_time %s -> %s.' % (
                      mdesc, info['ac_keys'], prer['request_id'], info['match'], utm_desc(upp), pre.get('operation_status'), pre.get('secondary_status'),
                      pre.get('modify_time'), i, sent_utm, dry_txt, live_txt, postr['request_id'], i, '==' if url_after == new else '!=',
                      utm_desc(upa), '(matching new)' if (upp and utm_ok) else ('(unchanged: none)' if (not upp and utm_ok) else '(NOT as expected)'),
                      items_before, items_after, diffs if diffs else 'none', rec.get('operation_status'), rec.get('secondary_status'),
                      pre.get('modify_time'), rec.get('modify_time')))
    else:
        had = bool(pre.get('utm_params'))
        up = [(p['key'], p['value']) for p in (rec.get('utm_params') or [])]
        q = [(p['key'], p['value']) for p in new_utms(new)]
        utm_ok = (sorted(up) == sorted(q) and len(up) == len(q)) if had else (rec.get('utm_params') == pre.get('utm_params'))
        diffs = [k for k in sorted(set(pre) | set(rec)) if k not in ('landing_page_url', 'utm_params', 'modify_time', 'secondary_status') and pre.get(k, '<absent>') != rec.get(k, '<absent>')]
        cr = P['creatives'][0]
        sent = [k for k in cr if k not in ('ad_id', 'landing_page_url', 'utm_params', 'tracking_pixel_id')]
        tn = info['text']
        txt = ('ad_text sent as read' + (' incl. ' + '/'.join(tn['nonprint']) if tn['nonprint'] else '') +
               (' (had a TRAILING SPACE: ad_text trailing space trimmed by gateway)' if tn['trailing_ws'] else ' (no edge whitespace)'))
        px = cr.get('tracking_pixel_id')
        pxd = ('pixel read as %r sent as exact string %s; ' % (info['pixel'], px)) if px else 'no pixel on the ad, none sent; '
        detail = ('%s %s manual ad (identity %s%s), adgroup %s. Pre-read ad/get req %s: URL == %s (%s; %s / %s; modify_time %s). '
                  'Full ad/update with creative fields as read (%s; %s) and only landing_page_url = new%s; %s'
                  '%s. %s. Re-read ad/get req %s: landing_page_url %s new byte for byte; %s %s; tiktok_item_id after: %s; '
                  'other fields changed: %s; %s / %s; modify_time %s -> %s.' % (
                      info['cls'], info['ad_format'], info['identity_id'], ', tiktok_item_id %s' % info['item'] if info['item'] else ', no tiktok_item_id',
                      info['adgroup_id'], prer['request_id'], info['match'], utm_desc(pre.get('utm_params')), pre.get('operation_status'),
                      pre.get('secondary_status'), pre.get('modify_time'), ', '.join(sent), txt,
                      (' and utm_params = the %d UTMs of new (no utm_id)' % len(q)) if had else ' (no utm_params on the ad, none added)', pxd,
                      dry_txt, live_txt, postr['request_id'], '==' if url_after == new else '!=', utm_desc(rec.get('utm_params')),
                      '(matching new)' if (had and utm_ok) else ('(unchanged: none)' if (not had and utm_ok) else '(NOT as expected)'),
                      rec.get('tiktok_item_id', '<absent>'), diffs if diffs else 'none', rec.get('operation_status'), rec.get('secondary_status'),
                      pre.get('modify_time'), rec.get('modify_time')))
    fixed = (url_after == new and cur_after == new and utm_ok)
    side = ''
    if pre.get('secondary_status') != rec.get('secondary_status'):
        side = (' Side effect: secondary_status %s -> %s (TikTok re-review after the edit; operation_status unchanged %s).' % (
            pre.get('secondary_status'), rec.get('secondary_status'), rec.get('operation_status') == pre.get('operation_status')))
    if diffs:
        side += ' WARNING: other fields differ after the write: %s.' % diffs
    row.update({'before': cur_before, 'after_live': url_after, 'result': 'Fixed' if fixed else 'Failed', 'detail': detail + side + ((' ' + note) if note else '')})
else:
    # no write: classification from the latest complete read
    info = classify(ad, R=R)
    r = latest(ad, R=R)
    cur = info['cur']
    res = {'AlreadyFixed': 'AlreadyFixed', 'Skipped': 'Skipped', 'Hold': 'NotAttempted'}.get(info['decision'])
    if '--blocked' in args:
        assert info['decision'] == 'Write'
        res = 'Failed'
    assert res, 'decision %s needs a manual record' % info['decision']
    rec = r['rec']
    if r['kind'] == 'sp':
        ups = (rec.get('ad_configuration') or {}).get('utm_params')
        base = 'Upgraded Smart+ ad; read smart_plus/ad/get req %s (%s; %s / %s; modify_time %s)' % (r['request_id'], utm_desc(ups), info['op'], info['sec'], info['modify_time'])
    else:
        base = '%s %s ad (identity_type %s, identity %s%s); read ad/get req %s (%s; %s / %s; modify_time %s)' % (
            info['cls'], info['ad_format'], info['identity_type'], info['identity_id'],
            ', BC %s' % info['bc'] if info['bc'] else '', r['request_id'], utm_desc(rec.get('utm_params')), info['op'], info['sec'], info['modify_time'])
    if '--blocked' in args:
        drys = call_info('dry')
        dtxt = ('; a dry run had been sent before the block: input == payload (%s), preview body == payload (%s)' % (
            drys[-1]['input'] == json.load(open(W + 'payload_%s.json' % ad))['payload'], drys[-1]['body'] == json.load(open(W + 'payload_%s.json' % ad))['payload'])) if drys else ''
        detail = ('blocked by session safety check: %s. Not written: no live attempt was sent%s; the ad is unchanged, URL == %s. Not worked around. %s.' % (
            args[args.index('--blocked') + 1], dtxt, info['match'], base))
    elif res == 'AlreadyFixed':
        detail = 'No write: the live URL already equals new (%s). %s.' % ('byte-identical' if cur == new else 'same params, other order', base)
    elif res == 'Skipped':
        detail = 'changed since plan: %s. Not written. %s.' % (cur, base)
    else:
        detail = ('held for the user: Spark Push ad (BC_AUTH_TT, tiktok_item_id %s) - an API URL edit makes TikTok re-publish the post 30-60 min later and '
                  'detach the ad from its original post (53 of 75 earlier writes); not written until the user decides. URL == %s. No dry run or write sent. %s.' % (info['item'], info['match'], base))
    row.update({'before': cur, 'after_live': cur, 'result': res, 'detail': detail + ((' ' + note) if note else '')})

row = {k: row[k] for k in REQ}
print(json.dumps(row, ensure_ascii=False, indent=1))
if '--dry-only' not in args:
    p = W + 'row_%s.json' % ad
    json.dump(row, open(p, 'w'), ensure_ascii=False, indent=1)
    tt9.append(p)
