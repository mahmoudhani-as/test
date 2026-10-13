import json, sys, os, uuid
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply9/work_google_2')
from lib import *

# usage: python3 -I step.py <gaql_req_id> <verify_unit|-> <next_unit|->
# One GAQL read serves as the read-back of <verify_unit> (just written) and the fresh pre-write
# re-read of <next_unit>. Prints the byte-for-byte verdict and, for the next unit, its class and payload.
rid, vunit, nunit = sys.argv[1], sys.argv[2], sys.argv[3]
rs, trunc, budget, inp = gaql_rows(rid)
if trunc or (budget and budget.get('truncated')):
    print('WARNING truncated result', rid)
rows = {}
for r in rs:
    aga = r['adGroupAd']; ad = aga['ad']
    rows[ad['id']] = {
        'req': rid, 'type': ad.get('type'), 'final_urls': ad.get('finalUrls', []),
        'final_url_suffix': ad.get('finalUrlSuffix'), 'tracking_url_template': ad.get('trackingUrlTemplate'),
        'status': aga.get('status'), 'approval': (aga.get('policySummary') or {}).get('approvalStatus'),
        'ad_group': r['adGroup']['id'], 'ad_group_name': r['adGroup'].get('name'),
        'campaign': r['campaign']['id'], 'campaign_status': r['campaign'].get('status'),
        'parent_suffix': [r['adGroup'].get('finalUrlSuffix'), r['campaign'].get('finalUrlSuffix'), r['customer'].get('finalUrlSuffix')],
        'parent_tut': [r['adGroup'].get('trackingUrlTemplate'), r['campaign'].get('trackingUrlTemplate'), r['customer'].get('trackingUrlTemplate')],
        'landing': landing(ad)}
U = {u['unit']: u for u in units()}
os.makedirs(W + '/reads', exist_ok=True)
if vunit != '-':
    ch = U[vunit]['changes'][0]
    r = rows.get(vunit)
    if r is None:
        print('VERIFY', vunit, 'NOT IN READ')
    else:
        byte_eq = r['final_urls'] == [ch['new']] and not r['final_url_suffix'] and r['landing'] == ch['new']
        clean = not any(r['parent_suffix']) and not any(r['parent_tut']) and not r['tracking_url_template']
        json.dump(dict(r, role='readback'), open(W + '/reads/%s_after.json' % vunit, 'w'), indent=1, ensure_ascii=False)
        print('VERIFY', vunit, 'BYTE_EQUAL_NEW' if byte_eq else 'MISMATCH', 'parents_clean' if clean else 'PARENT/TRACKING SET',
              r['status'], r['campaign_status'], r['approval'], rid)
        if not byte_eq:
            print('   live:', json.dumps(r['final_urls'], ensure_ascii=False), 'suffix:', r['final_url_suffix'])
            print('   new :', ch['new'])
if nunit != '-':
    u = U[nunit]; ch = u['changes'][0]
    r = rows.get(nunit)
    if r is None:
        print('NEXT', nunit, 'NOT IN READ')
        sys.exit(0)
    json.dump(dict(r, role='preread'), open(W + '/reads/%s_before.json' % nunit, 'w'), indent=1, ensure_ascii=False)
    cls = classify(r['landing'], ch)
    flags = []
    if len(r['final_urls']) != 1: flags.append('final_urls_len=%d' % len(r['final_urls']))
    if r['final_url_suffix']: flags.append('AD_SUFFIX=' + r['final_url_suffix'])
    if any(r['parent_suffix']): flags.append('PARENT_SUFFIX=%s' % r['parent_suffix'])
    if any(r['parent_tut']) or r['tracking_url_template']: flags.append('TRACKING_TEMPLATE')
    if (nunit, ch['slot']) in excluded(): flags.append('EXCLUDED')
    print('NEXT', nunit, cls, 'exact_now' if r['landing'] == ch['now'] else ('in_alt_now' if r['landing'] in ch.get('alt_now', []) else ''),
          r['type'], r['status'], r['campaign_status'], r['approval'], 'flags=%s' % flags, rid)
    if cls == 'Write' and not flags:
        ledger_p = W + '/idem_ledger.json'
        ledger = json.load(open(ledger_p)) if os.path.exists(ledger_p) else {}
        key = ledger.get(nunit) or str(uuid.uuid4())
        ledger[nunit] = key
        json.dump(ledger, open(ledger_p, 'w'), indent=1)
        print('KEY', key)
        print('PARAMS', json.dumps({'operations': [{'update': {'resource_name': 'customers/%s/ads/%s' % (u['account_id'], nunit),
                                                             'final_urls': [ch['new']]}, 'update_mask': 'final_urls'}]}, ensure_ascii=False))
    else:
        print('CUR', r['landing'])
