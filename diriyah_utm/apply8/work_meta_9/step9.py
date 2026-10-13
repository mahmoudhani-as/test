"""Local read-only checks for lane in_meta_9. Usage:
  step9.py prep AD            -> parse my last ad read, classify slots, build payload_<AD>.json, print it
  step9.py dry AD             -> compare my last adcreatives_create input (+ dry-run preview body) with payload_<AD>.json
  step9.py new AD NEWCR       -> parse my last read of NEWCR, compare with the original creative
  step9.py upd AD NEWCR       -> check my last meta_ad_id_update input/preview is exactly creative_id NEWCR
  step9.py after AD           -> parse my last ad read, compare slots with 'new' byte for byte
No API calls are made here."""
import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply8/work_meta_9')
from lib9 import *

cmd, AD = sys.argv[1], sys.argv[2]
u = unit(AD)

if cmd == 'prep':
    ad, inp, rid = last_ad_read(AD)
    json.dump(ad, open(W + 'ad_pre_%s.json' % AD, 'w'), ensure_ascii=False, indent=1)
    cr = ad['creative']
    print('read req', rid, '| ad', AD, ad.get('status'), ad.get('configured_status'), ad.get('effective_status'),
          '| creative', cr['id'], '(plan', u['creative_id'] + ')', '| updated', ad.get('updated_time'))
    print('url_tags:', repr(cr.get('url_tags')), '| creative keys:', sorted(cr.keys()))
    cl = classify(u, cr)
    for slot, v, cur in cl:
        print('  ', v, slot)
        print('      cur:', json.dumps(cur, ensure_ascii=False))
    if all(v == 'Write' for _, v, _ in cl):
        p, notes = build_payload(cr, u['changes'])
        print('notes', notes, '| invisible', has_invisible(p), '| bigints', big_ints(p))
        json.dump(p, open(W + 'payload_%s.json' % AD, 'w'), ensure_ascii=False, indent=1)
        orig = {k: cr[k] for k in p}
        print('diff original -> payload:')
        for l in diff(orig, p):
            print('   ', l)
        print('PAYLOAD_JSON:')
        print(dumps_safe(p))
    else:
        print('NOT ALL WRITE -> no payload built')

elif cmd == 'dry':
    p = json.load(open(W + 'payload_%s.json' % AD))
    inp, r, txt = last_call('meta_ad_account_id_adcreatives_create')
    print('dry_run sent:', inp.get('dry_run'), '| path_params', inp.get('path_params'), '| req', (r or {}).get('meta', {}).get('requestId'))
    sent = inp['payload']
    d1 = diff(p, sent)
    print('sent == payload file:', d1 == [], d1[:8])
    if inp.get('dry_run') is True:
        dd = r['data']['data']
        body = dd['request']['body'] if 'request' in dd else dd.get('body')
        d2 = diff(p, body)
        print('dry preview body == payload file:', d2 == [], d2[:8])
        print('preview method/url:', dd.get('method') or dd.get('request', {}).get('method'), dd.get('url') or dd.get('request', {}).get('url'))
        print('warnings:', json.dumps(dd.get('warnings'), ensure_ascii=False)[:600])
    else:
        print('live result:', json.dumps(r, ensure_ascii=False)[:800])

elif cmd == 'new':
    NEW = sys.argv[3]
    new, inp, rid = last_creative_read(NEW)
    json.dump(new, open(W + 'new_%s.json' % NEW, 'w'), ensure_ascii=False, indent=1)
    orig = json.load(open(W + 'ad_pre_%s.json' % AD))['creative']
    print('read req', rid, '| new creative', new.get('id'), '| status', new.get('status'), '| url_tags', repr(new.get('url_tags')))
    for c in u['changes']:
        v = get_slot(new, c['slot'])
        print('  new slot == new (bytes):', v == c['new'], c['slot'])
    print('website_url by link_url adlabel  orig:', json.dumps(url_by_label(orig), ensure_ascii=False))
    print('website_url by link_url adlabel  new :', json.dumps(url_by_label(new), ensure_ascii=False))
    print('label-keyed diff original -> new creative (asset_feed_spec arrays sorted by adlabel ids):')
    for l in diff(canon(orig), canon(new)):
        print('   ', l)

elif cmd == 'upd':
    NEW = sys.argv[3]
    inp, r, txt = last_call('meta_ad_id_update')
    print('dry_run sent:', inp.get('dry_run'), '| path_params', inp.get('path_params'), '| req', (r or {}).get('meta', {}).get('requestId'))
    print('sent payload == {"creative":{"creative_id":NEW}}:', inp.get('payload') == {'creative': {'creative_id': NEW}},
          '| path ad ok:', str((inp.get('path_params') or {}).get('ad_id')) == AD,
          '| extra top-level keys:', sorted(k for k in inp if k not in ('action', 'path_params', 'payload', 'dry_run', 'result_fields')))
    print('result:', json.dumps(r, ensure_ascii=False)[:900])

elif cmd == 'after':
    ad, inp, rid = last_ad_read(AD)
    json.dump(ad, open(W + 'ad_after_%s.json' % AD, 'w'), ensure_ascii=False, indent=1)
    cr = ad['creative']
    print('read req', rid, '| ad', AD, ad.get('status'), ad.get('configured_status'), ad.get('effective_status'),
          '| creative', cr['id'], '| updated', ad.get('updated_time'), '| url_tags', repr(cr.get('url_tags')))
    for c in u['changes']:
        after = full_url(cr, c['slot'])
        print('  after == new (bytes):', after == c['new'], c['slot'])
        print('      after_live:', json.dumps(after, ensure_ascii=False))
    print('  website_url by link_url adlabel:', json.dumps(url_by_label(cr), ensure_ascii=False))
    pre = json.load(open(W + 'ad_pre_%s.json' % AD))
    print('ad-level diff pre -> after (excluding creative):')
    for l in diff({k: v for k, v in pre.items() if k != 'creative'}, {k: v for k, v in ad.items() if k != 'creative'}):
        print('   ', l)
